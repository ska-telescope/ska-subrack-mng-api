import netproto.rmp as rmp
import sys
import socket
import struct
import binascii
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bsp.management import *
import lxml.etree as ET
from optparse import OptionParser


def format_num(num):
    return str(num)


def get_max_width(table1, index1):
    """Get the maximum width of the given column index"""
    return max([len(format(row1[index1])) for row1 in table1])


def pprint_table(table):
    """Prints out a table of data.
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns."""

    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # print row
        # left col
        print(row[0].ljust(col_paddings[0] + 1)),
        # rest of the cols
        for i in range(1, len(row)):
            col = str(row[i]).rjust(col_paddings[i] + 2)
            print(
                col,
            )
        print


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option(
        "-p", "--udp_port", dest="udp_port", default="10000", help="BOARD UCP UDP port"
    )
    parser.add_option("--ip", dest="ip", default="10.0.10.10", help="BOARD IP Address")
    parser.add_option(
        "-d",
        "--design",
        dest="design",
        default="MANAGEMENT",
        help="Number of 32 bits words",
    )
    parser.add_option(
        "-n", "--num", dest="num", default=1, help="Number of 32 bits words"
    )

    (options, args) = parser.parse_args()
    management_inst = MANAGEMENT(ip=options.ip, port=options.udp_port, timeout=5)

    if len(args) == 1:
        dat = management_inst.read_register(int(args[0], 16), n=int(options.num))
        if type(dat) != list:
            dat = [dat]
        lines = []
        k = 0
        for x in dat:
            # if options.lookup:
            #    lines.append([management_inst.get_register_name_by_address(int(args[0],16)+4*k), hex(x)])
            # else:
            lines.append([hex(x)])
            k = k + 1
        if lines != []:
            pprint_table(lines)
    elif len(args) == 2:
        str_list = args[1].split(".")
        dat_list = []
        for s in str_list:
            dat_list.append(int(s, 16))
        management_inst.write_register(int(args[0], 16), dat_list)
    else:
        "input error!"

    management_inst.rmp.CloseNetwork()
