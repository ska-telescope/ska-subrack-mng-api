__author__ = 'Bubs'

__author__ = 'Cristian Albanese'
"""This Script permit to on_off Selected TPM inserted in Backplane Board"""
import sys
import time
from optparse import OptionParser
from subrack_mng_api.subrack_management_board import *

subrack=SubrackMngBoard()

usage_string="usage: %prog [options] \n"
usage_hexample="(es power off TPM1 and TPM3). %prog --t1 --t3\n" \
               "(es power off all TPM). %prog --all\n"

if __name__ == '__main__':

    parser = OptionParser(usage =(usage_string+usage_hexample))
    parser.add_option("--t1",
                      action="store_true",
                      dest="tpm1",
                      default=False,
                      help="select TPM1 to power off")
    parser.add_option("--t2",
                      action="store_true",
                      dest="tpm2",
                      default=False,
                      help="select TPM2 to power off")
    parser.add_option("--t3",
                      action="store_true",
                      dest="tpm3",
                      default=False,
                      help="select TPM3 to power off")
    parser.add_option("--t4",
                      action="store_true",
                      dest="tpm4",
                      default=False,
                      help="select TPM4 to power off")
    parser.add_option("--t5",
                      action="store_true",
                      dest="tpm5",
                      default=False,
                      help="select TPM5 to power off")
    parser.add_option("--t6",
                      action="store_true",
                      dest="tpm6",
                      default=False,
                      help="select TPM6 to power off")
    parser.add_option("--t7",
                      action="store_true",
                      dest="tpm7",
                      default=False,
                      help="select TPM7 to power off")
    parser.add_option("--t8",
                      action="store_true",
                      dest="tpm8",
                      default=False,
                      help="select TPM8 to power off")
    parser.add_option("--all",
                      action="store_true",
                      dest="all",
                      default=False,
                      help="select all TPM to power off")
    (options, args) = parser.parse_args()


    if options.all is True:
        for i in range (1,9):
            print("Power Off TPM " + str(i))
            try:
                subrack.PowerOffTPM(i)
                logging.info("power off command success")
            except:
                print("power off command failed")
                logging.error("power off command success")

    if options.tpm1 is True:
        print("Power Off TPM 1")
        try:
            subrack.PowerOffTPM(1)
            logging.info("power off command success")
        except:
            print("power off command failed")
            logging.error("power off command success")

    if options.tpm2 is True:
        print("Power Off TPM 2")
        try:
            subrack.PowerOffTPM(2)
            logging.info("power off command success")
        except:
            print("power off command failed")
            logging.error("power off command success")

    if options.tpm3 is True:
        print("Power Off TPM 3")
        try:
            subrack.PowerOffTPM(3)
            logging.info("power off command success")
        except:
            print("power off command failed")
            logging.error("power off command success")

    if options.tpm4 is True:
        print("Power Off TPM 4")
        try:
            subrack.PowerOffTPM(4)
            logging.info("power off command success")
        except:
            print("power off command failed")
            logging.error("power off command success")

    if options.tpm5 is True:
        print("Power Off TPM 5")
        try:
            subrack.PowerOffTPM(5)
            logging.info("power off command success")
        except:
            print("power off command failed")
            logging.error("power off command success")

    if options.tpm6 is True:
        print("Power Off TPM 6")
        try:
            subrack.PowerOffTPM(6)
            logging.info("power off command success")
        except:
            print("power off command failed")
            logging.error("power off command success")

    if options.tpm7 is True:
        print("Power Off TPM 7")
        try:
            subrack.PowerOffTPM(7)
            logging.info("power off command success")
        except:
            print("power off command failed")
            logging.error("power off command success")

    if options.tpm8 is True:
        print("Power Off TPM 8")
        try:
            subrack.PowerOffTPM(8)
            logging.info("power off command success")
        except:
            print("power off command failed")
            logging.error("power off command success")
