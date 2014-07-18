#!/usr/bin/env python

USAGE = """

GP- This has been modified to make it a generic raw socket connection, with <CR><LF>

This program allows direct user interaction with the RAS_PPS instrument via a socket.


USAGE:
    RAS_PPS_safetest_logged.py address port basename # connect to instrument on address:port, with logger basename
    RAS_PPS_safetest_logged.py address port basename # connect to instrument on address:port, with logger defaulted to generic basename
    RAS_PPS_safetest_logged.py port              # connect to instrument on localhost:port, with logger defaulted to generic basename
    
    

Example:
    RAS_PPS_safetest_logged.py 10.180.80.166 4002 RAS-D1000_10.180.80.166_4002
    

It establishes a TCP connection with the provided service, starts a thread to
print all incoming data from the associated socket, and goes into a loop to
dispach commands from the user. In this "logged" version the script stops any sampling,
initializes a new sampling program.

Commands accepted: 

    - an empty string --> sends a '\r\n' (<CR><LF>)
    - the command 'wake' sends 5 control-Cs that wake and enable the RAS and PPS
    - the command 'autoTemp' starts a query of the Temp probe, only when connected to the correct port (4002)
    - once autoTemp enabled, any key followed by enter will exit autosample mode
    - the command 'autoRAS' starts a sampling simulation that protects against actually sampling, only when connected to RAS port (4001)
    - once autoRAS enabled, any key followed by enter will exit autosample mode
    - the command 'autoPPS' starts a sampling simulation that protects against actually sampling, only when connected to PPS port (4003)
    - once autoPPS enabled, any key followed by enter will exit autosample mode
    - the command 'cycleRAS' cycles through all ports, done to equalize pressure during deployment
    - the command 'cyclePPS' cycles through all ports, done to equalize pressure during deployment
    - The letter 'q' --> quits the program
    - Any other non-empty string --> sends the string followed by a '\r\n' (<CR><LF>)


"""

__author__ = 'Giora Proskurowski modified original Carlos Rueda'
__license__ = 'Apache 2.0'

import sys
import socket
import os
import time
import select
from logger import Logger   #logger.py is in Giora's python $path $HOME/Documents/python
from threading import Thread


class _Recv(Thread):
    """
    Thread to receive and print data.
    """

    def __init__(self, conn):
        Thread.__init__(self, name="_Recv")
        self._conn = conn
        self.myFileHandler = Logger(basename)
        print "logger initialized with basename %s, will create new file and name at 00:00UTC daily" % (basename)
        self._last_line = ''
        self._new_line = ''
        self.setDaemon(True)

    def _update_lines(self, recv):
        if recv == '\n':
            self._last_line = self._new_line
            self._new_line = ''
            return True
        else:
            self._new_line += recv
            return False

    def run(self):
        print "### _Recv running."
        while True:
            recv = self._conn.recv(1)
            newline = self._update_lines(recv)
            os.write(sys.stdout.fileno(), recv)
            self.myFileHandler.write(recv)    #writes to logger file  
            sys.stdout.flush()


class _Direct(object):
    """
    Main program.
    """

    def __init__(self, host, port):
        """
        Establishes the connection and starts the receiving thread.
        """
        print "### connecting to %s:%s" % (host, port)
        print "For automatic temperature polling (port 4002) enter autoTemp"
        print "For automatic RAS test (port 4001) enter autoRAS"
        print "For automatic PPS test (port 4003) enter autoPPS"
        print "To port cycle on RAS (port 4001) enter cycleRAS"
        print "To port cycle on PPS (port 4003) enter cyclePPS"
        self.myFileHandler = Logger(basename)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, port))
        self._bt = _Recv(self._sock)
        self._bt.start()

    def run(self):
        #        """
        #         Dispatches user commands.
        #         """
        while True:

            cmd = sys.stdin.readline()

            cmd = cmd.strip()

            if cmd == "wake":
                self.wake()

            elif cmd == "^C":
                print "### sending '%s'" % cmd
                self.send_control('c')

            elif cmd == "q":
                print "### exiting"
                break

            elif cmd == "autoTemp":
                self.automatic_control_temp()

            elif cmd == "autoRAS":
                self.automatic_control_RAS()

            elif cmd == "autoPPS":
                self.automatic_control_PPS()
            
            elif cmd == "cycleRAS":
                self.portcycle_RAS()
            
            elif cmd == "cyclePPS":
                self.portcycle_PPS()
            else:
                print "### sending '%s'" % cmd
                self.send(cmd)
                self.send('\r\n')

        self.stop()

    def wake(self):
        print "### attempting to wake"
        self.send_control('c')
        time.sleep(1.5)
        self.send_control('c')
        time.sleep(1.5)
        self.send_control('c')
        time.sleep(1.5)
        self.send_control('c')
        time.sleep(1.5)
        self.send_control('c')
        print "### five ^C sent"
        return True

    def automatic_control_temp(self):
        """
        Sends temp probe queries repeatedly until any keyed sequence is entered
        """
        print "### Automatic temperature polling mode"
        print "### To exit: input any key followed by enter"
        # The following two while loops do the same thing, however the exit strategy of the the second one,
        # utilizing a timer, is cleaner than the first, which utilizes a  hard break (thanks to Eric McRae)

        second = 0
        while True:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                stopcmd = sys.stdin.readline()
                print "### exiting polling mode"
                break
            if second == 1:
                print "Timestamp:", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
                self.myFileHandler.write(time.strftime("%Y-%m-%d %H:%M:%S UTC \n", time.gmtime()))
                self.send('$1RD')
                self.send('\r\n')
            if second == 1.25:
                self.send('$2RD')
                self.send('\r\n')
            if second == 1.50:
                self.send('$3RD')
                self.send('\r\n')
            time.sleep(.25)
            second += .25
            if second == 10:  # loop counter now set to 10s data for testing
                second = 0  # reset second counter

    def portcycle_PPS(self):
        """
        Cycles through all ports, in order to equalize pressure
        """
        print "### cycling through all ports"
        print "### To exit: input any key followed by enter"
        
        second = 0
        PPSport = 1  
        while True:
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                      stopcmd = sys.stdin.readline()
                      print "### exiting cycle"
                      break     
                if PPSport == 25:
                      print "### 24 ports cycled, exiting"
                      break
                if second == 1:           
                      self.send('PORT '+str(PPSport))
                      self.send('\r\n')                                                                                                                                                                 
                time.sleep(1)
                second += 1
                if second == 20:    
                      second = 0        
                      PPSport += 1
                      
    def portcycle_RAS(self):
        """
        Cycles through all ports, in order to equalize pressure
        """
        print "### cycling through all ports"
        print "### To exit: input any key followed by enter"
        
        second = 0
        PPSport = 1  
        while True:
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                      stopcmd = sys.stdin.readline()
                      print "### exiting rinse"
                      break     
                if PPSport == 50:
                      print "### 49 ports cycled, exiting"
                      break
                if second == 1:           
                      self.send('PORT '+str(PPSport))
                      self.send('\r\n')                                                                                                                                                                 
                time.sleep(1)
                second += 1
                if second == 20:    
                      second = 0        
                      PPSport += 1
    
    def automatic_control_RAS(self):
        """
        Simulates a sampling cycle by RAS, but never pumps on a port
        """
        print "### Test simulation of RAS started"
        print "### To exit: input any key followed by enter"

        second = 0
        while True:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                stopcmd = sys.stdin.readline()
                print "### exiting test simulation"
                break
            if second == 1:
                print "Timestamp:", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
                self.myFileHandler.write(time.strftime("%Y-%m-%d %H:%M:%S UTC \n", time.gmtime()))
                self.wake()
            if second == 18:
                self.send('CLOCK ' + time.strftime("%m/%d/%y %H:%M:%S", time.gmtime()))
                self.send('\r\n')
            if second == 20:  # actual is ~7s
                self.send('HOME')
                self.send('\r\n')
            if second == 60:  # actual is ~15s
                self.send('FORWARD 150 100 25')
                self.send('\r\n')
            if second == 260:  # actual is ~100s
                self.send('PORT 4')
            if second == 320:  # actual is ~15s
                self.send('HOME')
                self.send('\r\n')
            if second == 380:  # actual is ~350s
                self.send('FORWARD 425 75 25')
                self.send('\r\n')
            if second == 880:  # actual is ~15s
                self.send('REVERSE 75 100 25')
                self.send('\r\n')
            if second == 950:  # actual is ~50s
                self.send('SLEEP')
                self.send('\r\n')
                print "### test sample simulation complete, exiting"
                break
            time.sleep(1)
            second += 1


    def automatic_control_PPS(self):
        """
        Simulates a sampling cycle by PPS, but never pumps on a port
        """
        print "### Test simulation of PPS started"
        print "### To exit: input any key followed by enter"

        second = 0
        while True:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                stopcmd = sys.stdin.readline()
                print "### exiting test simulation"
                break
            if second == 1:
                print "Timestamp:", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
                self.myFileHandler.write(time.strftime("%Y-%m-%d %H:%M:%S UTC \n", time.gmtime()))
                self.wake()  # actual is ~7s
            if second == 18:
                self.send('CLOCK ' + time.strftime("%m/%d/%y %H:%M:%S", time.gmtime()))
                self.send('\r\n')
            if second == 20:  
                self.send('HOME')  # actual is ~20s
                self.send('\r\n')
            if second == 60:  
                self.send('FORWARD 150 100 75')  # actual is ~100s
                self.send('\r\n')
            if second == 260:  
                self.send('PORT 4')  # actual is ~7s
                self.send('\r\n')
            if second == 320:  
                self.send('HOME')  # actual is ~15s
                self.send('\r\n')
            if second == 380:  
                self.send('FORWARD 800 100 75')
                self.send('\r\n')
# uncomment below section for abbreviated PPS test, comment out for full PPS test          
            if second == 1080:  # actual is ~15s
                self.send('REVERSE 100 100 75')
                self.send('\r\n')
            if second == 1180:  # actual is ~50s
            
# uncomment below section for full PPS test            
#                 self.send('FORWARD 4000 100 75')
#             if second == 3600:  # actual is ~3000s
#                 self.send('REVERSE 100 100 75')
#             if second == 3700:  # actual is ~60s
                self.send('SLEEP')
                self.send('\r\n')
                print "### test sample simulation complete, exiting"
                break
            time.sleep(1)
            second += 1

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

    direct = _Direct(host, port)
    direct.run()

