#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@package basic_logger
@file basic_logger.py
@author Christopher Wingard
@brief Basic (limited command and control) RSN cabled instrument data logger
'''
__author__ = 'Christopher Wingard'
__license__ = 'Apache 2.0'


from base.logger import Direct
from base.command import main

if __name__ == '__main__':
    # parse the command line arguments
    args = main()

    # Initiate the direct connection and receiver objects
    direct = Direct(args.address, args.port, args.basename, args.increment)

    # start the connection
    direct.run()
