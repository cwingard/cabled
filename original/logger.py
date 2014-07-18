#!/usr/bin/env python

# File: logger.py
# Description: writes strings to a file, changes file name at midnight

from time import gmtime, strftime, struct_time

class Logger( object ):
    def __init__(self, baseFileName):
        """
        Init base filename string and clear final filename
        """
        ## the constant portion of the filename
        self.baseFileName = baseFileName
        ## the currentfileName
        self.fileName = ""
        ## used to remember what day we last were working with, normally 1 - 31
        self.dayOfMonth = 0     

        self.checkMakeNewFileName() # this will create our first filename

    def write( self, string ):
        """
        Check to see if we want to change the filename, then open the file, write the string, and close
        """
        self.checkMakeNewFileName()
        file = open( self.fileName, "ab" )
        file.write( string )
        file.close()


    def checkMakeNewFileName( self ):
        """
        Routine to check if we need a new filename and to create one if so
        """
        timevalue = gmtime()
        # if day of month has change or this is the first time (dayOfMonth == 0)
        if self.dayOfMonth != struct_time( timevalue ).tm_mday:   #tested w/ tm_hour
            # create a new filename string
            self.fileName = self.baseFileName + "_" + strftime("%Y%m%d", timevalue) + "_UTC.txt"   #_%H%M%S
            # update current day of month
            self.dayOfMonth = struct_time( timevalue ).tm_mday   #tested w/ tm_hour


