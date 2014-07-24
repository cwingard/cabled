#!/usr/bin/env python
'''
@package base.main
@file base/main.py
@author Christopher Wingard
@brief Module containing the command line argument parsing code
'''
__author__ = 'Christopher Wingard'
__license__ = 'Apache 2.0'

import argparse


def main():
    '''
    Description:

        Main command line argument parser for the RSN cabled instrumentation
        data logger code. Sets up a single command line parser that can be
        reused multiple times by the different instrument loggers.

    Created by:

        2014-07-18    Christopher Wingard   Initial, derived from original code
                                            provided by Ryan Cox and Giora
                                            Proskurowski.
    '''
    # initialize arguement parser
    parser = argparse.ArgumentParser(description='RSN Cabled Instrument Logger',
                                     epilog='''Initiates and manages a
                                     connection to an instrument hosted on the
                                     RSN cabled infrastructure.''')

    # assign arguements for the basename, hostname, port number and file
    # logging increment.
    parser.add_argument("-a",  "--address", dest="address",
                        default="localhost", type=str,
                        help="set the IP address of the host the instrument is attached to")
    parser.add_argument("-p", "--port", dest="port",
                        default=2101, type=int,
                        help="set the IP port number on the host to which the instrument is attached")
    parser.add_argument("-b", "--base", dest="basename",
                        default="INSTNAME_IPADDR_PORT", type=str,
                        help="writes data from the instrument to a file using this string as the base name")
    parser.add_argument("-i", "--incr", dest="increment",
                        default="daily", type=str, choices=['daily', 'hourly'],
                        help="set the file creation increment, options are daily or hourly")

    # parse and assign the arguements
    args = parser.parse_args()

    # return the parsed arguements for use in the function
    return args
