__author__ = 'Bubs'

__author__ = 'Cristian Albanese'
"""This Script permit to on_off Selected TPM inserted in Backplane Board"""
import sys
import time
from optparse import OptionParser
from subrack_management_board import *





subrack=SubrackMngBoard()



usage_string="usage: %prog [options] \n"
usage_hexample="(es power on TPM1 and TPM3). %prog --t1 --t3\n" \
               "(es power on all TPM). %prog --all\n"

if __name__ == '__main__':

    parser = OptionParser(usage =(usage_string+usage_hexample))
    parser.add_option("--t1",
                      action="store_true",
                      dest="tpm1",
                      default=False,
                      help="select TPM1 to power on")
    parser.add_option("--t2",
                      action="store_true",
                      dest="tpm2",
                      default=False,
                      help="select TPM2 to power on")
    parser.add_option("--t3",
                      action="store_true",
                      dest="tpm3",
                      default=False,
                      help="select TPM3 to power on")
    parser.add_option("--t4",
                      action="store_true",
                      dest="tpm4",
                      default=False,
                      help="select TPM4 to power on")
    parser.add_option("--t5",
                      action="store_true",
                      dest="tpm5",
                      default=False,
                      help="select TPM5 to power on")
    parser.add_option("--t6",
                      action="store_true",
                      dest="tpm6",
                      default=False,
                      help="select TPM6 to power on")
    parser.add_option("--t7",
                      action="store_true",
                      dest="tpm7",
                      default=False,
                      help="select TPM7 to power on")
    parser.add_option("--t8",
                      action="store_true",
                      dest="tpm8",
                      default=False,
                      help="select TPM8 to power on")
    parser.add_option("--all",
                      action="store_true",
                      dest="all",
                      default=False,
                      help="select all TPM to power on")
    (options, args) = parser.parse_args()


    if options.all==True:
        for i in range (1,9):
            print("Power On TPM " + str(i))
            try:
                subrack.PowerOnTPM(i)
                logging.info("power on command success")
            except:
                print("power on command failed")
                logging.error("power on command success")
    if options.tpm1==True:
        print("Power On TPM 1")
        try:
            subrack.PowerOnTPM(1)
            logging.info("power on command success")
        except:
            print("power on command failed")
            logging.error("power on command success")
    if options.tpm2==True:
        print("Power On TPM 2")
        try:
            subrack.PowerOnTPM(2)
            logging.info("power on command success")
        except:
            print("power on command failed")
            logging.error("power on command success")
    if options.tpm3==True:
        print("Power On TPM 3")
        try:
            subrack.PowerOnTPM(3)
            logging.info("power on command success")
        except:
            print("power on command failed")
            logging.error("power on command success")
    if options.tpm4==True:
        print("Power On TPM 4")
        try:
            subrack.PowerOnTPM(4)
            logging.info("power on command success")
        except:
            print("power on command failed")
            logging.error("power on command success")
    if options.tpm5==True:
        print("Power On TPM 5")
        try:
            subrack.PowerOnTPM(5)
            logging.info("power on command success")
        except:
            print("power on command failed")
            logging.error("power on command success")

    if options.tpm6==True:
        print("Power On TPM 6")
        try:
            subrack.PowerOnTPM(6)
            logging.info("power on command success")
        except:
            print("power on command failed")
            logging.error("power on command success")
    if options.tpm7==True:
        print("Power On TPM 7")
        try:
            subrack.PowerOnTPM(7)
            logging.info("power on command success")
        except:
            print("power on command failed")
            logging.error("power on command success")
    if options.tpm8==True:
        print("Power On TPM 8")
        try:
            subrack.PowerOnTPM(8)
            logging.info("power on command success")
        except:
            print("power on command failed")
            logging.error("power on command success")
