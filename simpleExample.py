#! /usr/bin/python

from xbee import XBee, ZigBee
import serial
import time
import sys
import pprint

# ZigBee Addressing
broadcastLongAddr = '\x00\x00\x00\x00\x00\x00\xff\xff'
broadcastShortAddr = '\xff\xfe'
switchLongAddr = ''
switchShortAddr = ''

# ZigBee Profile IDs
ZDP_PROFILE_ID = '\x00\x00' # ZigBee Device Profile
ALERTME_PROFILE_ID = '\xc2\x16' # AlertMe Private Profile

# Serial Configuration
XBEE_PORT = '/dev/tty.usbserial-A1014P7W' # MacBook Serial Port
# XBEE_PORT = '/dev/ttyUSB0' # Rasberry Pi Serial Port
XBEE_BAUD = 9600
serialPort = serial.Serial(XBEE_PORT, XBEE_BAUD, timeout=1)

def sendMessage(dest_addr_long, dest_addr, src_endpoint, dest_endpoint, cluster, profile, data):
    zb.send('tx_explicit',
        dest_addr_long=dest_addr_long,
        dest_addr=dest_addr,
        src_endpoint=src_endpoint,
        dest_endpoint=dest_endpoint,
        cluster=cluster,
        profile=profile,
        data=data
    )

def receiveMessage(data):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)
    
    global switchLongAddr
    global switchShortAddr
    switchLongAddr = data['source_addr_long']
    switchShortAddr = data['source_addr']
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

# Create ZigBee library API object, which spawns a new thread
zb = ZigBee(serialPort, callback = receiveMessage)

state = 1
while True:
    try:
        time.sleep(1.00)

        if(switchLongAddr != ''):
            # Toggle On and Off
            if(state == 1):
                databytes = '\x00\x01'
                state = 0
            else:
                databytes = '\x01\x01'
                state = 1
        
            data = '\x11\x00' + '\x02' + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

        else:
            data = '\x12' + '\x01'
            sendMessage(broadcastLongAddr, broadcastShortAddr, '\x00', '\x00', '\x00\x32', ZDP_PROFILE_ID, data)

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
