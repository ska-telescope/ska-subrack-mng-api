import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bsp.management import *
from optparse import OptionParser

MAX_REG_ADD = 0x3A3C
usage_string = "usage: %prog [options] [<pll_register_address>] [<value>]\n"
usage_hexample = (
    "es.(load configuration) %prog -l -f our_pll_cfg.txt \nes.(dump configuration)"
    " %prog -d -f dump_pll_cfg.txt\n"
    "es.(reg write) %prog 0x24 0x3\nes.(reg read) %prog 0x24\nes.(calibration) %prog -c\n"
)

if __name__ == "__main__":
    """
    Main script for PLL configuration and control.

    Example Usages:
    - Load configuration from file: ./script.py -l -f our_pll_cfg.txt
    - Dump configuration to file: ./script.py -d -f dump_pll_cfg.txt
    - Write register: ./script.py 0x24 0x3
    - Read register: ./script.py 0x24
    - Execute PLL calibration sequence: ./script.py -c
    - Execute IO Update command: ./script.py -u <register_address> <value>
    - Command without IO Update: ./script.py <register_address>
    """
    parser = OptionParser(usage=(usage_string + usage_hexample))
    parser.add_option(
        "-l",
        "--ldcfg",
        action="store_true",
        dest="pll_ldcfg",
        default=False,
        help="Require Load PLL cfg from file",
    )
    parser.add_option(
        "-d",
        "--dumpcfg",
        action="store_true",
        dest="pll_dumpcfg",
        default=False,
        help="Store PLL cfg to file",
    )
    parser.add_option(
        "-c",
        "--calib",
        action="store_true",
        dest="pll_calib",
        default=False,
        help="Execute PLL calibration sequence",
    )
    parser.add_option(
        "-f",
        "--filename",
        dest="cfg_filename",
        default=False,
        help="PLL configuration file name both for load and dump",
    )
    parser.add_option(
        "-u",
        "--update",
        action="store_true",
        dest="ioupdate",
        default=False,
        help="Execute IO Update command",
    )
    parser.add_option(
        "-p", "--udp_port", dest="udp_port", default="10000", help="BOARD UCP UDP port"
    )
    parser.add_option("--ip", dest="ip", default="10.0.10.10", help="BOARD IP Address")
    (options, args) = parser.parse_args()

    inst = MANAGEMENT(ip=options.ip, port=options.udp_port, timeout=5)

    if options.pll_ldcfg:
        """
        Load PLL configuration from a file.
        """
        cfgfile = open(options.cfg_filename, "r")
        cfglines = cfgfile.readlines()
        cfgfile.close()
        opnum = len(cfglines)
        print("Writing configuration...")
        for i in range(1, opnum):
            address = cfglines[i].split(",")[0]
            value = cfglines[i].split(",")[1].splitlines()[0]
            inst.write_spi(int(address, 16), int(value, 16))
        inst.write_spi(0xF, 0x1)

    elif options.pll_dumpcfg:
        """
        Dump PLL configuration to a file.
        """
        cfgfile = open(options.cfg_filename, "w")
        print("Reading configuration...")
        cfgfile.write("Address,Data\n")
        for address in range(0, MAX_REG_ADD):
            data = inst.read_spi(address)
            haddress = hex(address)
            hdata = hex(data)
            haddress = haddress[2:].zfill(4)
            hdata = hdata[2:].zfill(2)
            cfgfile.write("0x" + haddress.upper() + "," + "0x" + hdata.upper() + "\n")

    elif options.pll_calib:
        """
        Execute PLL calibration sequence.
        """
        print("Calibrating...")
        inst.write_spi(0x2000, 0x0)
        inst.write_spi(0xF, 0x1)
        inst.write_spi(0x2000, 0x2)
        inst.write_spi(0xF, 0x1)
        inst.write_spi(0x2000, 0x0)
        inst.write_spi(0xF, 0x1)

    elif options.ioupdate:
        """
        Execute IO Update command.
        """
        print("Command WITH update IO")
        if len(args) == 1:
            inst.write_spi(0xF, 0x1)
            print(hex(inst.read_spi(int(args[0], 16))))
        elif len(args) == 2:
            inst.write_spi(int(args[0], 16), int(args[1], 16))
            inst.write_spi(0xF, 0x1)
        else:
            inst.write_spi(0xF, 0x1)
            print("IO Updated. No command issued.")

    else:
        """
        Command WITHOUT update IO.
        """
        print("Command WITHOUT update IO")
        if len(args) == 1:
            print(hex(inst.read_spi(int(args[0], 16))))
        elif len(args) == 2:
            inst.write_spi(int(args[0], 16), int(args[1], 16))
        else:
            print("Error. Wrong number of parameters")
    inst.disconnect()
