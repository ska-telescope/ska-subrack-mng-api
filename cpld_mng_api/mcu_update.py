__author__ = 'Cristian Albanese'
"""This Script permit to read/write to CPLD2MCU serila interface"""
import sys
import time
from optparse import OptionParser
from sys import exit
import logging
import os
from bsp.management import *
import struct

usage_string="usage: %prog [options] [<value>]\n"
usage_hexample="es. %prog -s 0x0a\nes. %prog -r\n"


class flash_cmd():
    CLRGPNVM = "W400E0A04,5A00010C#"
    SETGPNVM = "W400E0A04,5A00010B#"
    ERASEWRITEPG= ""
    ERASEALL=""
    ERASESECT0="W400E0A04,5A000011#"
    ERASESECT1="W400E0A04,5A001011#"
    ERASESECTL = "W400E0A04,5A002011#"
    CLRLOCK=""
    SETLOCK=""
    WRITEPAGE="W400E0A04,5A000103#"
    WRITEPAGEERASE_CMD="W400E0A04"
    WRITEPAGE_ARG=0x5A000001
    WRITEPAGEERASE_ARG=0x5A000003

PAGE_SIZE=512
SECTOR_PAGE=128
MCU_NVMCTRL_BA=0x400E0A00


def loadBitstream(filename, pagesize):
    print ("Open Bistream file %s" % (filename))
    with open(filename, "rb") as f:
        dump = bytearray(f.read())
    bitstreamSize = len(dump)

    pages = bitstreamSize / pagesize
    if ((pages * pagesize) != bitstreamSize):
        pages = pages + 1
    print("Loading %s (%d bytes) = %d * %d bytes pages" % (filename, bitstreamSize, pages, pagesize))
    s = pages * pagesize
    tmp = bytearray(s)
    for i in range(0, bitstreamSize):
        tmp[i] = dump[i]
    for i in range(0, s - bitstreamSize):
        tmp[i + bitstreamSize] = 0xff
    return tmp, bitstreamSize, s



if __name__ == "__main__":
    parser = OptionParser(usage =(usage_string+usage_hexample))
    parser.add_option("--ip", action="store", dest="ip",
                      default="10.0.10.10", help="IP [default: 10.0.10.10]")
    parser.add_option("--port", action="store", dest="port",
                      type="int", default="10000", help="Port [default: 10000]")
    parser.add_option("-u","--update",
                    action="store_true",dest="update", default=False,
                    help="Update MCU")
    parser.add_option("-f", "--bitfile", action="store", dest="bitfile",
                      default=None, help="Bitfile to use (-P still required)")

    (options, args) = parser.parse_args()
    Mng = MANAGEMENT(ip=options.ip, port=options.port, timeout=5)
    if options.update:
        if options.bitfile is not None:
            if os.path.exists(options.bitfile) and os.path.isfile(options.bitfile):
                logging.info("Using MCU bitfile {}".format(options.bitfile))
                memblock, bitstreamSize, size = loadBitstream(options.bitfile, PAGE_SIZE)
                # Read bitfile and cast as a list of unsigned integers
                formatted_bitstream = list(struct.unpack_from('I' * (len(memblock) / 4), memblock))
                cmd=""
                page=0
                dataw=[]
                print("*************************** WARNING ************************************")
                print("This operation will Erase actual MCU FW and it's dangerous are you sure to continue?(y/n)")
                ans=raw_input("")
                if ans!="y":
                    exit()
                print ("Start Samba Monitor")
                Mng.mcuuart.start_mcu_sam_ba_monitor()
                print("Start FW loading in Flash")
                start=time.time()
                pre=start
                # ERASE sector cmd
                cmd_erase = [flash_cmd.ERASESECT0, flash_cmd.ERASESECT1, flash_cmd.ERASESECTL]
                dataw = []
                rxdata = []
                for w in range(0, 3):
                    cmd = cmd_erase[w]
                    print ("erase cmd %s" % cmd)
                    for i in range(0, len(cmd)):
                        dataw.append(ord(cmd[i]))
                    state = Mng.mcuuart.uart_send_buffer(dataw)
                    time.sleep(0.7)

                print ("Start time %.6f" %start)
                bw=0
                for i in range (0,len(formatted_bitstream)):
                    data = formatted_bitstream[i] & 0xFFFFFFFF
                    cmd = "W" + hex(0x400000 + i * 4)[2:] + "," + hex(data)[2:len(hex(data))] + "#"
                    dataw = []
                    for k in range(0, len(cmd)):
                        dataw.append(ord(cmd[k]))
                    state = Mng.mcuuart.uart_send_buffer(dataw)
                    if (state != 0):
                        print("ERROR: TIMEOUT Occurred during write")
                        exit()
                    bw = bw + 4
                    # if i != 0 and i % 127 == 0:
                    if bw == 512:
                        wp_data = flash_cmd.WRITEPAGE_ARG | (page << 8)
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
                        bw = 0
                end = time.time()
                print ("Elapsed time %.6f" %(end-start))
                #set GPNVM
                print("Setting MCU to start from Flash")
                cmd = flash_cmd.SETGPNVM
                dataw = []
                rxdata = []
                for i in range(0, len(cmd)):
                    dataw.append(ord(cmd[i]))
                state = Mng.mcuuart.uart_send_buffer(dataw)
                if (state != 0):
                    print("ERROR: TIMEOUT Occurred during write")
                    exit()
                time.sleep(0.5)
                #reset MCU
                print("resetting MCU...")
                Mng.mcuuart.reset_mcu()
            else:
                logging.error("Could not load bitfile {}, check filepath".format(options.bitfile))
        else:
            logging.error("No CPLD bitfile specified")
            exit(-1)

