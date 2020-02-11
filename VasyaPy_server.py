#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
VasyaPy tango device server"""

import sys
import os
import time
import logging
import numpy
import traceback
import math
from threading import Thread, Lock
import winsound

import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from tango.server import Device, attribute, command, pipe, device_property
from Utils import *

class VasyaPy_Server(Device):
    devices = []
    logger = config_logger(level=logging.DEBUG)
    beeped = False

    devicetype = attribute(label="type", dtype=str,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="", format="%s",
                        doc="Hello from Vasya")

    lastshottime = attribute(label="Last_Shot_Time", dtype=float,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%f",
                        doc="Time of the last shot")

    def init_device(self):
        #print(time_ms(), 'init_device entry', self)
        self.device_type_str = 'Hello from Vasya'
        self.last_shot_time = NaN
        self.device_name = self.get_name()
        self.device_proxy = tango.DeviceProxy(self.device_name)
        self.timer_name = self.get_device_property('timer_name', 'binp/nbi/timing')
        self.adc_name = self.get_device_property('adc_name', 'binp/nbi/adc0')
        level = self.get_device_property('loglevel', 10)
        self.logger.setLevel(level)
        try:
            self.timer_device = tango.DeviceProxy(self.timer_name)
            self.adc_device = tango.DeviceProxy(self.adc_name)
        except:
            self.timer_device = None
            self.adc_device = None
            msg = '%s Timer or ADC can not be found - exit' % self.device_name
            self.logger.debug('', exc_info=True)
            self.logger.error(msg)
            self.error_stream(msg)
            os._exit(5)
        self.set_state(DevState.INIT)
        try:
            Device.init_device(self)
            if self not in VasyaPy_Server.devices:
                VasyaPy_Server.devices.append(self)
            msg = 'Vasya has been born <%s>' % self.device_name
            self.logger.info(msg)
            self.info_stream(msg)
            self.set_state(DevState.RUNNING)
        except:
            msg = '%s Vasya creation error' % self.device_name
            self.logger.debug('', exc_info=True)
            self.logger.error(msg)
            self.error_stream(msg)
            self.set_state(DevState.FAULT)

    def delete_device(self):
        msg = '%s Vasya has been deleted' % self.device_name
        self.logger.info(msg)
        self.info_stream(msg)

    def read_devicetype(self):
        return self.device_type_str

    def read_lastshottime(self):
        if self.adc_device is None:
            VasyaPy_Server.logger.error('ADC is not present')
            return NaN
        elapsed = self.adc_device.read_attribute('Elapsed')
        t0 = time.time()
        if elapsed.quality != tango._tango.AttrQuality.ATTR_VALID:
            self.logger.info('Non Valid attribute %s %s' % (elapsed.name, elapsed.quality))
        t = elapsed.time.tv_sec + (1.0e-6 * elapsed.time.tv_usec)
        #VasyaPy_Server.logger.debug('elapsed.value %s' % elapsed.value)
        #VasyaPy_Server.logger.debug('t0 %f' % t0)
        #VasyaPy_Server.logger.debug('elapsed read time %f' % t)
        self.last_shot_time = t0 - elapsed.value
        return self.last_shot_time

    @command(dtype_in=int)
    def SetLogLevel(self, level):
        self.logger.setLevel(level)
        msg = '%s Log level set to %d' % (self.device_name, level)
        self.logger.info(msg)
        self.info_stream(msg)

    def get_device_property(self, prop: str, default=None):
        if not hasattr(self, 'device_proxy') or self.device_proxy is None:
            self.device_proxy = tango.DeviceProxy(self.device_name)
        pr = self.device_proxy.get_property(prop)[prop]
        result = None
        if len(pr) > 0:
            result = pr[0]
        if default is None:
            return result
        try:
            if result is None or result == '':
                result = default
            else:
                result = type(default)(result)
        except:
            result = default
        return result


def post_init_callback():
    pass

def looping():
    time.sleep(0.3)
    VasyaPy_Server.logger.debug('loop entry')
    for dev in VasyaPy_Server.devices:
        if dev.adc_device is not None and dev.timer_device is not None:
            mode = dev.timer_device.read_attribute('Start_mode')
            if mode == 1:
                period = dev.timer_device.read_attribute('Period')
                elapsed = dev.adc_device.read_attribute('Elapsed')
                remained = period - elapsed
                if not VasyaPy_Server.beeped and remained < 1.0:
                    winsound.Beep(1000, 300)
                    VasyaPy_Server.beeped = True
                if remained > 2.0:
                    VasyaPy_Server.beeped = False
    VasyaPy_Server.logger.debug('loop exit')

channels = ['channel_state'+str(k) for k in range(12)]

def check_timer_state(timer_device):
        if timer_device is None:
            return False
        state = False
        avs = []
        try:
            avs = timer_device.read_attributes(channels)
        except:
            pass
        for av in avs:
            state = state or av.value
        return state


if __name__ == "__main__":
    #VasyaPy_Server.run_server(post_init_callback=post_init_callback, event_loop=looping)
    VasyaPy_Server.run_server()
