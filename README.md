cabled
======

RSN Cabled Instrument Loggers for OOI EA

This folder contains the python modules used to launch logged socket
connections to instruments, some with automated command and control. If no
automation is required/desired use one of the basic logger modules for either
daily or hourly incremental file creation.

The syntax for using any of these scripts is:

    python SCRIPT.py -a IPADDRESS -p PORT -b basename -i increment

The convention for basename on the subsea network is:

    /data/INSTRUMENT_IP.IP.IP.IP_PORT

where /data/.. writes to the campus network data folder

Example:

    python adcp.py -a 10.180.80.178 -p 2101 -b /data/ADCP_10.180.80.178_2101 -i hourly

    python basic_logger.py -a 10.180.80.175 -p 2104 -b /data/CTD_10.180.80.175_2104 -i hourly


A script can be written to startup the appropriate logger/driver script with
the correctly configured argument list. (Don’t forget to chmod +x this file.)
See test.run for an example.

Requires:

    python 2.7.8
    numpy
    apscheduler
    