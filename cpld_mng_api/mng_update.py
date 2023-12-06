#!/usr/bin/env python
"""
Test TPM script.

__author__ = "Bubs"
"""

import os
import sys
import time
import datetime
import struct

from sys import exit
import logging
import os
from bsp.management import *

if __name__ == "__main__":

    # Use OptionParse to get command-line arguments
    from optparse import OptionParser
    from sys import argv, stdout

    parser = OptionParser(usage="usage: %test_tpm [options]")
    parser.add_option(
        "--ip",
        action="store",
        dest="ip",
        default="10.0.10.10",
        help="IP [default: 10.0.10.10]",
    )
    parser.add_option(
        "--port",
        action="store",
        dest="port",
        type="int",
        default="10000",
        help="Port [default: 10000]",
    )
    parser.add_option(
        "-f",
        "--bitfile",
        action="store",
        dest="bitfile",
        default=None,
        help="Bitfile to use (-P still required)",
    )
    parser.add_option(
        "-C",
        "--program-cpld",
        action="store_true",
        dest="program_cpld",
        default=False,
        help="Program CPLD (cannot be used with other options) [default: False]",
    )

    (conf, args) = parser.parse_args(argv[1:])

    # Set logging
    log = logging.getLogger("")
    log.setLevel(logging.DEBUG)
    line_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler(stdout)
    ch.setFormatter(line_format)
    log.addHandler(ch)

    # Create Tile
    mng = MANAGEMENT(ip=conf.ip, port=conf.port, timeout=5)
    error_count = 0
    # get expected board's devices info
    dev = []
    for i in range(0, 1):
        dev.append(mng.spiflash.DeviceGetInfo(i))
    id = []
    print("Read and CHECK Flasehes ID")
    id.append(mng.spiflash.DeviceGetID(0))
    # mng.spiflash.spi_config(1)
    # mng.spiflash.spi_trigger(10)
    # mng.spiflash.spi_config(0)
    for i in range(0, 1):
        if id[i] != dev[i].jedecID:
            print(
                "Error reading id of device %d: expected %x, read %x"
                % (i, dev[i].jedecID, id[i])
            )
            error_count += 1
        else:
            print("DeviceID of device %d: %x " % (i, id[i]))
    # Program CPLD
    cpld_FW_start_add = 0x10000
    if conf.program_cpld:
        if conf.bitfile is not None:
            if os.path.exists(conf.bitfile) and os.path.isfile(conf.bitfile):
                logging.info("Using CPLD bitfile {}".format(conf.bitfile))
                # tile.program_cpld(conf.bitfile)
                starttime = time.time()
                ec = mng.spiflash.firmwareProgram(0, conf.bitfile, cpld_FW_start_add)
                endtime = time.time()
                delta = endtime - starttime
                if ec == 0:
                    print("Bitstream write complete, power-off the board")
                    print("elapsed time " + str(delta) + "s")
                else:
                    print("Error detected while bitsream writing in flash")
                exit(0)
            else:
                logging.error(
                    "Could not load bitfile {}, check filepath".format(conf.bitfile)
                )
        else:
            logging.error("No CPLD bitfile specified")
            exit(-1)
