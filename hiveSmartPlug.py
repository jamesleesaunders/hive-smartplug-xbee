#! /usr/bin/python

from xbee import ZigBee
from struct import *
import serial
import time
import sys
import pprint

# Zigbee Addressing
BROADCAST = '\x00\x00\x00\x00\x00\x00\xff\xff'
BROADCAST_SHORT = '\xff\xfe'
switchLongAddr = '\x00'
switchShortAddr = '\x00'

# Zigbee Profile IDs
ZDP_PROFILE_ID = '\x00\x00' # Zigbee Device Profile
ALERTME_PROFILE_ID = '\xc2\x16' # AlertMe Private Profile

# Serial Configuration
XBEE_PORT = '/dev/tty.usbserial-A1014P7W' # MacBook Serial Port
# XBEE_PORT = '/dev/ttyUSB0' # Rasberry Pi Serial Port
XBEE_BAUD = 9600
serialPort = serial.Serial(XBEE_PORT, XBEE_BAUD)

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
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(data)

    global switchLongAddr
    global switchShortAddr
    switchLongAddr = data['source_addr_long']
    switchShortAddr = data['source_addr']
    profileId = data['profile']
    clusterId = data['cluster']

    if (profileId == ZDP_PROFILE_ID):
        print "Zigbee Device Profile ID"

        if (clusterId == '\x13'):
            # Device Announce Message.
            # Due to timing problems with the switch itself, I don't
            # respond to this message, I save the response for later after the
            # Match Descriptor request comes in.  You'll see it down below.
            print "Device Announce Message"

        elif (clusterId == '\x80\x05'):
            # Active Endpoint Response.
            # This message tells you what the device can do, but it isn't
            # constructed correctly to match what the switch can do according
            # to the spec. This is another message that gets it's response
            # after I receive the Match Descriptor below.
            print "Active Endpoint Response"

        elif (clusterId == '\x802'):
            # Route Record Response
            print "Broadcasting Route Record Response"

        elif (clusterId == '\x00\x06'):
            # Match Descriptor Request.
            # This is the point where I finally respond to the switch.
            # Several messages are sent to cause the switch to join with
            # the controller at a network level and to cause it to regard
            # this controller as valid.

            # First the Active Endpoint Request
            data = '\x00\x00'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x00', '\x00\x05', ZDP_PROFILE_ID, data)
            print "Sent Active Endpoint Request"

            # Now the Match Descriptor Response
            data = '\x00\x00\x00\x00\x01\x02'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x00', '\x80\x06', ZDP_PROFILE_ID, data)
            print "Sent Match Descriptor"

        elif (clusterId == '\x00\x06'):
            # Now there are two messages directed at the hardware
            # code (rather than the network code).
            data = '\x11\x01\xfc'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf6', ALERTME_PROFILE_ID, data)

            # The switch has to receive both of these to stay joined.
            data = '\x19\x01\xfa\x00\x01'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)
            print "Sent Hardware Join Messages"

        else:
            print "Minor Error: Unrecognised Cluster ID"

    elif (profileId == ALERTME_PROFILE_ID):
        # print "AlertMe Profile ID"

        clusterCmd = data['rf_data'][2]

        if (clusterId == '\x00\xef'):
            if (clusterCmd == '\x81'):
                print "Current Power"
                # '\tj\x81\x00\x00'
                values = dict(zip(
                    ('clusterCmd', 'Power'),
                    unpack('< 2x s H', data['rf_data'])
                ))
                print "\tInstantaneous Power:", values['Power']

            elif (clusterCmd == '\x82'):
                print "Usage Stats"
                # '\t\x00\x82Z\xbb\x04\x00\xdf\x86\x04\x00\x00'
                values = dict(zip(
                    ('clusterCmd', 'Usage', 'UpTime'),
                    unpack('< 2x s I I 1x', data['rf_data'])
                ))
                print "\tUsage (watt-seconds):", values['Usage']
                print "\tUsage (watt-hours):", values['Usage'] * 0.000277778
                print "\tUp Time (seconds):", values['UpTime']

            else:
                print "Minor Error: Unrecognised Cluster Command"

        elif (clusterId == '\x00\xf6'):
            if (clusterCmd == '\xfd'):
                print "Range Test"
                # '\t+\xfd\xc5w'
                values = dict(zip(
                    ('clusterCmd', 'RSSI'),
                    unpack('< 2x s B 1x', data['rf_data'])
                ))
                print "\tRSSI Value:", values['RSSI']

            elif (clusterCmd == '\xfe'):
                print "Version Information"
                # '\tq\xfeMN\xf8\xb9\xbb\x03\x00o\r\x009\x10\x07\x00\x00)\x00\x01\x0bAlertMe.com\tSmartPlug\n2013-09-26'
                values = dict(zip(
                    ('clusterCmd', 'Version', 'Manu'),
                    unpack('< 2x s H 17x 32s', data['rf_data'])
                ))
                print "\tVersion:", values['Version']
                print "\tManufacturer:", values['Manu'].split()[0]
                print "\tModel:", values['Manu'].split()[1]
                print "\tDate:", values['Manu'].split()[2]

            else:
                print "Minor Error: Unrecognised Cluster Command"

        elif (clusterId == '\x00\xee'):
            print "Switch Status"
            if (clusterCmd == '\x80'):
                # '\th\x80\x07\x01'
                # '\th\x80\x06\x00'
                if (ord(data['rf_data'][3]) & 0x01):
                    state = "ON"
                else:
                    state = "OFF"
                print "\tSwitch is:", state

            else:
                print "Minor Error: Unrecognised Cluster Command"

        elif (clusterId == '\x00\xf0'):
            if (clusterCmd == '\xfb'):
                print "Mystery Cluster Command"
                # '\t\x00\xfb\x1f#\xe9\xa2\x01\x10\x10\x1c\x02\xe2\xff\x01\x00'
                # Needs more investigation as to what these values are
                values = dict(zip(
                    ('clusterCmd', 'mysteryVal'),
                    unpack('< 2x s H 11x', data['rf_data'])
                ))
                print "\tUnknown Value:", values['mysteryVal']

            else:
                print "Minor Error: Unrecognised Cluster Command"

        else:
            print "Minor Error: Unrecognised Cluster ID"

    else:
        print "Minor Error: Unrecognised Profile ID"

# Create XBee library API object, which spawns a new thread
zb = ZigBee(serialPort, callback = receiveMessage)

print "Select Command:"
print "\t0 Switch Off"
print "\t1 Switch On"
print "\t2 Switch Status"
print "\t3 Version Data"
print "\t4 Restore Normal Mode"
print "\t5 Range Test"
print "\t6 Locked Mode"
print "\t7 Silent Mode"
print "\t8 Broadcast"

while True:
    try:
        time.sleep(0.001)
        str1 = raw_input("")

        if (str1[0] == '0'):
            # Turn Switch Off
            clusterCmd = '\x02'
            databytes = '\x00\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '1'):
            # Turn Switch On
            clusterCmd = '\x02'
            databytes = '\x01\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '2'):
            # Switch Status
            # This command causes a message return holding the state of the switch.
            clusterCmd = '\x01'
            databytes = '\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '3'):
            # Version Data
            # It's a combination of data and text
            clusterCmd = '\xfc'
            databytes = '\x00\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf6', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '4'):
            # Restore Normal Mode
            # Run after one of the mode changes that follow.
            clusterCmd = '\xfa'
            databytes = '\x00\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '5'):
            # Range Test
            # Periodic double blink, no control, sends RSSI, no remote control
            clusterCmd = '\xfa'
            databytes = '\x01\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '6'):
            # Locked Mode
            # Switch can't be controlled locally, no periodic data
            clusterCmd = '\xfa'
            databytes = '\x02\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '7'):
            # Silent mode
            # No periodic data, but switch is controllable locally
            clusterCmd = '\xfa'
            databytes = '\x03\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '8'):
            # Broadcast
            data = '\x12' + '\x01'
            sendMessage(BROADCAST, BROADCAST_SHORT, '\x00', '\x00', '\x00\x32', ZDP_PROFILE_ID, data)

        else:
            # Unrecognised Option
            print "Unknown Command"

    except IndexError:
        print "No Command"

    except KeyboardInterrupt:
        print "Keyboard Interrupt"
        break

    except NameError as e:
        print "Name Error:",
        print e.message.split("'")[1]

    except:
        print "Unexpected Error:", sys.exc_info()[0]
        break

# Close up shop
print "Closing Serial Port"
zb.halt()
serialPort.close()