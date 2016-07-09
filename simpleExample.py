#! /usr/bin/python

# Filename:    simpleExample.pl
# Description: Switch a Hive SmartPlug On/Off using a XBee
# Author:      James Saunders [james@saunders-family.net]
# Copyright:   Copyright (C) 2016 James Saunders
# License:     MIT
# Version:     1.0.5"

from xbee import XBee, ZigBee
import serial
import time
import sys
import pprint

# Serial Configuration
# XBEE_PORT = '/dev/tty.usbserial-A1014P7W' # MacBook Serial Port
XBEE_PORT = '/dev/ttyUSB0' # Rasberry Pi Serial Port
XBEE_BAUD = 9600
serialPort = serial.Serial(XBEE_PORT, XBEE_BAUD)

# ZigBee Profile IDs
ZDP_PROFILE_ID = '\x00\x00' # ZigBee Device Profile
ALERTME_PROFILE_ID = '\xc2\x16' # AlertMe Private Profile

# ZigBee Addressing
BROADCAST_LONG = '\x00\x00\x00\x00\x00\x00\xff\xff'
BROADCAST_SHORT = '\xff\xfe'
switchLongAddr = ''
switchShortAddr = ''

def receiveMessage(data):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)
    
    global switchLongAddr; switchLongAddr = data['source_addr_long']
    global switchShortAddr; switchShortAddr = data['source_addr']
    profileId = data['profile']
    clusterId = data['cluster']

    if (profileId == ZDP_PROFILE_ID):
        if (clusterId == '\x00\x06'):
            # Active Endpoint Request
            data = '\x00\x00'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x00', '\x00\x05', ZDP_PROFILE_ID, data)

            # Now the Match Descriptor Response
            data = '\x00\x00\x00\x00\x01\x02'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x00', '\x80\x06', ZDP_PROFILE_ID, data)

        elif (clusterId == '\x00\x06'):
            # Now there are two messages directed at the hardware code
            data = '\x11\x01\xfc'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf6', ALERTME_PROFILE_ID, data)

            # The switch has to receive both of these to stay joined
            data = '\x19\x01\xfa\x00\x01'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

    elif (profileId == ALERTME_PROFILE_ID):
        if (clusterId == '\x00\xee'):
            clusterCmd = data['rf_data'][2]
            if (clusterCmd == '\x80'):
                if (ord(data['rf_data'][3]) & 0x01):
                    state = "ON"
                else:
                    state = "OFF"
                print "Switch State:", state

def sendMessage(destLongAddr, destShortAddr, srcEndpoint, destEndpoint, clusterId, profileId, data):
    zb.send('tx_explicit',
        dest_addr_long = destLongAddr,
        dest_addr = destShortAddr,
        src_endpoint = srcEndpoint,
        dest_endpoint = destEndpoint,
        cluster = clusterId,
        profile = profileId,
        data = data
    )

# Create ZigBee library API object, which spawns a new thread
zb = ZigBee(serialPort, callback = receiveMessage)

switchState = True
while True:
    try:
        time.sleep(1.00)

        if(switchLongAddr != ''):
            # Toggle On and Off
            switchState = not switchState
            data = '\x11\x00\x02\x00\x01' if switchState else '\x11\x00\x02\x01\x01' 
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

        else:
            # Send out initial broadcast to provoke a response,
            # So we can then ascertain the switch address
            data = '\x12' + '\x01'
            sendMessage(BROADCAST_LONG, BROADCAST_SHORT, '\x00', '\x00', '\x00\x32', ZDP_PROFILE_ID, data)

    except KeyboardInterrupt:
        print "Keyboard Interrupt"
        break

    except:
        print "Unexpected Error:", sys.exc_info()[0], sys.exc_info()[1]
        break

# Close up shop
print "Closing Serial Port"
zb.halt()
serialPort.close()
