#!/usr/bin/env python

USAGE = """

This program displays and records everything sent or received on the specified socket


USAGE:
    python BasicLogger.py address port basename # connect to instrument on address:port, with logger basename
    python BasicLogger.py address port # connect to instrument on address:port, with logger defaulted to generic basename
    python BasicLogger.py port # connect to instrument on localhost:port, with logger defaulted to generic basename
    
    
Example:
    python BasicLogger.py 10.180.80.169 2101 ADCP.180.80.169_2101

"""

__author__ = 'Ryan Cox'
__license__ = 'Apache 2.0'

import sys
import socket
import os
import re
import time
import select
from logger import Logger   #logger.py is in Ryan's python $path C:/python27
from threading import Thread

# Thread to receive and print data.
class _Recv(Thread):
    def __init__(self, conn, basename):
        Thread.__init__(self, name="_Recv")
        self._conn = conn
        self.myFileHandler = Logger(basename)
        print "logger initialized with basename %s, will create new file and name at 00:00UTC daily" % (basename)
        self._last_line = ''
        self._new_line = ''
        self.setDaemon(True)

    # The _update_lines method adds each new character received to the current line or saves the current line and creates a new line
    def _update_lines(self, recv):
        if recv == "\n":  #TMPSF data line terminates with a ?, most I/O is with a '\n'
            self._new_line += recv #+ "\n" #this keeps the "#" in the I/O
            self._last_line = self._new_line
            self._new_line = ''
            return True
        else:
            self._new_line += recv
            return  False
            
    # The run method receives incoming chars and sends them to _update_lines, prints them to the console and sends them to the logger.
    def run(self):
        print "### _Recv running."
        while True:
            recv = self._conn.recv(1)
            newline = self._update_lines(recv)
            os.write(sys.stdout.fileno(), recv)   #this writes char by char-- use commented out 'if newline' to write as a line
            self.myFileHandler.write(recv)    #writes to logger file  

            # uncomment code below to print by lines instead of by characters.
            # if newline:
                 # os.write(sys.stdout.fileno(), self._last_line)  #writes to console
                 # myFileHandler.write( self._last_line )    #writes to logger file   + "\n"
                    
            sys.stdout.flush()

# Main program
class _Direct(object):
    # Establishes the connection and starts the receiving thread.
    def __init__(self, host, port, basename):
        print "### connecting to %s:%s" % (host, port)  
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self._sock.connect((host, port))
        self._bt = _Recv(self._sock, basename)
        self._bt.start()
    
    # Dispatches user commands.    
    def run(self):
        while True:
        
            cmd = sys.stdin.readline()
            
            cmd = cmd.strip()
            
            if cmd == "q":
                print "### exiting"
                break
                
            else:
                print "### sending '%s'" % cmd
                self.send(cmd)
                self.send('\r\n')

        self.stop()
    
    # closes the connection to the socket
    def stop(self):
        self._sock.close()
    
    # Sends a string. Returns the number of bytes written.
    def send(self, s):
        c = os.write(self._sock.fileno(), s)
        return c

# main method.  Accepts command line input parameters and runs the program
# default host: 'localhost'
# default port: no default, must be specified
# default basename: "INSTNAME_IPADDR_PORT"
if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print USAGE
        exit()
    
    elif len(sys.argv) == 2:
        host = 'localhost'
        port = int(sys.argv[1])
        basename = "INSTNAME_IPADDR_PORT"
        
    elif len(sys.argv) == 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        basename = "INSTNAME_IPADDR_PORT"
        
    else:
        host = sys.argv[1]
        port = int(sys.argv[2])
        basename = sys.argv[3]

    direct = _Direct(host, port, basename)
    direct.run()

