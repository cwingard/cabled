#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@package sami_ph
@file sami_ph.py
@author Christopher Wingard
@brief Utilizes base classes from logger.py to create a custom scheduled logger
    for the Sunburst Sensors, SAMI2-ph (PHSEN)
'''
__author__ = 'Christopher Wingard'
__license__ = 'Apache 2.0'

import sys
from time import gmtime, mktime, sleep
from apscheduler.scheduler import Scheduler

from base.logger import Direct
from base.command import main


# Create a subclass of the Direct class from base/logger.py extending the run
# definition to include a scheduler for sending the sample processing (R0)
# command to the SAMI2-pH.
class _Direct(Direct):

    # set initial conditions for the subclass (in addition to the superclass
    # methods defined in Direct) and initialize the scheduler
    def __init__(self, *args, **kwargs):
        Direct.__init__(self, *args, **kwargs)
        self.scheduler = Scheduler()
        self.sampling = False

    def collect_sample(self):
        time_value = gmtime()
        self.send('R0\r')
        print '#\t--- Collecting Sample at %.3f' % mktime(time_value)

    def query_status(self):
        time_value = gmtime()
        self.send('S\r')
        print '#\t--- Query Instrument Status at %.3f' % mktime(time_value)

    def run(self):
        while True:

            # parse the user commands from stdin
            cmd = sys.stdin.readline()
            cmd = cmd.strip()

            # default command set
            if cmd == 'q':
                if self.sampling is True:
                    print '#\t--- stop all scheduled sampling'
                    self.scheduler.unschedule_job(self.sample)
                    self.scheduler.unschedule_job(self.status)
                    self.scheduler.shutdown()

                print '#\t--- turning on 1 Hz status messages'
                self.send('F1\r')
                print '### exiting'
                sleep(1)
                break

            elif cmd == 'init':
                print '### initialize instrument for sampling'
                print '#\t--- turning off 1 Hz status messages'
                self.send('F5A\r')
                sleep(1)
                print '#\t--- flush internal pump 2 times with reagent'
                self.send('P2\r')
                sleep(2)
                print '#\t\t--- * first cycle complete'
                self.send('P2\r')
                sleep(2)
                print '#\t\t--- * second cycle complete, ready for sampling'

            elif cmd == 'start':
                print '### sampling started, will sample every hour at the top of the hour'
                self.scheduler.start()
                self.sample = self.scheduler.add_cron_job(self.collect_sample, minute=0)
                self.status = self.scheduler.add_cron_job(self.query_status, hour='0,12', minute=15)
                #self.scheduler.print_jobs()
                self.sampling = True

            elif cmd == 'stop':
                print '### sampling stopped'
                self.scheduler.unschedule_job(self.sample)
                self.scheduler.unschedule_job(self.status)
                self.scheduler.shutdown()
                self.sampling = False

            else:
                print '### sending %s' % cmd
                self.send(cmd + '\r')

if __name__ == '__main__':
    # parse the command line arguments
    args = main()

    # Initiate the direct connection and receiver objects
    direct = _Direct(args.address, args.port, args.basename, args.increment)

    # start the connection and log data from the instrument
    direct.run()
