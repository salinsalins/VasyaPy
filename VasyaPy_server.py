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

class VasyaPy_Server(Device):
    devices = []
    logger = None

    devicetype = attribute(label="type", dtype=str,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="", format="%s",
                        doc="Hello from Vasya")
    timerstart = attribute(label="Shot_Time", dtype=float,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%f",
                        doc="Timer start time")

    timerhistory = attribute(label="Shot_Time_History", dtype=tango,
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
            self.logger = self.config_logger(level=logging.INFO)
            VasyaPy_Server.logger = self.logger
            #self.logger.debug('init_device logger created %s %s', self.logger, self)
            self.device_name = self.get_name()
            self.dp = tango.DeviceProxy(self.device_name)
            # read device properties
            self.timer_name = int(self.get_device_property('timer_name', 'binp/nbi/timing'))
            self.adc_name = int(self.get_device_property('adc_name', 'binp/nbi/adc0'))
            self.dimer_device = tango.DeviceProxy(self.timer_name)
            self.adc_device = tango.DeviceProxy(self.adc_name)
            self.set_state(DevState.INIT)
            try:
                Device.init_device(self)
                VasyaPy_Server.devices.append(self)
                msg = '%s Vasya has been born' % self.device_name
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

    def read_timerstart(self):
        with self._lock:
            return self.timer_start

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

    def config_logger(self, name: str=__name__, level: int=logging.DEBUG):
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

    # def get_attribute_property(self, attr_name: str, prop_name: str):
    #     device_name = self.get_name()
    #     databse = self.database
    #     all_attr_prop = databse.get_device_attribute_property(device_name, attr_name)
    #     all_prop = all_attr_prop[attr_name]
    #     if prop_name in all_prop:
    #         prop = all_prop[prop_name][0]
    #     else:
    #         prop = ''
    #     return prop


def post_init_callback():
    pass

def looping():
    VasyaPy_Server.logger.debug('loop entry')
    time.sleep(0.1)
    for dev in VasyaPy_Server.devices:
        mode = dev.timer_device.read_attribute('Start_mode')
        if mode == 0:   #single
            dev.expected_timer_start = NaN
            if check_timer_state(dev.timer_device):
                if not dev.start_flag:
                    dev.timer_start = time.time()
                    dev.times.append(dev.timer_start)
                    dev.start_flag = True
            else:
                dev.start_flag = False
        elif mode == 1:  # periodical
            elapsed = dev.adc_device.read_attribute('Elapsed')
            period = dev.timer_device.read_attribute('Period')
            dev.expected_timer_start = time.time() + period - elapsed
    VasyaPy_Server.logger.debug('loop exit')

def check_timer_state(timer_device):
        if timer_device is None:
            return None
        state = False
        for k in range(12):
            try:
                av = timer_device.read_attribute('channel_state'+str(k))
                state = state or av.value
            except:
                pass
        return state


if __name__ == "__main__":
    VasyaPy_Server.run_server(post_init_callback=post_init_callback, event_loop=looping)
