__author__ = "Cristian Albanese"
"""This Script permit to read/write Single Fpga Register"""
import sys
import time
from optparse import OptionParser
from subrack_mng_api.management import *


usage_string = "usage: %prog [options] [<I2C Device add>.<i2c_bus_id>.<data_size> <offset>] [<value>] \n"
usage_hexample = (
    "es (Read 8bit from reg 0x1 of device at add 0x40 on bus i2c2 ). %prog 0x40.2.8 0x01\n"
    "(Write 16bit, data 0x1234 at reg 0x1 of device at add 0x40 on bus i2c3). %prog 0x40.3.16 0x01 0x1234\n"
)
zMng = Management()


parser = OptionParser(usage=(usage_string + usage_hexample))


(options, args) = parser.parse_args()


if len(args) == 1:
    print("Error invalid paramenters")
    parser.print_usage()
    exit()

if len(args) == 2:
    print("FPGA I2C read operation")
    add = args[0]
    bus = add.split(".")[1]
    dev = add.split(".")[0]
    size = add.split(".")[2]
    if int(bus, 16) == 1:
        busid = FPGA_I2CBUS.i2c1
    if int(bus, 16) == 2:
        busid = FPGA_I2CBUS.i2c2
    if int(bus, 16) == 3:
        busid = FPGA_I2CBUS.i2c3
    offset = int(args[1], 16)
    deviceadd = int(dev, 16)

    if int(size) == 8:
        print("read 8 bit")
        data = Mng.fpgai2c_read8(deviceadd, offset, busid)
    else:
        print("read 16 bit")
        data = Mng.fpgai2c_read16(deviceadd, offset, busid)
    print(dev + "[" + hex(offset) + "]" + " = " + hex(data[0]))

if len(args) == 3:
    print("FPGA I2C write operation")
    add = args[0]
    bus = add.split(".")[1]
    dev = add.split(".")[0]
    size = add.split(".")[2]
    if int(bus, 16) == 1:
        busid = FPGA_I2CBUS.i2c1
    if int(bus, 16) == 2:
        busid = FPGA_I2CBUS.i2c2
    if int(bus, 16) == 3:
        busid = FPGA_I2CBUS.i2c3
    offset = int(args[1], 16)
    deviceadd = int(dev, 16)
    value = int(args[2], 16)
    if int(size) == 8:
        print("write 8 bit")
        data = Mng.fpgai2c_write8(deviceadd, offset, value, busid)
    else:
        print("write 16 bit")
        data = Mng.fpgai2c_write16(deviceadd, offset, value, busid)
