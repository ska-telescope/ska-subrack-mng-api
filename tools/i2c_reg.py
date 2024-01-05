__author__ = "Cristian Albanese"
"""This Script permit to read/write Single Fpga Register"""
import sys
import time
from optparse import OptionParser
from subrack_mng_api.management import *

usage_string = "usage: %prog [options] [<I2C Device name> <offset>] [<value>] \n"
usage_hexample = "es. %prog EEPROM_MAC_1 0xfa\n"
Mng = Management()


def get_dev_add(devname):
    """
    Get the I2C device address based on the device name.

    Args:
        devname (str): The name of the I2C device.

    Returns:
        int: The I2C device address.

    Raises:
        SystemExit: If the provided device name is incorrect.
    """
    found = False
    for i in range(0, len(I2CDevices)):
        if vars(I2CDevAdd).keys()[i + 1] == devname:
            found = True
            break
    if found:
        return vars(I2CDevAdd).values()[i + 1]
    else:
        print("Error: incorrect device name")
        exit()


parser = OptionParser(usage=(usage_string + usage_hexample))
parser.add_option(
    "-l",
    "--list_i2c",
    action="store_true",
    dest="list_i2c",
    default=False,
    help="show i2c devices & address",
)

(options, args) = parser.parse_args()

if options.list_i2c:
    print("List I2C devices address:")
    zMng.list_i2c_devadd()
    exit()

if len(args) == 1:
    print("Error invalid parameters")
    parser.print_usage()
    exit()

if len(args) == 2:
    print("I2C read operation")
    deviceadd = get_dev_add(args[0])
    offset = int(args[1], 16)
    data = Mng.read_i2c(0, deviceadd, offset, "b")

if len(args) == 3:
    print("I2C write operation")
    deviceadd = get_dev_add(args[0])
    offset = int(args[1], 16)
    value = int(args[2], 16)
    data = Mng.write_i2c(0, deviceadd, offset, value, "b")
