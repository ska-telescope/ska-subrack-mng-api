__author__ = "Luca Schettini"
"""This Script search 1Wire Device on the bus (fixed to bus 1)"""
import sys
import time
from optparse import OptionParser
from management import *
from backplane import *

import os
import sys
import termios, fcntl
import select
import struct
import subprocess

backplane = Backplane()

Mng = Management()


def search():
    Mng.OneWire_SelectMux(0)
    time.sleep(0.5)

    board = 1
    print("Search device for board %d" % board)
    dev_id = search_device()

    print("Detected %d devices" % len(dev_id))

    for i in range(0, len(dev_id)):
        # print "Device %d id:" %i
        # print [hex(d) for d in dev_id[i]]
        if i < 3:
            dev_table[0][i] = dev_id[i]


def search_device():
    disc_pos = []
    prev_disc_pos = []
    v_discrepances = []
    idcodes = []

    idcode = []
    discrepances = []
    pos = 0
    iter = 0
    prev_pos = 0
    disc_to_use_with_unch = 0
    disc_byte = [
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]

    dir = 0

    while 1:
        idcode = []
        discrepances = []
        data = []
        # print "Iteration %d" %iter
        Mng.write("ONEWIRE.Command1WM", 0x0)
        Mng.OneWire_ResetCmd()
        Mng.OneWire_WriteByte(0xF0)
        Mng.OneWire_AccelerateModeCmd()

        for i in range(0, 16):
            # print "Byte to be send %x" %disc_byte[i]
            result, status = Mng.OneWire_ReadByte_d(disc_byte[i])
            if (status) == 0:
                # print "Read value " + hex(result)
                data.append(result)
        # else:
        #     print "Error while reading"

        # print "rx data "
        # print [hex(d) for d in data]

        i = 0
        for q in range(0, 8):
            # print "data: %x data+1 %x" %(data[i],data[i+1])
            # retrieve id
            id_l = (
                ((data[i] & 0x2) >> 1)
                | ((data[i] & 0x8) >> 2)
                | ((data[i] & 0x20) >> 3)
                | ((data[i] & 0x80) >> 4)
            )
            id_h = (
                ((data[i + 1] & 0x2) >> 1)
                | ((data[i + 1] & 0x8) >> 2)
                | ((data[i + 1] & 0x20) >> 3)
                | ((data[i + 1] & 0x80) >> 4)
            )
            # print "idh %x idl %x" %(id_h,id_l)
            id = id_l | (id_h << 4)
            idcode.append(id)
            # retrieve discrepances
            disc_l = (
                ((data[i] & 0x0))
                | ((data[i] & 0x4) >> 1)
                | ((data[i] & 0x10) >> 2)
                | ((data[i] & 0x40) >> 3)
            )
            disc_h = (
                ((data[i + 1] & 0x0))
                | ((data[i + 1] & 0x4) >> 1)
                | ((data[i + 1] & 0x10) >> 2)
                | ((data[i + 1] & 0x40) >> 3)
            )
            # print "disc_h %x disc_l %x" %(disc_h,disc_l)
            disc = disc_l | (disc_h << 4)
            discrepances.append(disc)
            i = i + 2

        # print [hex(W) for W in idcode]
        # print [hex(W) for W in discrepances]
        # for i in range (0,len(idcode)):
        #    print "id: %x  disc: %x " %(idcode[i],discrepances[i])

        v_discrepances.append(discrepances)

        # detect_disc_bit
        prev_disc = pos
        found_disc = False
        for n in range(0, 8):
            dato = discrepances[n]
            for i in range(0, 8):
                if (dato & 0x1) == 0x1:
                    found_disc = True
                    pos = (n * 8) + i
                dato = dato >> 1
        if found_disc == False:
            pos = 9
            # print "No discrepances detected"
        # else:
        # print "Last discrepance detected at bit: %d" %pos

        # idcodes.append(idcode)

        # return idcodes

        # reconstruct transimt data

        if iter > 0:
            if v_discrepances[iter - 1] == v_discrepances[iter]:
                # print "Detected two times same discrepances"
                # print "actual pos %d" %pos
                pos = prev_pos - 1
                # print "new pos %d" %pos
                """
                if dir == 0:
                    pos += 1
                    dir = 1
                else:
                    pos -= 1
                    dir = 0
                """ ""
        #    else:
        #        idcodes.append(idcode)
        # else:
        #    idcodes.append(idcode)

        exist = 0
        if len(idcodes) > 0:
            for z in range(0, len(idcodes)):
                if idcode == idcodes[z]:
                    exist = 1
                    break

        if exist == 0:
            idcodes.append(idcode)

        prev_pos = pos

        byte_disc_count = pos * 2 / 8
        bitinbytepos = ((pos * 2) - (byte_disc_count * 8)) + 1

        # print "Byte Discrepancy %x and bit in bytes %x" %(byte_disc_count,bitinbytepos)

        for i in range(0, 16):
            if i < byte_disc_count:
                disc_byte[i] = (
                    0x0
                    | (data[i] & 0x2)
                    | (data[i] & 0x8)
                    | (data[i] & 0x20)
                    | (data[i] & 0x80)
                )
            elif i == byte_disc_count:
                # print "Discrepancy byte: ", hex(disc_byte[i])
                disc_byte[i] = 0
                for m in range(0, 8):
                    # print "Discrepancy byte (for): ", hex(disc_byte[i])
                    if m % 2 != 0:
                        if m == bitinbytepos:
                            disc_byte[i] = disc_byte[i] | (1 << m)
                            break
                        else:
                            disc_byte[i] = disc_byte[i] | (data[i] & (1 << m))
                    else:
                        disc_byte[i] = disc_byte[i] | 0

                mask = 0
                for m in range(0, bitinbytepos + 1):
                    mask = mask | (1 << m)
                # print "mask %x disc_byte %x" %(mask,disc_byte[i] )
                disc_byte[i] = disc_byte[i] & 0xAA & mask
            else:
                disc_byte[i] = 0x0

        # disc_byte=discrepances
        # print "discrepance byte "
        # print disc_byte
        iter = iter + 1
        if iter > 32:
            # print "OOOhps Somethings Wrong..."

            print(idcodes)

            lens = len(idcodes)
            removes = []
            for i in range(0, lens):
                if idcodes[i][0] != 0x28:
                    removes.append(i)
                    # print "\nlist rem " + str(i)

            remlens = len(removes)
            if remlens > 0:
                for i in range(remlens, 0, -1):
                    rmm = removes[i - 1]
                    # print rmm
                    # print "\nrem " + str(i) + " = " + str(rmm)
                    del idcodes[rmm]

            # print idcodes

            lens = len(idcodes)
            for i in range(0, lens):
                print(
                    "Sensor "
                    + str(i)
                    + ": "
                    + "{0:02x}".format(idcodes[i][0], "x")
                    + "{0:02x}".format(idcodes[i][1], "x")
                    + "{0:02x}".format(idcodes[i][2], "x")
                    + "{0:02x}".format(idcodes[i][3], "x")
                    + "{0:02x}".format(idcodes[i][4], "x")
                    + "{0:02x}".format(idcodes[i][5], "x")
                    + "{0:02x}".format(idcodes[i][6], "x")
                    + "{0:02x}".format(idcodes[i][7], "x")
                )

            # print idcodes

            return idcodes


backplane.pwr_on_tpm(1)
time.sleep(2)
w, h, z = 8, 3, 8
dev_table = [[[0 for x in range(w)] for y in range(h)] for z in range(z)]
search()
# backplane.pwr_off_tpm(1)
