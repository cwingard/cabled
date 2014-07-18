#!/usr/bin/env python
# -*- coding: utf-8 -*-

USAGE = """

GP- This has been modified to make it a generic raw socket connection, with <CR><LF>

This program allows direct user iteraction with the TMPSF instrument via a socket.


USAGE:
    TMPSF_logged_2.py address port basename # connect to instrument on address:port, with logger basename
    TMPSF_logged_2.py address port basename # connect to instrument on address:port, with logger defaulted to generic basename
    TMPSF_logged_2.py port              # connect to instrument on localhost:port, with logger defaulted to generic basename
    
    

Example:
    TMPSF_logged_2.py 10.180.80.169 2101 TMPSF_10.180.80.169_2101
    

It establishes a TCP connection with the provided service, starts a thread to
print all incoming data from the associated socket, and goes into a loop to
dispach commands from the user. In this "logged" version the script stops any sampling,
initializes a new sampling program.

Commands accepted: 
    "stop" - erases flash memory and resets sampling mode
    "sample,X" - initializes sampling with a period defined by "X" in seconds (must be less than 100)
    "q" - closes TCP connection and exits program

"""

__author__ = 'Giora Proskurowski'
__license__ = 'Apache 2.0'

import sys
import socket
import os
import re
import time
import select
from logger import Logger   #logger.py is in Giora's python $path $HOME/Documents/python
from threading import Thread

# create an output logger file handler
# myFileHandler = Logger("TMPSF_10.180.80.169_2101_")  #worked here, now moved to _Recv, with basename passed from command line to _Direct to _Recv

class _Recv(Thread):
    """
    Thread to receive and print data.
    """

    def __init__(self, conn, basename):
        Thread.__init__(self, name="_Recv")
        self._conn = conn
        self.myFileHandler = Logger(basename)
        print "logger initialized with basename %s, will create new file and name at 00:00UTC daily" % (basename)
        self._last_line = ''
        self._new_line = ''
        self.setDaemon(True)


    def _update_lines(self, recv):
        if recv == "\n":  #TMPSF data line terminates with a ?, most I/O is with a '\n'
            self._new_line += recv #+ "\n" #this keeps the "#" in the I/O
            self._last_line = self._new_line
            self._new_line = ''
            return True
        else:
            self._new_line += recv
            return  False
            

    def run(self):
        print "### _Recv running."
        while True:
            recv = self._conn.recv(1)
            newline = self._update_lines(recv)
            os.write(sys.stdout.fileno(), recv)   #this writes char by char-- use commented out 'if newline' to write as a line
            self.myFileHandler.write(recv)    #writes to logger file  
# 
#             if newline:
#                  os.write(sys.stdout.fileno(), self._last_line)  #writes to console
#                  myFileHandler.write( self._last_line )    #writes to logger file   + "\n"
#                     
            sys.stdout.flush()


class _Direct(object):
    """
    Main program.
    """

    def __init__(self, host, port, basename):
        """
        Establishes the connection and starts the receiving thread.
        """
        print "### connecting to %s:%s" % (host, port)  
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, port))
        self._bt = _Recv(self._sock, basename)
        self._bt.start()

        print "### To check status, enter 'status'"
        print "### To stop sampling, erase memory and reset sampling mode enter 'stop'"
        print "### To initialize and start sampling mode enter 'sample,X' where X is sample period in seconds"
        print "### To close socket and exit program enter 'q'"
        
    def run(self):
        """
        Dispaches user commands.
        """
        while True:
        
            cmd = sys.stdin.readline()
            
            cmd = cmd.strip()
            cmd1 = cmd.split(",")
            
            if cmd=="q":
                print "### exiting"
                break
            
            elif cmd== "stop":
                print "### Erasing flash memory and resetting sampling mode"
                print "### this will take 20 seconds"
                self.send('A')
                time.sleep(.5)
                self.send('A')
                time.sleep(.5)
                self.send('!9')
                time.sleep(.5)
                self.send('!U01N')
                time.sleep(1)
                self.send('N')
                print "### intrument will not respond to commands for 15 seconds"
                time.sleep(15)
                self.send('T')
                print "### if instrument is in mode 00, it has been reset"
                
            elif cmd1[0] == "sample":
                cmdperiod=int(cmd1[1])
                print "### sampling period set to %s seconds" % cmdperiod
                self.send('A')
                self.send('A')
                time.sleep(.5)
                self.send('!9')
                time.sleep(.5)
                timevalue = time.gmtime()
                self.send('J'+ time.strftime("%y%m%d%H%M%S", timevalue))
                time.sleep(3)
                self.send('B')
                time.sleep(.5)
                self.send('L121004152152')
                time.sleep(3)
                self.send('D')
                time.sleep(.5)
                self.send('M191010180824')
                time.sleep(3)
                self.send('E')
                time.sleep(.5)
                self.send("K0000%02d" % cmdperiod)
                time.sleep(3)
                self.send('C')
                time.sleep(.5)
                self.send('!B0D')
                time.sleep(3)
                self.send('!M')
                time.sleep(.5)
                print "### Erasing flash memory and resetting sampling mode"
                print "### this will take 20 seconds"
                self.send('!U01N')
                time.sleep(1)
                self.send('N')
                time.sleep(20)
                self.send('T')
                time.sleep(3)
                self.send('T')
                time.sleep(3)
                self.send('!180370000')
                time.sleep(.5)
                self.send('!2')
                time.sleep(.5)
                self.send('P')
                time.sleep(.5) 
                print "### sampling started"
                
            elif cmd1[0]== "status":
                self.send('A')
                time.sleep(.5)
                self.send('A')
                time.sleep(.5)
                self.send('B')
                time.sleep(.5)
                self.send('C')
                time.sleep(.5)
                self.send('D')
                time.sleep(.5)
                self.send('E')
                time.sleep(.5)
                self.send('T')
                time.sleep(.5)
                self.send('F00')
                time.sleep(5)
                print "### Status checks complete, but not verified"
                
            else:
                print "### sending '%s'" % cmd
                self.send(cmd)
                self.send('\r\n')

        self.stop()
            
    def stop(self):
        self._sock.close()

    def send(self, s):
        """
        Sends a string. Returns the number of bytes written.
        """
        c = os.write(self._sock.fileno(), s)
        return c

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print USAGE
        exit()

    if len(sys.argv) == 2:
        host = 'localhost'
        port = int(sys.argv[1])
        basename = "INSTNAME_IPADDR_PORT"
        
    if len(sys.argv) == 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        basename = "INSTNAME_IPADDR_PORT"
        
    else:
        host = sys.argv[1]
        port = int(sys.argv[2])
        basename = sys.argv[3]

    direct = _Direct(host, port, basename)
    direct.run()

