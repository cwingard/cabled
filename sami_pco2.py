#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@package sami_pco2
@file sami_pco2.py
@author Christopher Wingard
@brief Utilizes base classes from logger.py to create a custom scheduled logger
    for the Sunburst Sensors, SAMI2-pCO2 (PCO2W)
'''
__author__ = 'Christopher Wingard'
__license__ = 'Apache 2.0'

import sys
import apscheduler


from base.logger import Direct
from base.command import main


# Create a subclass of the Direct class from base/logger.py extending the run
# definition to include a scheduler for sending the pump (R1) and sample
# processing (R0) commands to the SAMI2-pCO2.
class _Direct(Direct):
    
    def run(self):
        while True:
            # parse the user commands from stdin
            cmd = sys.stdin.readline()
            cmd = cmd.strip()

            # default command set
            if cmd == 'q':
                print '### exiting'
                break
            else:
                print '### sending %s' % cmd
                self.send(cmd)
                self.send('\r\n')

if __name__ == '__main__':
    # parse the command line arguments
    args = main()

    # Initiate the direct connection and receiver objects
    direct = _Direct(args.address, args.port, args.basename, args.increment)

    # start the connection
    direct.run()
