__author__ = "Cristian Albanese"
"""This Script permit to read/write to CPLD2MCU serila interface"""
import sys
import time
from optparse import OptionParser
from sys import exit
import logging
import os
from bsp.management import *
import struct

usage_string = "usage: %prog [options] [<value>]\n"
usage_hexample = "es. %prog -s 0x0a\nes. %prog -r\n"


class FlashCmd:
    """
    Class containing flash commands and related constants.
    """

    CLRGPNVM = "W400E0A04,5A00010C#"
    SETGPNVM = "W400E0A04,5A00010B#"
    ERASEWRITEPG = ""
    ERASEALL = ""
    ERASESECT0 = "W400E0A04,5A000011#"
    ERASESECT1 = "W400E0A04,5A001011#"
    ERASESECTL = "W400E0A04,5A002011#"
    CLRLOCK = ""
    SETLOCK = ""
    WRITEPAGE = "W400E0A04,5A000103#"
    WRITEPAGEERASE_CMD = "W400E0A04"
    WRITEPAGE_ARG = 0x5A000001
    WRITEPAGEERASE_ARG = 0x5A000003


PAGE_SIZE = 512
SECTOR_PAGE = 128
MCU_NVMCTRL_BA = 0x400E0A00


def load_bitstream(filename, pagesize):
    """
    Load a bitstream from a file.

    :param filename: The name of the file to load.
    :param pagesize: The size of the pages.
    :return: A tuple containing the loaded bitstream, bitstream size, and total size.
    """
    print("Open Bitstream file %s" % (filename))
    with open(filename, "rb") as f:
        dump = bytearray(f.read())
    bitstream_size = len(dump)

    pages = bitstream_size / pagesize
    if (pages * pagesize) != bitstream_size:
        pages = pages + 1
    print(
        "Loading %s (%d bytes) = %d * %d bytes pages"
        % (filename, bitstream_size, pages, pagesize)
    )
    total_size = pages * pagesize
    tmp = bytearray(total_size)
    for i in range(0, bitstream_size):
        tmp[i] = dump[i]
    for i in range(0, total_size - bitstream_size):
        tmp[i + bitstream_size] = 0xFF
    return tmp, bitstream_size, total_size

if __name__ == '__main__':
    parser = OptionParser(usage=(usage_string + usage_hexample))
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
        "-e",
        "--enable",
        dest="enable",
        action="store_true",
        default=False,
        help="enable monitor",
    )
    parser.add_option(
        "-s", "--send", dest="send", default="", help="send a character or string to MCU"
    )
    parser.add_option(
        "-r",
        "--receive",
        action="store_true",
        dest="receive",
        default=False,
        help="receive data from MCU",
    )
    parser.add_option(
        "-b",
        "--setgpnvm",
        action="store_true",
        dest="setgpnvm",
        default=False,
        help="send Flash GPNVM set command",
    )
    parser.add_option(
        "-c",
        "--clrgpnvm",
        action="store_true",
        dest="clrgpnvm",
        default=False,
        help="send Flash GPNVM clear command",
    )
    parser.add_option(
        "--erase",
        action="store_true",
        dest="erase",
        default=False,
        help="send Flash ERASE for first 2 FLASH sectors ",
    )
    parser.add_option(
        "--reset", action="store_true", dest="reset", default=False, help="Reset MCU "
    )
    parser.add_option(
        "-w", "--write", dest="write", default="", help="Write a word to MCU Flash "
    )
    parser.add_option(
        "-u",
        "--update",
        action="store_true",
        dest="update",
        default=False,
        help="Update MCU",
    )
    parser.add_option(
        "-f",
        "--bitfile",
        action="store",
        dest="bitfile",
        default=None,
        help="Bitfile to use (-P still required)",
    )


    (options, args) = parser.parse_args()

    # Mng=Management(False)

    Mng = MANAGEMENT(ip=options.ip, port=options.port, timeout=5)

    """
    if options.send2!="":
        rxdata=[]
        datar=""
        for i in range(0,len(options.send)):
            state,data=Mng.uart2mcu_write(ord(options.send[i]))
            if (state != 0):
                print("ERROR: TIMEOUT Occurred during write")
                exit()
            else:
                if data!=None:
                    for i in range(0, len(data)):
                        rxdata.append(data[i])

        while(1):
            if Mng.uart2mcu_havedata()==False:
                break
            else:
                datar, status = Mng.uart2mcu_read()
                if status==0:
                    for i in range(0, len(datar)):
                        rxdata.append(datar)
        print (rxdata)
        if rxdata != None:
            for i in range(0, len(rxdata)):
                datar = datar + chr(rxdata[i])
            print("Read data %s: " %datar)
        exit()
    """
    if options.enable:
        print("Start Samba Monitor")
        Mng.mcuuart.start_mcu_sam_ba_monitor()
        exit()


    if options.reset:
        print("resetting MCU...")
        Mng.mcuuart.reset_mcu()
        exit()

    if options.send != "":
        rxdata = []
        datar = ""
        dataw = []
        for i in range(0, len(options.send)):
            dataw.append(ord(options.send[i]))
        state, data = Mng.mcuuart.uart_send_buffer_wrx(dataw)
        if state != 0:
            print("ERROR: TIMEOUT Occurred during write")
            exit()
        else:
            if data != None:
                for i in range(0, len(data)):
                    rxdata.append(data[i])
        print(rxdata)
        if rxdata != None:
            for i in range(0, len(rxdata)):
                datar = datar + chr(rxdata[i])
            print("Read data %s: " % datar)
        exit()

    if options.receive:
        datar, status = Mng.mcuuart.uart2mcu_read()
        data = ""
        if status == 0:
            for i in range(0, len(datar)):
                data = data + chr(datar[i])
            print("Read data %s: " % data)
        else:
            print("ERROR: Timeout occurred during read")
        exit()


    if options.setgpnvm:
        cmd = flash_cmd.SETGPNVM
        dataw = []
        rxdata = []
        for i in range(0, len(cmd)):
            dataw.append(ord(cmd[i]))
        state, data = Mng.mcuuart.uart_send_buffer_wrx(dataw)
        if state != 0:
            print("ERROR: TIMEOUT Occurred during write")
            exit()
        else:
            if data != None:
                for i in range(0, len(data)):
                    rxdata.append(data[i])
        print(rxdata)
        if rxdata != None:
            for i in range(0, len(rxdata)):
                datar = data + chr(rxdata[i])
            print("Read data %s: " % datar)
        exit()

    if options.erase:
        cmd_erase = [flash_cmd.ERASESECT0, flash_cmd.ERASESECT1]
        dataw = []
        rxdata = []
        cmd = cmd_erase[0]
        for i in range(0, len(cmd)):
            dataw.append(ord(cmd[i]))
        state, data = Mng.mcuuart.uart_send_buffer_wrx(dataw)
        if state != 0:
            print("ERROR: TIMEOUT Occurred during write")
            exit()
        else:
            if data != None:
                for i in range(0, len(data)):
                    rxdata.append(data[i])
        print(rxdata)
        if rxdata != None:
            for i in range(0, len(rxdata)):
                datar = datar + chr(rxdata[i])
            print("Read data %s: " % datar)
        time.sleep(0.5)
        exit()

    if options.write:
        rxdata = []
        datar = ""
        dataw = []
        for i in range(0, len(options.write)):
            dataw.append(ord(options.write[i]))
        state = Mng.mcuuart.uart_send_buffer(dataw)
        if state != 0:
            print("ERROR: TIMEOUT Occurred during write")
            exit()
        cmd = flash_cmd.WRITEPAGE
        dataw = []
        rxdata = []
        for i in range(0, len(cmd)):
            dataw.append(ord(cmd[i]))
        state = Mng.mcuuart.uart_send_buffer(dataw)
        if state != 0:
            print("ERROR: TIMEOUT Occurred during write")
            exit()
        time.sleep(0.5)
        exit()

    if options.update:
        if options.bitfile is not None:
            if os.path.exists(options.bitfile) and os.path.isfile(options.bitfile):
                logging.info("Using MCU bitfile {}".format(options.bitfile))

                memblock, bitstreamSize, size = loadBitstream(options.bitfile, PAGE_SIZE)
                # Read bitfile and cast as a list of unsigned integers
                formatted_bitstream = list(
                    struct.unpack_from("I" * (len(memblock) / 4), memblock)
                )
                cmd = ""
                page = 0
                dataw = []
                start = time.time()
                pre = start
                sect = size / (64 * 1024) + 1
                print("Number of sector: %d" % sect)
                # ERASE sector cmd
                cmd_erase = [
                    flash_cmd.ERASESECT0,
                    flash_cmd.ERASESECT1,
                    flash_cmd.ERASESECTL,
                ]
                dataw = []
                rxdata = []
                for w in range(0, 3):
                    cmd = cmd_erase[w]
                    print("erase cmd %s" % cmd)
                    for i in range(0, len(cmd)):
                        dataw.append(ord(cmd[i]))
                    state = Mng.mcuuart.uart_send_buffer(dataw)
                    time.sleep(0.7)

                print("Start time %.6f" % start)
                bw = 0
                for i in range(0, len(formatted_bitstream)):
                    """
                    data=((formatted_bitstream[i]&0xFF000000)>>24) |    \
                    ((formatted_bitstream[i] & 0x00FF0000) >> 8) |      \
                    ((formatted_bitstream[i] & 0x0000FF00) << 8) | \
                    ((formatted_bitstream[i] & 0x000000FF) << 24)
                    """
                    # data=data&0xFFFFFFFF
                    data = formatted_bitstream[i] & 0xFFFFFFFF
                    cmd = (
                        "W"
                        + hex(0x400000 + i * 4)[2:]
                        + ","
                        + hex(data)[2 : len(hex(data))]
                        + "#"
                    )
                    dataw = []
                    for k in range(0, len(cmd)):
                        dataw.append(ord(cmd[k]))
                    state = Mng.mcuuart.uart_send_buffer(dataw)
                    if state != 0:
                        print("ERROR: TIMEOUT Occurred during write")
                        exit()
                    bw = bw + 4
                    # if i != 0 and i % 127 == 0:
                    if bw == 512:
                        wp_data = flash_cmd.WRITEPAGE_ARG | (page << 8)
                        wp_cmd = (
                            flash_cmd.WRITEPAGEERASE_CMD
                            + ","
                            + hex(wp_data)[2 : len(hex(wp_data))]
                            + "#"
                        )
                        print("wp_command: %s" % wp_cmd)
                        print("Write page %d" % page)
                        now = time.time()
                        print("Elapsed time for page write %.6f" % (now - pre))
                        pre = now
                        page = page + 1
                        dataw = []
                        for k in range(0, len(wp_cmd)):
                            dataw.append(ord(wp_cmd[k]))
                        state = Mng.mcuuart.uart_send_buffer(dataw)
                        if state != 0:
                            print("ERROR: TIMEOUT Occurred during write")
                            exit()
                        time.sleep(0.5)
                        bw = 0
                """          
                wp_data = flash_cmd.WRITEPAGEERASE_ARG | (page << 8)
                wp_cmd = flash_cmd.WRITEPAGEERASE_CMD + "," + hex(wp_data)[2:len(hex(wp_data))] + "#"
                print ("wp_command: %s" % wp_cmd)
                print ("Write page %d" % page)
                now = time.time()
                print ("Elapsed time for page write %.6f" % (now - pre))
                pre = now
                page = page + 1
                dataw = []
                for k in range(0, len(wp_cmd)):
                    dataw.append(ord(wp_cmd[k]))
                state = Mng.mcuuart.uart_send_buffer(dataw)
                if (state != 0):
                    print("ERROR: TIMEOUT Occurred during write")
                    exit()
                time.sleep(0.5)
                """
                end = time.time()
                print("Elapsed time %.6f" % (end - start))
            else:
                logging.error(
                    "Could not load bitfile {}, check filepath".format(options.bitfile)
                )
        else:
            logging.error("No CPLD bitfile specified")
            exit(-1)
