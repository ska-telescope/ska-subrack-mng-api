
import sys
from bsp.management import *
from optparse import OptionParser
from netifaces import AF_INET
import netifaces as ni
from functools import reduce

CPLD_IP_OFFSET = 0x00010028
CPLD_NETMASK_OFFSET = 0x0001002c
CPLD_GATEWAY_OFFSET = 0x00010030

def int2ip(value):
    ip = str((value >> 24)&0xff)
    ip += "."
    ip += str((value >> 16)&0xff)
    ip += "."
    ip += str((value >> 8)&0xff)
    ip += "."
    ip += str((value >> 0)&0xff)
    return ip

def get_mac_from_eep(inst, phy_addr = 0xA0):
    mac=[]
    for i in range(eep_sec["MAC"]["size"]):
        rdval=inst.bsp.eep_rd8(eep_sec["MAC"]["offset"]+i, phy_addr)
        mac.append(rdval)
    return mac


def nuple2mac(mac):
    mac_str = ""
    for i in range(0,len(mac)-1):
        mac_str += '{0:02x}'.format(mac[i])+":"
    mac_str += '{0:02x}'.format(mac[len(mac)-1])
    return mac_str

def write_string(inst,offset,string):
    #print string
    #print len(string)
    addr = offset
    for i in range(len(string)):
        #print string[i]
        inst.bsp.eep_wr8(addr, ord(string[i]))
        addr += 1
    #print "ord(\"\\n\"): " + str(ord("\n"))
    inst.bsp.eep_wr8(addr, ord("\n"))

def read_string(inst,offset,max_len = 32):
    addr = offset
    string = ""
    for i in range(max_len):
        byte = inst.bsp.eep_rd8(addr)
        if byte == ord("\n") or byte == 0xff :
            break
        string += chr(byte)
        addr += 1
    return string

BOARD_MODE = {
"subrack": 1,
"cabinet": 2,
}

eep_sec={
"ip_address":       {"offset":  0x0, "size":  4, "name":"ip_address"      },
"netmask":          {"offset":  0x4, "size":  4, "name":"netmask"         },
"gateway":          {"offset":  0x8, "size":  4, "name":"gateway"         },
"password":         {"offset":  0xc, "size":  4, "name":"password"        },
"SN":               {"offset": 0x20, "size": 32, "name":"SN"              },
"PN":               {"offset": 0x40, "size": 32, "name":"PN"              },
"BOARD_MODE":       {"offset": 0x60, "size":  1, "name":"BOARD_MODE"      },# 1 subrack, 2 cabinet
"HARDWARE_REV":     {"offset": 0x61, "size":  3, "name":"HARDWARE_REV"    },# v00.00.00
"SITE_LOCATION":    {"offset": 0x64, "size":  2, "name":"SITE_LOCATION"   },
"CABINET_LOCATION": {"offset": 0x66, "size":  2, "name":"CABINET_LOCATION"},
"SUBRACK_LOCATION": {"offset": 0x68, "size":  2, "name":"SUBRACK_LOCATION"},
"SLOT_LOCATION":    {"offset": 0x6a, "size":  2, "name":"SLOT_LOCATION"   },
"MAC":              {"offset": 0xFA, "size":  6, "name":"MAC"             },#READ-ONLY
}



if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("--eep",
        action="store_true",
        dest="eep",
        default=False,
        help="Store network configuration in BOARD EEPROM")
    parser.add_option("--volatile",
        action="store_true",
        dest="volatile",
        default=False,
        help="Store network configuration in volatile registers")
    parser.add_option("--get",
        action="store_true",
        dest="get",
        default=False,
        help="Get information instead of set")
    parser.add_option("--boot_sel",
        dest="boot_sel",
        default="",
        help="BOARD boot_sel (b0 = krn, b1 = fs) (eep options required)")
    parser.add_option("--ip",
        dest="ip",
        default="",
        help="BOARD IP Address (volatile or eep options required)")
    parser.add_option("--netmask",
        dest="netmask",
        default="",
        help="BOARD IP Netmask  (volatile or eep options required)")
    parser.add_option("--gateway",
        dest="gateway",
        default="",
        help="BOARD IP Gateway  (volatile or eep options required)")
    parser.add_option("--sn",
        dest="sn",
        default="",
        help="Serial number to be written into EEPROM")
    parser.add_option("--pn",
        dest="pn",
        default="",
        help="Part number to be written into EEPROM")
    parser.add_option("--hw_rev",
        dest="hw_rev",
        default="",
        help="Hardware revision to be written into EEPROM (example 1.1 or 1.1.3)")
    parser.add_option("--mode",
        dest="mode",
        default="",
        help="Management mode to be written into EEPROM (SUBRACK|CABINET)")
    parser.add_option("--location",
        dest="location",
        default="",
        help="LOCATION to be written into EEPROM (SITE:CABINET:SUBRACK:SLOT)")
    parser.add_option("-p", "--udp_port",
        dest="udp_port",
        default="10000",
        help="BOARD UCP UDP port")
    parser.add_option("--host_ip",
        dest="host_ip",
        default="",
        help="Host ip address where to scan for BOARDs")
    parser.add_option("--unicast_ip",
        dest="unicast_ip",
        default="",
        help="Select board from current ip address")
    parser.add_option("--force",
        action="store_true",
        dest="force",
        default=False,
        help="forse update, no warning request")



    (options, args) = parser.parse_args()

    if options.get == False:
        print()
        print ("""-----------------------------------------------------------------------
        -- WARNING! This script sets the specified network configuration to all
        -- MANAGEMENT boards in the local network! Make sure to have a direct cable
        -- connection to the board you want to set!
        -----------------------------------------------------------------------""")
        print()
        if options.ip != "" or options.netmask != "" or options.gateway != "" or options.boot_sel != "":
            print ("The new IP configuration on the MANAGEMENT board will be:")
        if options.ip != "":
            print ("IP\t\t" + options.ip)
        if options.netmask != "":
            print ("Netmask\t\t" + options.netmask)
        if options.gateway != "":
            print ("Gateway\t\t" + options.gateway)
        if options.boot_sel != "":
            print ("BOOT_SEL\t\t" + str(int(options.boot_sel,16)&0xff))
        print()
        if options.force==False:
            if input("Press Y to continue, any other key to exit. ") != "Y":
                exit (0)
    #print
    #print "List of available IP addresses:"
    #print
    idx = 0
    ips = []
    for intf in ni.interfaces():
        try:
            if ni.ifaddresses(intf)[AF_INET][0]['addr'] != "127.0.0.1":
                #print "[" + str(idx) + "] " + ni.ifaddresses(intf)[AF_INET][0]['addr']
                ips.append(ni.ifaddresses(intf)[AF_INET][0]['addr'])
                idx += 1
        except:
            pass

    print()
    if options.host_ip == "":
        print()
        print ("List of available IP addresses:")
        for i in range(len(ips)):
            print ("[" + str(i) + "] " + ips[i])
        idx = input("Select the IP address, this selects the output interface of broadcast UCP packets. ")
        try:
            idx = int(idx)
        except:
            print ("What are you doing? I have to input a number!")
            sys.exit(1)
        if not idx in range(len(ips)):
            print("The specified interface doesn't exist!")
        else:
            print("Selected IP: " + ips[idx])
    else:
        idx = -1
        i = 0
        for ip in ips:
            if ip == options.host_ip:
                idx = i
                break
            i += 1
        if idx == -1:
            print("IP addresses not found: " + options.host_ip)
            print("List of available IP addresses:")
            for i in range(len(ips)):
                print ("[" + str(i) + "] " + ips[i])
            exit(-1)


    if options.unicast_ip=="":
        inst = MANAGEMENT(ip="255.255.255.255", port=options.udp_port, timeout=5, host_ip=ips[idx])
    else:
        inst = MANAGEMENT(ip=options.unicast_ip, port=options.udp_port, timeout=5, host_ip=ips[idx])

    ip2int = lambda ip: reduce(lambda a, b: (a << 8) + b, map(int, ip.split('.')), 0)

    if options.get == True:
        print()
        print ("==== EEP Settings ==========================")
        inst.bsp.i2c_set_passwd()
        print (eep_sec["SN"]["name"]+"\t\t" + read_string(inst,eep_sec["SN"]["offset"]))
        print (eep_sec["PN"]["name"]+"\t\t" + read_string(inst,eep_sec["PN"]["offset"]))
        mode = inst.bsp.eep_rd8(eep_sec["BOARD_MODE"]["offset"])
        if mode == BOARD_MODE['subrack']:
            print (eep_sec["BOARD_MODE"]["name"]+"\tSUBRACK")
        elif mode == BOARD_MODE['cabinet']:
            print (eep_sec["BOARD_MODE"]["name"]+"\tCABINET")
        else:
            print (eep_sec["BOARD_MODE"]["name"]+"\tUNKNOWN")
        print (eep_sec["HARDWARE_REV"]["name"]+"\tv" + str(inst.bsp.eep_rd8(eep_sec["HARDWARE_REV"]["offset"])) +"."+ str(inst.bsp.eep_rd8(eep_sec["HARDWARE_REV"]["offset"]+1)) +"."+str(inst.bsp.eep_rd8(eep_sec["HARDWARE_REV"]["offset"]+2)))
        LOCATION=[]
        LOCATION.append(inst.bsp.eep_rd16(eep_sec["SITE_LOCATION"]["offset"]))
        LOCATION.append(inst.bsp.eep_rd16(eep_sec["CABINET_LOCATION"]["offset"]))
        LOCATION.append(inst.bsp.eep_rd16(eep_sec["SUBRACK_LOCATION"]["offset"]))
        LOCATION.append(inst.bsp.eep_rd16(eep_sec["SLOT_LOCATION"]["offset"]))
        print ("LOCATION\t" +str(LOCATION[0])+":"+str(LOCATION[1])+":"+str(LOCATION[2])+":"+str(LOCATION[3]))
        print ("MAC (CPLD)\t" + nuple2mac(get_mac_from_eep(inst)))
        print ("MAC (CPU)\t" + nuple2mac(get_mac_from_eep(inst,0xA2)))
        print ("IP\t\t" + int2ip(inst.bsp.eep_rd32(eep_sec["ip_address"]["offset"])))
        print ("Netmask\t\t" + int2ip(inst.bsp.eep_rd32(eep_sec["netmask"]["offset"])))
        print ("Gateway\t\t" + int2ip(inst.bsp.eep_rd32(eep_sec["gateway"]["offset"])))
        inst.bsp.i2c_remove_passwd()
        print ("BOOT_SEL\t" + hex(inst.bsp.get_field('BOOT_SEL')))
        print()
        print ("==== Volatile Settings =====================")
        print ("IP\t\t" + int2ip(inst.rmp.rd32(CPLD_IP_OFFSET)))
        print ("Netmask\t\t" + int2ip(inst.rmp.rd32(CPLD_NETMASK_OFFSET)))
        print ("Gateway\t\t" + int2ip(inst.rmp.rd32(CPLD_GATEWAY_OFFSET)))


        exit(0)

    if options.volatile == True:
        if options.ip != "":
            inst.rmp.wr32(CPLD_IP_OFFSET, ip2int(options.ip))
        if options.netmask != "":
            inst.rmp.wr32(CPLD_NETMASK_OFFSET, ip2int(options.netmask))
        if options.gateway != "":
            inst.rmp.wr32(CPLD_GATEWAY_OFFSET, ip2int(options.gateway))

    if options.eep == True:
        #storing network configuration in EEPROM

        if options.boot_sel != "":
            inst.bsp.set_field('BOOT_SEL',int(options.boot_sel,16)&0xff)

        if options.ip != "":
            inst.bsp.i2c_set_passwd()
            inst.bsp.eep_wr32(0x0, ip2int(options.ip))
            inst.bsp.i2c_remove_passwd()

        if options.netmask != "":
            inst.bsp.i2c_set_passwd()
            inst.bsp.eep_wr32(0x4, ip2int(options.netmask))
            inst.bsp.i2c_remove_passwd()

        if options.gateway != "":
            inst.bsp.i2c_set_passwd()
            inst.bsp.eep_wr32(0x8, ip2int(options.gateway))
            inst.bsp.i2c_remove_passwd()

        if options.sn != "":
            inst.bsp.i2c_set_passwd()
            write_string(inst,eep_sec["SN"]["offset"],options.sn)
            inst.bsp.i2c_remove_passwd()

        if options.pn != "":
            inst.bsp.i2c_set_passwd()
            write_string(inst,eep_sec["PN"]["offset"],options.pn)
            inst.bsp.i2c_remove_passwd()

        if options.hw_rev != "":
            #hw_rev=map(int,options.hw_rev.split("."))
            hw_rev = list(map(int, options.hw_rev.split(".")))
            if len(hw_rev) == 2:
                hw_rev.append(0)
            if len(hw_rev) != 3:
                print ("Error - hw_rev malformed (example 1.1 or 1.1.3)")
                exit(-1)
            inst.bsp.i2c_set_passwd()
            inst.bsp.eep_wr8(eep_sec["HARDWARE_REV"]["offset"]+0, hw_rev[0])
            inst.bsp.eep_wr8(eep_sec["HARDWARE_REV"]["offset"]+1, hw_rev[1])
            inst.bsp.eep_wr8(eep_sec["HARDWARE_REV"]["offset"]+2, hw_rev[2])
            inst.bsp.i2c_remove_passwd()

        if options.location != "":
            location=list(map(int,options.location.split(":")))
            if len(location) != 4:
                print ("Error - LOCATION (SITE:CABINET:SUBRACK:SLOT)")
                exit(-1)
            inst.bsp.i2c_set_passwd()
            inst.bsp.eep_wr16(eep_sec["SITE_LOCATION"]["offset"], location[0])
            inst.bsp.eep_wr16(eep_sec["CABINET_LOCATION"]["offset"], location[1])
            inst.bsp.eep_wr16(eep_sec["SUBRACK_LOCATION"]["offset"], location[2])
            inst.bsp.eep_wr16(eep_sec["SLOT_LOCATION"]["offset"], location[3])
            inst.bsp.i2c_remove_passwd()

        if options.mode != "":
            if options.mode == "CABINET" or options.mode == "SUBRACK":
                if options.mode == "CABINET":
                    mode = BOARD_MODE['cabinet']
                else:
                    mode = BOARD_MODE['subrack']
            else:
                print ("Error - mamangement mode malformed (SUBRACK|CABINET)")
                exit(-1)
            inst.bsp.i2c_set_passwd()
            inst.bsp.eep_wr8(eep_sec["BOARD_MODE"]["offset"]+0, mode)
            inst.bsp.i2c_remove_passwd()


        #read configuration from EEPROM and set volatile registers
        #inst.rmp.wr32(0x00010018,1)

inst.disconnect()
