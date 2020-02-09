#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
VasyaPy tango device server"""

import sys
import time
import logging
import numpy
import traceback
import math
from threading import Thread, Lock

import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from tango.server import Device, attribute, command, pipe, device_property

NaN = float('nan')

def config_logger(name: str=__name__, level: int=logging.DEBUG):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.propagate = False
        logger.setLevel(level)
        f_str = '%(asctime)s,%(msecs)3d %(levelname)-7s [%(process)d:%(thread)d] %(filename)s ' \
                '%(funcName)s(%(lineno)s) %(message)s'
        log_formatter = logging.Formatter(f_str, datefmt='%H:%M:%S')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)
    return logger


class VasyaPy_Server(Device):
    devices = []
    logger = config_logger(level=logging.DEBUG)

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

    timerhistory = attribute(label="Shot_Time_History", dtype=(float,),
                        max_dim_x=1024,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%f",
                        doc="Timer start time history")

    def init_device(self):
        #print(time_ms(), 'init_device entry', self)
        self.device_type_str = 'Hello from Vasya'
        self.timer_start = NaN
        self.expected_timer_start = NaN
        self.start_flag = False
        self.times = []
        # init a thread lock
        if not hasattr(self, '_lock'):
            self._lock = Lock()
        with self._lock:
            #self.logger = VasyaPy_Server.logger
            #self.logger = self.config_logger(level=logging.INFO)
            #VasyaPy_Server.logger = self.logger
            #self.logger.debug('init_device logger created %s %s', self.logger, self)
            self.device_name = self.get_name()
            self.dp = tango.DeviceProxy(self.device_name)
            self.timer_name = self.get_device_property('timer_name', 'binp/nbi/timing')
            self.adc_name = self.get_device_property('adc_name', 'binp/nbi/adc0')
            try:
                self.timer_device = tango.DeviceProxy(self.timer_name)
                self.adc_device = tango.DeviceProxy(self.adc_name)
            except:
                self.timer_device = None
                self.adc_device = None
            self.set_state(DevState.INIT)
            try:
                Device.init_device(self)
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
        with self._lock:
            msg = '%s Vasya has been deleted' % self.device_name
            self.logger.info(msg)
            self.info_stream(msg)

    def read_devicetype(self):
        with self._lock:
            return self.device_type_str

    def read_lastshottime(self):
        with self._lock:
            return self.timer_start

    def read_timerhistory(self):
        with self._lock:
            return self.times

    @command(dtype_in=int)
    def SetLogLevel(self, level):
        with self._lock:
            self.logger.setLevel(level)
            msg = '%s Log level set to %d' % (self.device_name, level)
            self.logger.info(msg)
            self.info_stream(msg)

    def get_device_property(self, prop: str, default=None):
        # read property
        pr = self.dp.get_property(prop)[prop]
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
            pass
        return result


def post_init_callback():
    pass

def looping():
    time.sleep(0.1)
    VasyaPy_Server.logger.debug('loop entry')
    for dev in VasyaPy_Server.devices:
        with dev._lock:
            if dev.timer_device is None or dev.adc_device is None:
                VasyaPy_Server.logger.debug('Timer or ADC is not present - loop exit')
                return
            mode = dev.timer_device.read_attribute('Start_mode')
            if mode == 0:   #single
                dev.expected_timer_start = NaN
                if check_timer_state(dev.timer_device):
                    if not dev.start_flag:
                        dev.timer_start = time.time()
                        dev.times.append(dev.timer_start)
                        dev.start_flag = True
                        VasyaPy_Server.logger.info('Shot detected')
                else:
                    dev.start_flag = False
            elif mode == 1:  # periodical
                elapsed = dev.adc_device.read_attribute('Elapsed')
                period = dev.timer_device.read_attribute('Period')
                t = time.time() + period - elapsed
                if dev.expected_timer_start is NaN:
                    dev.expected_timer_start = t
                elif t > (dev.expected_timer_start - 1.0):
                    dev.timer_start = dev.expected_timer_start
                    dev.times.append(dev.timer_start)
                    dev.expected_timer_start = t
                    VasyaPy_Server.logger.info('Shot detected')
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
    VasyaPy_Server.run_server(post_init_callback=post_init_callback, event_loop=looping)
