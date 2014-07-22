#!/usr/bin/env python
'''
@package base.logger
@file base/logger.py
@author Ryan Cox and Christopher Wingard
@brief Module containing base classes for file writing and naming utilities
'''
__author__ = 'Ryan Cox and Christopher Wingard'
__license__ = 'Apache 2.0'

# import python modules
import os
import socket
import sys
from threading import Thread
from time import gmtime, sleep, strftime, struct_time


class Logger(object):
    def __init__(self, basename, increment):
        '''
        Initialize the base filename string and the file creation increment,
        clearing the last filename
        '''
        # set the constant portion of the file name and the increment
        self.basename = basename
        self.increment = increment

        # set the current file name
        self.fileName = ''

        # used to remember what day or hour we last were working with
        self.dayOfMonth = -1
        self.hourOfDay = -1

        self.checkMakeNewFileName()  # this will create our first filename

    def write(self, string):
        '''
        Check to see if we want to change the filename, then open the file,
        write the string, and close
        '''
        self.checkMakeNewFileName()
        file = open(self.fileName, 'ab')
        file.write(string)
        file.close()

    def checkMakeNewFileName(self):
        '''
        Routine to check if we need a new filename and to create one if so.
        Uses the increment flag (default is daily) to determine how often to
        create a new file.

        2014-07-17 C. Wingard   Added code to create files based on either
                                daily or hourly increments. Adds time to base
                                file name.
        '''
        time_value = gmtime()
        time_string = strftime('%Y%m%dT%H%M', time_value) + '_UTC.dat'

        if self.increment == 'hourly':
            # check if the hour of the day has changed or if this is the first
            # time we've run this (e.g. hourOfDay == 0)
            if self.hourOfDay != struct_time(time_value).tm_hour:
                # create a new filename string
                self.fileName = self.basename + '_' + time_string

                # update current day of month
                self.hourOfDay = struct_time(time_value).tm_hour

        if self.increment == 'daily':
            # check if the day of month has changed or if this is the first
            # time we've run this (e.g. dayOfMonth == 0)
            if self.dayOfMonth != struct_time(time_value).tm_mday:
                # create a new filename string
                self.fileName = self.basename + '_' + time_string

                # update current day of month
                self.dayOfMonth = struct_time(time_value).tm_mday


# Thread to receive and print data.
class Recv(Thread):
    # Establishes the receiving thread and file handling
    def __init__(self, conn, basename, increment):
        Thread.__init__(self, name='Recv')
        self.myFileHandler = Logger(basename, increment)
        self._conn = conn
        self._last_line = ''
        self._new_line = ''
        self.msglen = 4096  # default socket buffer size (4096 or 8192 are suggested)
        self.setDaemon(True)
        print 'logger initialized with basename %s, will create a new file %s' % (basename, increment)

    # The update_lines method adds each new character received to the current
    # line (up to self.msglen bytes) and then writes the chunk to the file.
    def update_lines(self, recv):
        self._new_line += recv
        self._last_line = self._new_line
        self._new_line = ''

    # The run method receives incoming characters, sends them to update_lines,
    # prints them to the console and sends them to the logger in byte
    # chunks where the size of the chunk is set by self.msglen.
    def run(self):
        print '### Receiver running.'
        while True:
            # read data from the socket at 1 Hz
            recv = self._conn.recv(min(self.msglen, 1024))
            if recv == '':
                raise RuntimeError("socket connection broken")

            self.update_lines(recv)
            self.myFileHandler.write(self._last_line)
            #os.write(sys.stdout.fileno(), recv)
            sys.stdout.write('#\t--- Received and saved %d bytes\n' % len(recv))
            sys.stdout.flush()
            sleep(1)


class Direct(object):
    # Establishes the connection and starts the receiving thread.
    def __init__(self, host, port, basename, increment):
        print '### connecting to %s:%s' % (host, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, port))
        self._bt = Recv(self._sock, basename, increment)
        self._bt.start()

    # Dispatches user commands.
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

        # exit the application
        self.stop()

    # closes the connection to the socket
    def stop(self):
        self._sock.close()

    # Sends a string. Returns the number of bytes written.
    def send(self, s):
        c = os.write(self._sock.fileno(), s)
        return c
