#!/usr/bin/env python
# -*- coding: utf-8 -*-

USAGE = """

GP- This has been modified to make it a generic raw socket connection, with <CR><LF>

This program allows direct user iteraction with the THSPH instrument via a socket.


USAGE:
    THSPH_logged.py address port basename # connect to instrument on address:port,with logger basename
    THSPH_logged.py address port  # connect to instrument on address:port, with logger defaulted to generic basename
    THSPH_logged.py port          # connect to instrument on localhost:port, with logger defaulted to generic basename

Example:
    THSPH_logged.py 10.180.80.131 4002 THSPH_10.180.80.131_4002
    

It establishes a TCP connection with the provided service, starts a thread to
print all incoming data from the associated socket, and goes into a loop to
dispach commands from the user.  In this "logged" version, the script runs two 
communication tests, and then begins sampling. Instrument output is printed to screen 
and logged in a file that is incremented on a daily basis.

The dataline from the instrument is translated from native 14-bit resolution 

The commands are:
    - an empty string --> sends a '\r\n' (<CR><LF>)
    - the command 'comms' sends 5 cP* commands to test communications, user should verify that 5 aP# are received
    - the command 'sample,X' polls the THSPH with "cH*" every X seconds
    - once sample,X is enabled, any key followed by enter will exit autopolling mode
    - The letter 'q' --> quits the program
    - Any other non-empty string --> sends the string followed by a '\r\n' (<CR><LF>)


"""

__author__ = 'Giora Proskurowski'
__license__ = 'Apache 2.0'

import sys
import socket
import os
import re
import time
import select
import numpy as np
from collections import deque
from matplotlib import pyplot as plt
from threading import Thread
from logger import Logger   #logger.py is in Giora's python $path /Applications/python
from math import log

# create an output logger file handler
# myFileHandler = Logger("THSPH_10.180.80.131_4002_") #worked here, now moved to _Recv, with basename passed from command line to _Direct to _Recv

class _Recv(Thread):
    """
    Thread to receive and print data.
    """

    def __init__(self, conn, basename):
        Thread.__init__(self, name="_Recv")
        self._conn = conn
        self._last_line = ''
        self._new_line = ''
        self.setDaemon(True)
        self.myFileHandler = Logger(basename)
        print "logger initialized with basename %s, will create new file and name at 00:00UTC daily" % (basename)
        self.sampleData = SampleData(100)
        self.samplePlot = SamplePlot(self.sampleData)
        print "### Plotting Thermocouple temperature"


    def _update_lines(self, recv):
        if recv == "#":  #THSPH data line terminates with a #, most I/O is with a '\n'
            self._new_line += recv #this keeps the "#" in the I/O
            self._last_line = self._new_line
            self._new_line = ''
            return True
        else:
            self._new_line += recv
            return  False
            
    def parse(self, sample):
            # constants for calculation, these are specific to unit "c"
            c1_e2l_H = 0.9979
            c0_e2l_H = -0.10287
            c1_e2l_L = 0.9964
            c0_e2l_L = -0.46112
            c1_e2l_r = 1.04938
            c0_e2l_r = -275.5
            c1_e2l_b = 1.04938
            c0_e2l_b = -275.5
            c5_l2s_H = .000000932483
            c4_l2s_H = -0.000122268
            c3_l2s_H = 0.00702
            c2_l2s_H = -.23532
            c1_l2s_H = 17.06172
            c0_l2s_H = 0
            c5_l2s_L = .000000932483
            c4_l2s_L = -0.000122268
            c3_l2s_L = 0.00702
            c2_l2s_L = -.23532
            c1_l2s_L = 17.06172
            c0_l2s_L = 0
            c3_l2s_r = .0000000877549539
            c1_l2s_r = .000234101
            c0_l2s_r = .001129306
            c3_l2s_b = .0000000877549539
            c1_l2s_b = .000234101
            c0_l2s_b = .001129306
            c5_s2v_r = 5.83124E-14
            c4_s2v_r = -4.09038E-11
            c3_s2v_r = -3.44498E-08
            c2_s2v_r = 5.14528E-05
            c1_s2v_r = 0.05841
            c0_s2v_r = 0.00209
            
            # parse data string
            ch1hex = sample[2:6]
            ch2hex = sample[6:10]
            ch3hex = sample[10:14]
            ch4hex = sample[14:18]
            ch5hex = sample[18:22]
            ch6hex = sample[22:26]
            ch7hex = sample[26:30]
            ch8hex = sample[30:34]
#            print "ch1 %s ch2 %s ch3 %s ch4 %s ch5 %s ch6 %s ch7 %s ch8 %s \r" % (ch1hex,ch2hex,ch3hex,ch4hex,ch5hex,ch6hex,ch7hex,ch8hex)
            # hex to decimal
            ch5dec = int(ch5hex,16)
            ch6dec = int(ch6hex,16)
            ch7dec = int(ch7hex,16)
            ch8dec = int(ch8hex,16)
#            print "ch5 %f ch6 %f ch7 %f ch8 %f \r" % (ch5dec,ch6dec,ch7dec,ch8dec)
            # raw to engineering
            vch5 = (ch5dec*0.25-1024)/61.606
            vch6 = (ch6dec*0.25-1024)/61.606
            rch7 = (10000*ch7dec*0.125)/(2048-ch7dec*0.125)
            rch8 = (10000*ch8dec*0.125)/(2048-ch8dec*0.125)
#            print "vch5 %f vch6 %f rch7 %f rch8 %f \r" % (vch5,vch6,rch7,rch8)
            # engineering to lab
            vch5act = vch5*c1_e2l_H + c0_e2l_H
            vch6act = vch6*c1_e2l_L + c0_e2l_L
            rch7act = rch7*c1_e2l_r + c0_e2l_r
            rch8act = rch8*c1_e2l_b + c0_e2l_b
#            print "vch5act %f rch7act %f rch8act %f \r" % (vch5act,rch7act,rch8act)
            # lab to scientific
            Tch5 = c0_l2s_H + c1_l2s_H*vch5act + c2_l2s_H*(vch5act)**2 + c3_l2s_H*(vch5act)**3 + c4_l2s_H*(vch5act)**4 + c5_l2s_H*(vch5act)**5
            Tch6 = c0_l2s_L + c1_l2s_L*vch6act + c2_l2s_L*(vch6act)**2 + c3_l2s_L*(vch6act)**3 + c4_l2s_L*(vch6act)**4 + c5_l2s_L*(vch6act)**5
            Tch7 = (1/(c0_l2s_r + c1_l2s_r*log(rch7act) + c3_l2s_r*log(rch7act)**3))-273.15
            Tch8 = (1/(c0_l2s_b + c1_l2s_b*log(rch8act) + c3_l2s_b*log(rch8act)**3))-273.15
            Vch7 = c0_s2v_r + c1_s2v_r*Tch7 + c2_s2v_r*(Tch7)**2 + c3_s2v_r*(Tch7)**3 + c4_s2v_r*(Tch7)**4 + c5_s2v_r*(Tch7)**5
            # final scientific
            TH = c0_l2s_H + c1_l2s_H*(vch5act + Vch7) + c2_l2s_H*(vch5act + Vch7)**2 + c3_l2s_H*(vch5act + Vch7)**3 + c4_l2s_H*(vch5act + Vch7)**4 + c5_l2s_H*(vch5act + Vch7)**5
            TL = c0_l2s_L + c1_l2s_L*(vch6act + Vch7) + c2_l2s_L*(vch6act + Vch7)**2 + c3_l2s_L*(vch6act + Vch7)**3 + c4_l2s_L*(vch6act + Vch7)**4 + c5_l2s_L*(vch6act + Vch7)**5
#            print "Tch5 %.2f Tch7 %.2f Tch8 %.2f TH %.2f THcal %.2f \r" % (Tch5, Tch6, Tch7, Tch8, TH, TL)
            print " %.2f TH %.2f TL %.2f ref %.2f board " % (TH, TL, Tch7, Tch8) + time.strftime("%Y-%m-%d %H:%M:%S UTC ", time.gmtime()) 
            return (TH, TL, Tch7, Tch8)  


    def run(self):
        print "### _Recv running."
        while True:
            recv = self._conn.recv(1)
            newline = self._update_lines(recv)
#            os.write(sys.stdout.fileno(), recv)   #this writes char by char, but I've moved it so that it is written as a line
            if newline:
                 os.write(sys.stdout.fileno(), self._last_line)  #writes to console
                 if self._last_line[0:2] == 'aH':
                    temps = self.parse(self._last_line)
                    self.myFileHandler.write( self._last_line + " %.2f TH %.2f TL %.2f ref %.2f board " % (temps[0], temps[1], temps[2], temps[3]) + time.strftime("%Y-%m-%d %H:%M:%S UTC \n", time.gmtime()) )    #writes to logger file
                    #timestamp = time.time()
                    new_data = temps
                    self.sampleData.add(new_data)
                    self.samplePlot.update(self.sampleData)
                 else:
                    self.myFileHandler.write( self._last_line + "\n")    #writes to logger file
                    
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
        print "For communication test enter 'comms'"
        print "To sample enter sample,X where X is sampling period in seconds"
        print "To stop sampling press any key followed by enter"
        print "To save plot enter 'saveplot'"          
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, port))
        self._bt = _Recv(self._sock, basename)
        self._bt.start()
#         self.commstest()
#         time.sleep(2)
#         self.commstest()
#         time.sleep(3)
        print ''
        print "### to test communications enter 'comms'"
        print "### to start sampling, enter 'sample,x' where x is period in seconds (default 5)"

    def run(self):
        """
        Dispaches user commands.
        """
        while True:
        
            cmd = sys.stdin.readline()
 
            cmd = cmd.strip()
            cmd1 = cmd.split(",")
            
            if cmd=="comms":
                self.commstest()
            
            elif cmd1[0] == "sample":
                if len(cmd1) ==1:
                    cmdperiod = 5
                else:
                    cmdperiod=int(cmd1[1])
                print "### sampling period set to %s seconds" % cmdperiod
                self.poll(cmdperiod) 
            
            elif cmd=="saveplot":
                now = 'THSPH_'+time.strftime("%Y-%m-%d_%H%M", time.gmtime())+'_UTC' 
                plt.savefig(now,orientation='landscape')
                print "### plot saved"
                
            elif cmd=="q":
                print "### exiting"
                break
                
            else:
                print "### sending '%s'" % cmd
                self.send(cmd)
                self.send('\r\n')

        self.stop()

    def commstest(self):
        print "### communication test, verify each command is responded to"
        self.send('cP*')
        time.sleep(.1)
        print '\r'
        self.send('cP*')
        time.sleep(.1)
        print '\r'
        self.send('cP*')
        time.sleep(.1)
        print '\r'
        self.send('cP*')
        time.sleep(.1)
        print '\r'
        self.send('cP*')
        time.sleep(.1)
        print '\r'
        print "### five test commands sent"
        return True
        
    def poll(self, period):
        """
        Polls THSPH with aH* repeatedly, at the sampling period, until any keyed sequence is entered
        """
        print "### Automatic polling mode"
        print "### To exit: input any key followed by enter"
        
        second = 0
        while True:
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                      stopcmd = sys.stdin.readline()
                      print "### exiting polling mode"
                      now = 'THSPH_'+time.strftime("%Y-%m-%d_%H%M", time.gmtime())+'_UTC' 
                      plt.savefig(now,orientation='landscape')
                      print "### plot saved"
                      break
                if second == period:
                      #print '\r'    #this had been used to make lines when recv was written char by char
                      self.send('cH*')
                      second = 0  # reset second counter
                time.sleep(.25)
                second += .25
            
    def stop(self):
        self._sock.close()

    def send(self, s):
        """
        Sends a string. Returns the number of bytes written.
        """
        c = os.write(self._sock.fileno(), s)
        return c

    def send_control(self, char):
        """
        Sends a control character.
        @param char must satisfy 'a' <= char.lower() <= 'z'
        """
        char = char.lower()
        assert 'a' <= char <= 'z'
        a = ord(char)
        a = a - ord('a') + 1
        return self.send(chr(a))
        
#class that holds data for N samples
class SampleData:
    # constr
    def __init__(self, maxLen):
        self.tcH = deque([0.0]*maxLen, maxlen = maxLen)
        self.tcL = deque([0.0]*maxLen, maxlen = maxLen)
        self.tsref = deque([0.0]*maxLen, maxlen = maxLen)
        self.tsbd = deque([0.0]*maxLen, maxlen = maxLen)
 
    # ring buffer
    def addToBuf(self, buf, val):
        buf.append(val)
 
    # add data
    def add(self, data):
        self.addToBuf(self.tcH, data[0])    #thermocouple "H"
        self.addToBuf(self.tcL, data[1])    #thermocouple "L"
        self.addToBuf(self.tsref, data[2])  #reference thermistor
        self.addToBuf(self.tsbd, data[3])   #thermistor in housing
        
#plot class
class SamplePlot:
    # constr
    def __init__(self, sampleData):
    # set plot to animated
        font = {'family' : 'serif', 'color'  : 'black','weight' : 'normal','size'   : 14}
        plt.ion()
        plt.axes()
        self.tcHline, = plt.plot(sampleData.tcH, label = 'Thermocouple H')
        self.tcLline, = plt.plot(sampleData.tcL, label = 'Thermocouple L')
        self.tsrefline, = plt.plot(sampleData.tsref, label = 'Ref Thermistor')
        self.tsbdline, = plt.plot(sampleData.tsbd, label = 'Board Thermistor')
        self.ymax = 40
        plt.ylim([0, self.ymax])
        plt.xlim([0, 100])
        plt.xlabel('time (not scaled to sample period)', fontdict = font)
        plt.ylabel('temperature (degC)', fontdict = font) #($^\circ$C)
        plt.legend(loc=2, prop = {'size':11, 'family':'serif'}, labelspacing=0.25)
        

 
    # update plot
    def update(self, sampleData):
        self.tcHline.set_ydata(sampleData.tcH)
        self.tcLline.set_ydata(sampleData.tcL)
        self.tsrefline.set_ydata(sampleData.tsref)
        self.tsbdline.set_ydata(sampleData.tsbd)
        if self.ymax < float(max(sampleData.tcH)):
            self.ymax = float(max(sampleData.tcH))+10
            plt.ylim([0, self.ymax])
        plt.draw()

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
