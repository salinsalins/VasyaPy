# coding: utf-8
'''
Created on Feb 10, 2020

@author: sanin
'''

import sys
import time
import logging
import os.path

import tango
from Utils import *

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'Timer_UI'
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '1_0'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

# Global configuration dictionary
TIMER_PERIOD = 300  # ms

logger = config_logger(level=logging.INFO)

class client():
    def __init__(self):
        #
        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')
        #
        # timer device
        try:
            self.timer_device = tango.DeviceProxy('binp/nbi/timing')
            self.adc_device = tango.DeviceProxy('binp/nbi/adc0')
        except:
            self.timer_device = None
            self.adc_device = None

def event_callback(*vars):
    logger.debug('%s Event callback', vars)


if __name__ == '__main__':
    adc = tango.DeviceProxy('binp/nbi/adc0')
    logger.debug('%s Timer created', adc)
    attr_name = 'Elapsed'
    attr = adc.read_attribute(attr_name)
    logger.debug('%s Attribute read', attr)
    logger.debug('%s Attribute value', attr.value)
    adc.subscribe_event(attr_name, tango.EventType.CHANGE_EVENT, event_callback)
    while True:
        time.sleep(1.0)

