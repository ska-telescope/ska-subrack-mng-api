__author__ = "Cristian Albanese"
"""This Script permit to read/write Single Fpga Register"""
import sys
import time
from optparse import OptionParser
from subrack_mng_api.management import *

usage_string = (
    "usage: %prog [options] [<register_category>.<register/bitfield name>] [<value>]\n"
)
usage_hexample = (
    "es. %prog FPGA_FW.FirmwareVersion\nes. %prog UserReg.UserReg0 0x12345678\n"
)
zMng = Management()


parser = OptionParser(usage=(usage_string + usage_hexample))
parser.add_option(
    "-l",
    "--list_cat",
    action="store_true",
    dest="list_cat",
    default=False,
    help="show registers category",
)
parser.add_option(
    "-r",
    "--list_regs",
    action="store_true",
    dest="list_regs",
    default=False,
    help="show list of all fpga registers & flags",
)
parser.add_option(
    "-d",
    "--dump_regs",
    action="store_true",
    dest="dump_regs",
    default=False,
    help="dump all fpga registers & flags",
)


(options, args) = parser.parse_args()

if options.list_cat == True:
    print("List categories:")
    Mng.dump_categories()
    exit()

if options.list_regs == True:
    print("List available register:")
    Mng.create_all_regs_list()
    exit()

if options.dump_regs == True:
    print("Fpga dump:")
    Mng.get_fpga_fw_version()
    print("Housekeeping Flags:")
    Mng.dump_housekeeping_flags_all()
    print("MCU Registers:")
    Mng.dump_mcu_regs_all()
    print("User Led registers:")
    Mng.dump_userled_all()
    print("UserReg registers:")
    Mng.dump_fpga_userreg_all()
    print("FramRegs registers:")
    Mng.dump_fram_regs_all()
    exit()

if len(args) == 1:
    reg_value = Mng.read(args[0])
    if args[0].split(".")[0] == "MCUR":
        for i in range(0, len(MCUReg_names)):
            if args[0].split(".")[1] == MCUReg_names[i]:
                break
        if i > 6 and i < 19:
            print(args[0] + " = " + str("%.2f" % (float(reg_value) / 1000)))
        elif i >= 19 and i < (len(MCUReg_names) - 1):
            print(args[0] + " = " + str("%.2f" % (reg_value)))
        elif i == (len(MCUReg_names) - 1):
            print(args[0] + " = " + str("%.2f" % (float(reg_value) / 10)))
        else:
            print(args[0] + " = " + hex(reg_value & 0xFFFFFFFF))
    else:
        print(args[0] + " = " + hex(reg_value & 0xFFFFFFFF))
    exit()

if len(args) == 2:
    reg_value = Mng.write(args[0], args[1])
    exit()
