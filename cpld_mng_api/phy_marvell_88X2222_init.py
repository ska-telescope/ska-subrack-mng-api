__author__ = 'Gabriele Sorrenti'
"""
import os

import sys
sys.path.append("../")
from optparse import OptionParser
from t_common import *

import netproto.rmp as rmp
import sys
import os
import socket
import struct
import binascii
import time
sys.path.append("../")
import config.manager as config_man
from bsp.tpm import *
"""


from sys import exit
import logging
import os
from bsp.management import *
import time

ba = 0x60000 #MDIO baseaddress

def wr(address,value):
	#print "WR "+hex(address)+"-"+hex(value)
	mng[address] = value

def rd(address):
	value=None
	value = mng[address]
	#if value is not None:
	#	print "RD "+hex(address)+"-"+hex(value)
	#else:
	#	print "RD "+hex(address)+"-"+"Dummy"
	return value


def read45(mux, phy_adr, device, register):
	wr(ba + 0, ((0x3 & mux) << 10) | ((0x1f & phy_adr) << 5) | (0x1f & device))
	wr(ba + 4, register)
	value = rd(ba + 0x18) & 0xffff
	# print "read45 " +hex(mux)+", "+hex(phy_adr)+", "+hex(device)+", "+hex(register)+", "+hex(value)
	return value


def write45(mux, phy_adr, device, register, value):
	# print "write45 " +hex(mux)+", "+hex(phy_adr)+", "+hex(device)+", "+hex(register)+", "+hex(value)
	wr(ba + 0, ((0x3 & mux) << 10) | ((0x1f & phy_adr) << 5) | (0x1f & device))
	wr(ba + 4, register)
	wr(ba + 0x18, value)


def read22(mux, phy_adr, register):
	wr(ba + 0, 0xc000 | ((0x3 & mux) << 10) | ((0x1f & phy_adr) << 5))
	wr(ba + 4, register)
	value = rd(ba + 0x08) & 0xffff
	print("read22 " + hex(mux) + ", " + hex(phy_adr) + ", " + hex(register) + ", " + hex(value))
	return value


def write22(mux, phy_adr, register, value):
	print("write22 " + hex(mux) + ", " + hex(phy_adr) + ", " + hex(register) + ", " + hex(value))
	wr(ba + 0, 0xc000 | ((0x3 & mux) << 10) | ((0x1f & phy_adr) << 5))
	wr(ba + 4, register)
	wr(ba + 0x08, value)


def readmodifywrite(mux, phy_adr, device, register, value, select):
	read_value = read45(mux, phy_adr, device, register)
	write_value = (value & select) | (read_value & ~select)
	write45(mux, phy_adr, device, register, write_value)


# test to acces switches
# for mux in [2]:
#	print " === MUX " + str(mux) + " ==="
#	for i in range(11):
#		print hex(i) + " " +hex(read22(mux,0,i)&0xffff)
# exit(0)

port_status_reg = {'name': "Port Status", 'offset': 0x0, 'fields': [
	["TxPause En", 15, 0x1],
	["RxPause En", 14, 0x1],
	["PHYDetect", 12, 0x1],
	["Link", 11, 0x1],
	["Duplex", 10, 0x1],
	["Speed", 8, 0x3],
	["DuplexFixed", 7, 0x1],
	["EEEEnabled", 6, 0x1],
	["TxPaused", 5, 0x1],
	["FlowCtrl", 4, 0x1],
	["C_Mode", 0, 0xf],
]}

phy_control_reg = {'name': "PHY Control", 'offset': 0x1, 'fields': [
	["RGMII TxTiming", 15, 0x1],
	["RGMII RxTiming", 14, 0x1],
	["ForcedSpd", 13, 0x1],
	["AltSpeed", 12, 0x1],
	["MII PHY", 11, 0x1],
	["EEEValue", 9, 0x1],
	["ForceEEE", 8, 0x1],
	["LinkValue", 5, 0x1],
	["ForcedLink", 4, 0x1],
	["DpxValue", 3, 0x1],
	["ForcedDpx", 2, 0x1],
	["SpdValue", 0, 0x3],
]}

port_control_reg = {'name': "Port Control", 'offset': 0x4, 'fields': [
	["SAFiltering", 14, 0x3],
	["EgressMode", 12, 0x3],
	["Header", 11, 0x1],
	["IGMP/MLD Snoop", 10, 0x1],
	["FrameMode", 8, 0x3],
	["VLANTunnel", 7, 0x1],
	["TaglfBoth", 6, 0x1],
	["InitialPri", 4, 0x3],
	["EgressFloods", 2, 0x3],
	["PortState", 0, 0x3],
]}


def read_and_decode(port, reg_def, mdio_mux=2):
	reg_value = read22(mdio_mux, port, reg_def['offset'])
	decode_register(port, reg_def, reg_value)


def write22_reg(port, reg_def, reg_value):
	write22(2, port, reg_def['offset'], reg_value)


def set_field(port, reg_def, field_name, field_value):
	reg_value = read22(2, port, reg_def['offset'])
	for _field in reg_def['fields']:
		if _field[0] == field_name:
			field = _field
			break
	reg_value = reg_value & (~(field[2] << field[1])) | ((field_value & field[2]) << field[1])
	write22(2, port, reg_def['offset'], reg_value)


def decode_register(port, reg_def, reg_value):
	print("=== P" + str(port) + " R" + str(reg_def['offset']) + " " + reg_def['name'] + " = " + hex(reg_value) + " ===")
	for field in reg_def['fields']:
		print(field[0] + ": " + str(reg_value >> field[1] & field[2]))


def get_port_cfg(port, mdio_mux=2):
	read_and_decode(port, port_status_reg, mdio_mux)
	read_and_decode(port, phy_control_reg, mdio_mux)
	read_and_decode(port, port_control_reg, mdio_mux)


def read_scratch(mux, offset):
	write22(mux, 0x1c, 0x1a, (offset & 0x7f) << 8)
	value = read22(mux, 0x1c, 0x1a) & 0xff
	return value


def write_scratch(mux, offset, value):
	write22(mux, 0x1c, 0x1a, 0x8000 | ((offset & 0x7f) << 8) | (value & 0xff))
	# print "wr status " + hex(read22(mux,0x1c,0x1a))
	while (read22(mux, 0x1c, 0x1a) & 0x8000 != 0):
		time.sleep(0.001)
		print(".")
	return


def set_SFP(mdio_mux=2):
	get_port_cfg(9,mdio_mux)
	#/* Set Ports in 1000Base-X
	write22(mdio_mux,9,0x0,0x9)
	#/* P9
	write22(mdio_mux,0x1c,25,0xF054)
	write22(mdio_mux,0x1c,24,0x8124)
	write22(mdio_mux,0x1c,25,0x400c)
	write22(mdio_mux,0x1c,24,0x8524)
	write22(mdio_mux,0x1c,25,0xF054)
	write22(mdio_mux,0x1c,24,0x8124)
	write22(mdio_mux,0x1c,25,0x4000)
	write22(mdio_mux,0x1c,24,0x8524)
	#/*Start configuring ports for traffic
	#/*Clear power down bit and reset SERDES P9
	write22(mdio_mux,0x1c,25,0x2000)
	write22(mdio_mux,0x1c,24,0x8124)
	write22(mdio_mux,0x1c,25,0xa040)
	write22(mdio_mux,0x1c,24,0x8524)
	#/*Fix 1000Base-X AN advertisement
	#/*write45 4.2004.5 to 1
	#/* ADDR 0x09
	write22(mdio_mux,0x1c,25,0x2004)
	write22(mdio_mux,0x1c,24,0x8124)
	write22(mdio_mux,0x1c,25,0x20)
	write22(mdio_mux,0x1c,24,0x8524)
	#/*Enable Forwarding on ports:
	write22(mdio_mux,9,4,0x007F)
	get_port_cfg(9,mdio_mux)




from optparse import OptionParser
from sys import argv, stdout

parser = OptionParser(usage="usage: %test_tpm [options]")
parser.add_option("--ip", action="store", dest="ip",
				  default="10.0.10.10", help="IP [default: 10.0.10.10]")
parser.add_option("--port", action="store", dest="port",
				  type="int", default="10000", help="Port [default: 10000]")

(conf, args) = parser.parse_args(argv[1:])

#tpm_inst = TPM(ip="10.0.10.2", port=10000, timeout=5)
mng = MANAGEMENT(ip=conf.ip, port=conf.port, timeout=5)
decode_register(10, port_status_reg, 0x7fff)
fw_ver = 0
fw_ver = mng[0x8]
print("Fw ver: " + hex(fw_ver))
if (fw_ver & 0xffff) < 0x0009:
	print("Error, minimum version required 0x0009")
	exit(1)

#read_scratch(2, 0x60)
#exit(0)
#write_scratch(2, 0x62, 0x80)
#write_scratch(2, 0x6b, 0x7 << 4)
#write_scratch(2, 0x63, 0xf9)
#for i in range(16):
#	print hex(0x60 + i) + " " + hex(read_scratch(2, 0x60 + i))

#while (1):
#	write_scratch(2, 0x65, 0xf9 | (0x0 << 1))
#	time.sleep(1)
#	write_scratch(2, 0x65, 0xf9 | (0x1 << 1))
#	time.sleep(1)
#	write_scratch(2, 0x65, 0xf9 | (0x2 << 1))
#	time.sleep(1)
#	write_scratch(2, 0x65, 0xf9 | (0x3 << 1))
#	time.sleep(1)
#exit(0)

#mdio_mux = 3  # MDIO select (SW0,SW1,PHY)

#get_port_cfg(10)
#exit(0)
#read_and_decode(0, port_status_reg)
#set_field(0, port_status_reg, "DuplexFixed", 1)
#read_and_decode(0, port_status_reg)
#exit(0)

for switch_mdio in range(1, 2):
	set_SFP(switch_mdio)
while (1):
	for switch_mdio in range(1, 2):
		get_port_cfg(9, switch_mdio)
		print(hex(read22(switch_mdio, 9, 0x1f)))
	time.sleep(1)
exit(0)

WIS_Device_Identifier_1 = read45(mdio_mux, 0, 2, 0x0002) & 0xffff
WIS_Device_Identifier_2 = read45(mdio_mux, 0, 2, 0x0003) & 0xffff
print("WIS Device Identifier 1: " + hex(WIS_Device_Identifier_1))
print("WIS Device Identifier 2: " + hex(WIS_Device_Identifier_2))
if (WIS_Device_Identifier_1 == 0x0141 and WIS_Device_Identifier_2 == 0x0f15):
	print("Marvell 88X2222 Integrated Dual-port Multi-speed Ethernet Transceiver")
elif (WIS_Device_Identifier_1 == 0x0141 and WIS_Device_Identifier_2 == 0x0d99):
	print("Marvell 88X2222 Integrated Dual-port Multi-speed Ethernet Transceiver with MACsec, IEEE 1588 PTP")
	exit(-1)
else:
	print("Unknown PHY")
	exit(-1)

# os.system('sudo ifconfig ens2 down && sudo ifconfig ens3 down')
# /*Chip Hardware Reset*/

write45(mdio_mux, 0, 31, 0xF404, 0x4000)
time.sleep(0.100)

print("Port Transmitter Source N: " + hex(read45(mdio_mux, 0, 31, 0xf400)))
print("Port Transmitter Source M: " + hex(read45(mdio_mux, 0, 31, 0xf401)))
print("Host Side Lane Muxing: " + hex(read45(mdio_mux, 0, 31, 0xf402)))
print("Power Management: " + hex(read45(mdio_mux, 0, 31, 0xf403)))
print("Port PCS Configuration: " + hex(read45(mdio_mux, 0, 31, 0xf002)))
# mgdPDStatePowerUp()
print("Port Transmitter Source N: " + hex(read45(mdio_mux, 0, 31, 0xf400)))
print("Port Transmitter Source M: " + hex(read45(mdio_mux, 0, 31, 0xf401)))
print("Power Management: " + hex(read45(mdio_mux, 0, 31, 0xf403)))
print("Host Side Lane Muxing: " + hex(read45(mdio_mux, 0, 31, 0xf402)))
print("Port PCS Configuration: " + hex(read45(mdio_mux, 0, 31, 0xf002)))
# 31,0xf403

# /*10GR - XAUI mode*/
for port in {0}:
	print("=== PORT " + str(port) + " ===")
	write45(mdio_mux, port, 31, 0xf002, 0x7173)
	write45(mdio_mux, port, 30, 0xb841, 0xe000)
	write45(mdio_mux, port, 30, 0x9041, 0x03fe)
	write45(mdio_mux, port, 30, 0xb108, 0xf8d0)
	readmodifywrite(mdio_mux, port, 30, 0xb1e7, 0b0000000000000000, 0b1100000000000000)
	readmodifywrite(mdio_mux, port, 30, 0xb1e8, 0b0010000000000000, 0b0111111100000000)
	readmodifywrite(mdio_mux, port, 30, 0xb042, 0b0000000010110000, 0b0000000011110000)
	write45(mdio_mux, port, 30, 0xb1a2, 0x00b0)
	write45(mdio_mux, port, 30, 0xb19c, 0x00a0)
	readmodifywrite(mdio_mux, port, 30, 0xb1b5, 0b0000000000000000, 0b0001000000000000)
	readmodifywrite(mdio_mux, port, 30, 0xb1b4, 0b0001000000000000, 0b0001000000000000)
	write45(mdio_mux, port, 30, 0xb181, 0x0011)
	write45(mdio_mux, port, 30, 0x8141, 0x8f1a)
	write45(mdio_mux, port, 30, 0x8131, 0x8f1a)
	write45(mdio_mux, port, 30, 0x8077, 0x820a)
	readmodifywrite(mdio_mux, port, 30, 0x80a0, 0b0000000100000000, 0b0000000111111111)
	readmodifywrite(mdio_mux, port, 30, 0x8085, 0b0000011100000000, 0b0011111100000000)
	readmodifywrite(mdio_mux, port, 30, 0x807B, 0b0000001010110010, 0b0000111111111111)
	readmodifywrite(mdio_mux, port, 30, 0x80b0, 0b0000001000100000, 0b0000011101110000)
	readmodifywrite(mdio_mux, port, 30, 0x80b1, 0b0000100000100000, 0b0000110000110000)
	readmodifywrite(mdio_mux, port, 30, 0x8093, 0b0100011000000000, 0b0111111100000000)
	readmodifywrite(mdio_mux, port, 30, 0x809F, 0b0000000001111001, 0b0000000001111111)
	write45(mdio_mux, port, 30, 0x805e, 0x4759)
	write45(mdio_mux, port, 30, 0x805f, 0x5900)
	write45(mdio_mux, port, 31, 0xf016, 0x0010)
	write45(mdio_mux, port, 31, 0xf003, 0x8080)
	time.sleep(0.2000)
	readmodifywrite(mdio_mux, port, 30, 0xb1b5, 0b0001000000000000, 0b0001000000000000)
	readmodifywrite(mdio_mux, port, 30, 0xb1b4, 0b0001000000000000, 0b0001000000000000)
	print("Port Transmitter Source N: " + hex(read45(mdio_mux, 0, 31, 0xf400)))
	print("Port Transmitter Source M: " + hex(read45(mdio_mux, 0, 31, 0xf401)))
	print("Power Management: " + hex(read45(mdio_mux, 0, 31, 0xf403)))
	print("Host Side Lane Muxing: " + hex(read45(mdio_mux, 0, 31, 0xf402)))
	print("Port PCS Configuration: " + hex(read45(mdio_mux, 0, 31, 0xf002)))
tpm_inst.disconnect()

# os.system('sudo ifconfig ens2 10.0.2.1 netmask 255.255.255.0 up && sudo ifconfig ens3 10.0.3.1 netmask 255.255.255.0 up')
# os.system('sudo ethtool -s ens2 speed 10000  autoneg off && sudo ethtool -s ens3 speed 10000 autoneg off')
# os.system('sudo ethtool ens2 && sudo ethtool ens3')
# os.system('sudo ifconfig ens2 down && sudo ifconfig ens3 down')
