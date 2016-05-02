#! /usr/bin/python

from xbee import ZigBee
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
XBEE_PORT = '/dev/tty.usbserial-A1014P7W'
# XBEE_PORT = '/dev/ttyUSB0' # Rasberry Pi Serial Port
XBEE_BAUD = 9600
serialPort = serial.Serial(XBEE_PORT, XBEE_BAUD)

pp = pprint.PrettyPrinter(indent=4)

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
    # Print the data
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
            print "\tDevice Announce Message"

        elif (clusterId == '\x80\x05'):
            # Active Endpoint Response.
            # This message tells you what the device can do, but it isn't
            # constructed correctly to match what the switch can do according
            # to the spec.  This is another message that gets it's response
            # after I receive the Match Descriptor.
            print "\tActive Endpoint Response"

        elif (clusterId == '\x00\x06'):
            # Match Descriptor Request.
            # This is the point where I finally respond to the switch.
            # Several messages are sent to cause the switch to join with
            # the controller at a network level and to cause it to regard
            # this controller as valid.

            # First the Active Endpoint Request
            data = '\x00\x00'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x00', '\x00\x05', ZDP_PROFILE_ID, data)
            print "\tSent Active Endpoint Request"

            # Now the Match Descriptor Response
            data = '\x00\x00\x00\x00\x01\x02'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x00', '\x80\x06', ZDP_PROFILE_ID, data)
            print "\tSent Match Descriptor"

        elif (clusterId == '\x00\x06'):
            # Now there are two messages directed at the hardware
            # code (rather than the network code). The switch has to
            # receive both of these to stay joined.
            data = '\x11\x01\xfc'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf6', ALERTME_PROFILE_ID, data)
            data = '\x19\x01\xfa\x00\x01'
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

            print "\tSent Hardware Join Messages"

        elif (clusterId == '\x802'):
            # Broadcast Response.
            print "\tBroadcasting Route Record Response"

        else:
            print "\tUnimplemented Cluster ID"

    elif (profileId == ALERTME_PROFILE_ID):
        print "AlertMe Profile ID"

        clusterCmd = data['rf_data'][2]

        if (clusterId == '\x00\xef'):
            if (clusterCmd == '\x81'):
                print "\tInstantaneous Power:",
                print ord(data['rf_data'][3]) + (ord(data['rf_data'][4]) * 256)

            elif (clusterCmd == '\x82'):
                print "\tMinute Stats"
                print "\t\tUsage:",
                usage = (ord(data['rf_data'][3]) +
                         (ord(data['rf_data'][4]) * 256) +
                         (ord(data['rf_data'][5]) * 256 * 256) +
                         (ord(data['rf_data'][6]) * 256 * 256 * 256))
                print usage, "Watt Seconds"
                print "\t\tUp Time:",
                upTime = (ord(data['rf_data'][7]) +
                          (ord(data['rf_data'][8]) * 256) +
                          (ord(data['rf_data'][9]) * 256 * 256) +
                          (ord(data['rf_data'][10]) * 256 * 256 * 256))
                print upTime, "Seconds"

        elif (clusterId == '\x00\xf0'):
            if (clusterCmd == '\xfb'):
                print "\tMystery Value:",
                print ord(data['rf_data'][3]) + (ord(data['rf_data'][4]) * 256)
            else:
                print "\tUnimplemented Cluster Command", hex(ord(clusterCmd))

        elif (clusterId == '\x00\xf6'):
            if (clusterCmd == '\xfd'):
                print "\tRSSI Value:",
                print ord(data['rf_data'][3])
            elif (clusterCmd == '\xfe'):
                print "\tVersion Information"
                print "\t\tManufacturer:", str(data['rf_data'][22:len(data['rf_data'])]).replace('\t', ' ').replace('\n', ' ')
                print "\t\tSoftware:", ord(data['rf_data'][3]) + (ord(data['rf_data'][4]) * 256)

            else:
                print "\tUnimplemented Cluster Command", hex(ord(clusterCmd))

        elif (clusterId == '\x00\xee'):
            if (clusterCmd == '\x80'):
                print "\tSwitch is:",
                if (ord(data['rf_data'][3]) & 0x01):
                    print "ON"
                else:
                    print "OFF"
            else:
                print "\tUnimplemented Cluster Command", hex(ord(clusterCmd))

        else:
            print "\tUnimplemented Cluster ID"

    else:
        print "Unknown Profile ID"

# Create XBee library API object, which spawns a new thread
zb = ZigBee(serialPort, callback = receiveMessage)

print "Select Command:"
print "\t0 Switch Off"
print "\t1 Switch On"
print "\t2 Version Data"
print "\t3 Switch Status"
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
            # Note 2 commands?
            print "Turn Switch Off"
            clusterCmd = '\x01'
            databytes = '\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

            clusterCmd = '\x02'
            databytes = '\x00\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '1'):
            # Turn Switch On
            # Note 2 commamds?
            print "Turn Switch On"
            clusterCmd = '\x01'
            databytes = '\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

            clusterCmd = '\x02'
            databytes = '\x01\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '2'):
            # Version Data
            # It's a combination of data and text
            print "Version Data"
            clusterCmd = '\xfc'
            databytes = '\x00\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf6', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '3'):
            # Switch Status
            # This command causes a message return holding the state of the switch.
            print "Switch Status"
            clusterCmd = '\x01'
            databytes = '\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xee', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '4'):
            # Restore Normal Mode
            # Run after one of the mode changes that follow.
            print "Restore Normal Mode"
            clusterCmd = '\xfa'
            databytes = '\x00\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '5'):
            # Range Test
            # Periodic double blink, no control, sends RSSI, no remote control
            print "Range Test"
            clusterCmd = '\xfa'
            databytes = '\x01\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '6'):
            # Locked Mode
            # Switch can't be controlled locally, no periodic data
            print "Locked Mode"
            clusterCmd = '\xfa'
            databytes = '\x02\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '7'):
            # Silent mode
            # No periodic data, but switch is controllable locally
            print "Silent Mode"
            clusterCmd = '\xfa'
            databytes = '\x03\x01'
            data = '\x11\x00' + clusterCmd + databytes
            sendMessage(switchLongAddr, switchShortAddr, '\x00', '\x02', '\x00\xf0', ALERTME_PROFILE_ID, data)

        elif (str1[0] == '8'):
            # Broadcast
            print "Broadcasting Route Record Request"
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