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


class VasyaPy_Server(Device):
    devices = []
    #database = tango.Database()

    devicetype = attribute(label="type", dtype=str,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="", format="%s",
                        doc="Hello from Vasya")

    def init_device(self):
        #print(time_ms(), 'init_device entry', self)
        self.device_type_str = 'Hello from Vasya'
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
            #self.reconnect_timeout = int(self.get_device_property('reconnect_timeout', 5000))
            self.set_state(DevState.INIT)
            try:
                Device.init_device(self)
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

    # def restore_polling(self, attr_name: str):
    #     try:
    #         p = self.get_attribute_property(attr_name, 'polling')
    #         pn = int(p)
    #         self.dp.poll_attribute(attr_name, pn)
    #     except:
    #         #self.logger.warning('', exc_info=True)
    #         pass

def time_ms():
    t = time.time()
    return time.strftime('%H:%M:%S')+(',%3d' % int((t-int(t))*1000.0))

def post_init_callback():
    #util = tango.Util.instance()
    #devices = util.get_device_list('*')
    for dev in VasyaPy_Server.devices:
        #print(dev)
        #if hasattr(dev, 'add_io'):
        dev.add_io()
            #print(' ')

def test():
    time.sleep(0.5)
    print('test')

def looping():
    VasyaPy_Server.logger.debug('loop entry')
    time.sleep(5.0)
    all_connected = True
    for dev in VasyaPy_Server.devices:
        dev.reconnect()
        all_connected = all_connected and dev.is_connected()
        VasyaPy_Server.logger.debug('loop %s %s', dev.device_name, all_connected)
        #print(dev, all_connected)
    VasyaPy_Server.logger.debug('loop exit')

if __name__ == "__main__":
    #if len(sys.argv) < 3:
        #print("Usage: python VasyaPy_server.py device_name ip_address")
        #exit(-1)
    VasyaPy_Server.run_server(post_init_callback=post_init_callback, event_loop=looping)
    #ET7000_Server.run_server(post_init_callback=post_init_callback)
