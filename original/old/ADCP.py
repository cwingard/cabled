#!/usr/bin/env python
# -*- coding: utf-8 -*-


USAGE = """

GP- This has been modified to make it a generic raw socket connection, with <CR><LF>

This program allows direct user interaction with an ADCP instrument via a socket.


USAGE:
    python ADCP.py address port basename # connect to instrument on address:port, with logger basename
    python ADCP.py address port # connect to instrument on address:port, with logger defaulted to generic basename
    python ADCP.py port              # connect to instrument on localhost:port, with logger defaulted to generic basename
    
    

Example:
    python ADCP.py 10.180.80.169 2101 ADCP.180.80.169_2101
    

It establishes a TCP connection with the provided service, starts a thread to
print all incoming data from the associated socket, and goes into a loop to
dispatch commands from the user. In this "logged" version the script stops any sampling,
initializes a new sampling program.

Commands accepted: 
    "init,[configuration]" - reconfigures instrument to desired configuration.  Configurations include: B104, I103, E101, D102, K101, E301, D302
    "status" - prints status and configuration information
    "sample" - initializes sampling
    "stop" - stop sampling
    "q" - closes TCP connection and exits program

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
        
        # wake and connect to instrument
        self.send('+++\r\n') # wakes instrument 
        time.sleep(2)
        
        # set the instruments internal clock
        timevalue = time.gmtime()
        self.send('TT'+ time.strftime("%Y/%m/%d,%H:%M:%S" + '\r\n', timevalue))
        time.sleep(1)
        
        # print status messages
        self.send('PS0\r\n') # output system configuration
        time.sleep(3)
        self.send('AC\r\n') # output active calibration data
        time.sleep(4)
        self.send('FD\r\n') # output fault log 
        time.sleep(2)
        # self.send('PT200\r\n') # 'PT200' runs all tests.  'PT300' runs all tests continuously
        # time.sleep(25)

            
        # print possible user commands
        print "### Status checks complete, but not verified"
        print "### To configure instrument enter 'init,[configuration]'"
        print "### Supported configurations are: 'B104, I103, E101, D102, K101, E301, D302'"
        print "### To display status and configuration information enter 'status'"
        print "### To start sampling enter 'sample'"
        print "### To close socket and exit program enter 'q'"
        print "### To stop sampling enter 'stop'"
    
    # Dispatches user commands.    
    def run(self):
        while True:
        
            cmd = sys.stdin.readline()
            
            cmd = cmd.strip()
            cmd1 = cmd.split(",")
            
            if cmd1[0] == "q":
                print "### exiting"
                break
            
            # initializes instrument factory default and then to user specified configuration
            elif cmd1[0] == "init":
                print "### initializing"
                
                # initialize system settings
                self.send('CR1\r\n') # 'CR1' factory default, 'CR0' user default
                time.sleep(2)
                
                # if no configuration specified print options
                if len(cmd1) != 2:
                    print "### must specify configuration.  Enter 'init,[configuration]'"
                    print "### Supported configurations are: 'K101'"
        
                # Configures system settings based on specified configuration
                # TODO: confirm configuration settings
                if cmd1[1] == "B104":
                    print "### configuring B104"
                    self.send('CF11110\r\n') # Flow control
                    time.sleep(1)
                    self.send('CL0\r\n') # Don't sleep between pings
                    time.sleep(1)
                    self.send('ED8000\r\n') # transducer depth
                    time.sleep(1)
                    self.send('EX00111\r\n') # coordinate transformation
                    time.sleep(1)
                    self.send('TE00:00:00.00\r\n') # Time per ensemble
                    time.sleep(1)
                    self.send('TP00:00.00\r\n') # Time between pings
                    time.sleep(1)
                    self.send('WN22\r\n') # Number of depth cells
                    time.sleep(1)
                    self.send('WP1\r\n') # Pings per ensemble
                    time.sleep(1)
                    self.send('WS400\r\n') # Depth cell size
                    time.sleep(1)
                elif cmd1[1] == "I103":
                    print "### configuring I103"
                    self.send('CF11110\r\n') # Flow control
                    time.sleep(1)
                    self.send('CL0\r\n') # Don't sleep between pings
                    time.sleep(1)
                    self.send('ED8000\r\n') # transducer depth
                    time.sleep(1)
                    self.send('EX00111\r\n') # coordinate transformation
                    time.sleep(1)
                    self.send('TE00:00:00.00\r\n') # Time per ensemble
                    time.sleep(1)
                    self.send('TP00:00.00\r\n') # Time between pings
                    time.sleep(1)
                    self.send('WN40\r\n') # Number of depth cells
                    time.sleep(1)
                    self.send('WP1\r\n') # Pings per ensemble
                    time.sleep(1)
                    self.send('WS1600\r\n') # Depth cell size
                    time.sleep(1)
                elif cmd1[1] == "E101":
                    print "### configuring E101"
                    self.send('CF11110\r\n') # Flow control
                    time.sleep(1)
                    self.send('CL0\r\n') # Don't sleep between pings
                    time.sleep(1)
                    self.send('ED8000\r\n') # transducer depth
                    time.sleep(1)
                    self.send('EX00111\r\n') # coordinate transformation
                    time.sleep(1)
                    self.send('TE00:00:00.00\r\n') # Time per ensemble
                    time.sleep(1)
                    self.send('TP00:00.00\r\n') # Time between pings
                    time.sleep(1)
                    self.send('WN50\r\n') # Number of depth cells
                    time.sleep(1)
                    self.send('WP1\r\n') # Pings per ensemble
                    time.sleep(1)
                    self.send('WS800\r\n') # Depth cell size
                    time.sleep(1)
                elif cmd1[1] == "D102":
                    print "### configuring D102"
                    self.send('CF11110\r\n') # Flow control
                    time.sleep(1)
                    self.send('CL0\r\n') # Don't sleep between pings
                    time.sleep(1)
                    self.send('ED8000\r\n') # transducer depth
                    time.sleep(1)
                    self.send('EX00111\r\n') # coordinate transformation
                    time.sleep(1)
                    self.send('TE00:00:00.00\r\n') # Time per ensemble
                    time.sleep(1)
                    self.send('TP00:00.00\r\n') # Time between pings
                    time.sleep(1)
                    self.send('WN20\r\n') # Number of depth cells
                    time.sleep(1)
                    self.send('WP1\r\n') # Pings per ensemble
                    time.sleep(1)
                    self.send('WS800\r\n') # Depth cell size
                    time.sleep(1)
                elif cmd1[1] == "K101":
                    print "### configuring K101"
                    self.send('CF11110\r\n') # Flow control
                    time.sleep(1)
                    self.send('CL0\r\n') # Don't sleep between pings
                    time.sleep(1)
                    self.send('ED8000\r\n') # transducer depth
                    time.sleep(1)
                    self.send('EX00111\r\n') # coordinate transformation
                    time.sleep(1)
                    self.send('TE00:00:00.00\r\n') # Time per ensemble
                    time.sleep(1)
                    self.send('TP00:00.00\r\n') # Time between pings
                    time.sleep(1)
                    self.send('WN30\r\n') # Number of depth cells
                    time.sleep(1)
                    self.send('WP1\r\n') # Pings per ensemble
                    time.sleep(1)
                    self.send('WS3200\r\n') # Depth cell size
                    time.sleep(1)
                elif cmd1[1] == "E301":
                    print "### configuring E301"
                    self.send('CF11110\r\n') # Flow control
                    time.sleep(1)
                    self.send('CL0\r\n') # Don't sleep between pings
                    time.sleep(1)
                    self.send('ED8000\r\n') # transducer depth
                    time.sleep(1)
                    self.send('EX00111\r\n') # coordinate transformation
                    time.sleep(1)
                    self.send('TE00:00:00.00\r\n') # Time per ensemble
                    time.sleep(1)
                    self.send('TP00:00.00\r\n') # Time between pings
                    time.sleep(1)
                    self.send('WN50\r\n') # Number of depth cells
                    time.sleep(1)
                    self.send('WP1\r\n') # Pings per ensemble
                    time.sleep(1)
                    self.send('WS800\r\n') # Depth cell size
                    time.sleep(1)
                elif cmd1[1] == "D302":
                    print "### configuring D302"
                    self.send('CF11110\r\n') # Flow control
                    time.sleep(1)
                    self.send('CL0\r\n') # Don't sleep between pings
                    time.sleep(1)
                    self.send('ED8000\r\n') # transducer depth
                    time.sleep(1)
                    self.send('EX00111\r\n') # coordinate transformation
                    time.sleep(1)
                    self.send('TE00:00:00.00\r\n') # Time per ensemble
                    time.sleep(1)
                    self.send('TP00:00.00\r\n') # Time between pings
                    time.sleep(1)
                    self.send('WN30\r\n') # Number of depth cells
                    time.sleep(1)
                    self.send('WP1\r\n') # Pings per ensemble
                    time.sleep(1)
                    self.send('WS800\r\n') # Depth cell size
                    time.sleep(1) 

            elif cmd1[0] == "status":
                # print status messages
                self.send('PS0\r\n') # output system configuration
                time.sleep(3)
                self.send('AC\r\n') # output active calibration data
                time.sleep(4)
                self.send('FD\r\n') # output fault log
                time.sleep(2)
                self.send('PT200\r\n') # 'PT200' runs all tests.  'PT300' runs all tests continuously
                time.sleep(25)
            
            elif cmd1[0] == "sample":
                print "sampling started"
                
                self.send('CK\r\n') # saves setup to RAM and must be second to last command
                time.sleep(2)
                self.send('CS\r\n') # starts deployment and must be the last command
                time.sleep(2)
                
            elif cmd1[0] == "stop":
                print "stopping"
                
                self.send('+++\r\n') 
                time.sleep(1)
                
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

