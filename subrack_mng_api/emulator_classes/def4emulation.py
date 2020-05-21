__author__ = 'Cristian Albanese'
import string
from subprocess import Popen, PIPE
import sys
import os
import psutil
import time
from datetime import datetime
import random
import logging
import xml.etree.ElementTree as eTree

I2C_REG_FILE="subrack_emulator_i2cregs.csv"
class i2cfields:
    bus=0
    devadd=1
    offset=2
    value=3
    default=4
    state=5
    mode=6


CPLD_REGS_FILE="subrack_emulator_cpldregs.csv"

class cpldfields:
    cat=0
    name=1
    value=2
    default=3
    state=4
    mode=5



MAX_TEMP_RANGE_SIM_VALUE = 65
MIN_TEMP_RANGE_SIM_VALUE = 25
i2c1 = 0
i2c2 = 0x1
i2c3 = 0x2

POWERON=0xbb
POWEROFF=0xb3



simulation_regs=[
    {"cat":"FPGA_FW",  "name":"FirmwareVersion","value":  0xe0000001, "def":0xe0000001, "state":0,"mode":"RO"},
    {"cat": "FPGA_FW", "name": "FirmwareBuildLow", "value": 0x05110000, "def": 0x05110000, "state": 0, "mode": "RO"},
    {"cat": "FPGA_FW", "name": "FirmwareBuildHigh", "value": 0x2020, "def": 0x2020, "state": 0, "mode": "RO"},
    {"cat":"HKeep", "name":"TPMsPresent","value":0x0, "def":random.randrange(0xff), "state":0,"mode":"RW"},
    {"cat":"Fram",  "name":"TPM_SUPPLY_STATUS","value":  0x0, "def":0, "state":0,"mode":"RW"},
    #power control power regs
    {"cat":"Fram",  "name": "LTC4281_B1_power","value":  random.triangular(35.5,60.5), "def":0, "state":0,"mode":"RO"},
    {"cat": "Fram", "name": "LTC4281_B2_power", "value": random.triangular(35.5,60.5), "def": 0, "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B3_power", "value": random.triangular(35.5,60.5), "def": 0, "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B4_power", "value": random.triangular(35.5,60.5), "def": 0, "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B5_power", "value": random.triangular(35.5,60.5), "def": 0, "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B6_power", "value": random.triangular(35.5,60.5), "def": 0, "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B7_power", "value": random.triangular(35.5,60.5), "def": 0, "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B8_power", "value": random.triangular(35.5,60.5), "def": 0, "state": 0, "mode": "RO"},
    #power control voltage regs
    {"cat": "Fram", "name": "LTC4281_B1_Vsource", "value": random.randrange(46979, 47769), "def": 0, "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B2_Vsource", "value": random.randrange(46979, 47769), "def": 0, "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B3_Vsource", "value": random.randrange(46979, 47769), "def": 0, "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B4_Vsource", "value": random.randrange(46979, 47769), "def": 0, "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B5_Vsource", "value": random.randrange(46979, 47769), "def": 0, "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B6_Vsource", "value": random.randrange(46979, 47769), "def": 0, "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B7_Vsource", "value": random.randrange(46979, 47769), "def": 0, "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "LTC4281_B8_Vsource", "value": random.randrange(46979, 47769), "def": 0, "state": 0,"mode": "RO"},
    #sensor temperature
    {"cat": "Fram", "name": "ADT7408_B1_temp", "value": random.randrange(0x200, 0x250), "def": random.randrange(0x200, 0x250), "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "ADT7408_B2_temp", "value": random.randrange(0x200, 0x250), "def":random.randrange(0x200, 0x250), "state": 0,"mode": "RO"},
    #management sens temp
    {"cat": "Fram", "name": "Adt1TempValue", "value": random.randrange(0x200, 0x250), "def": random.randrange(0x200, 0x250), "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "Adt2TempValue", "value": random.randrange(0x200, 0x250), "def": random.randrange(0x200, 0x250), "state": 0, "mode": "RO"},
    #fan ctrl regs
    {"cat": "Fram", "name": "FAN1_TACH", "value": random.randrange(1000,1500), "def": random.randrange(1000,1500), "state": 0,"mode": "RO"},
    {"cat": "Fram", "name": "FAN2_TACH", "value": random.randrange(1000,1500), "def": random.randrange(1000,1500), "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "FAN3_TACH", "value": random.randrange(1000,1500), "def": random.randrange(1000,1500), "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "FAN4_TACH", "value": random.randrange(1000,1500), "def": random.randrange(1000,1500), "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "FAN_PWM", "value": 0, "def": 0x2ff3030, "state": 0, "mode": "RO"},
    #psu voltage and current
    {"cat": "Fram", "name": "PSU0_Vout", "value": random.randrange(0x17d0, 0x1850), "def": random.randrange(0x17d0, 0x1850), "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "PSU1_Vout", "value": random.randrange(0x17d0, 0x1850), "def": random.randrange(0x17d0, 0x1850), "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "PSU0_Iout", "value": random.randrange(0x17, 0x30), "def": random.randrange(0x17, 0x30), "state": 0, "mode": "RO"},
    {"cat": "Fram", "name": "PSU1_Iout", "value": random.randrange(0x17, 0x30), "def": random.randrange(0x17, 0x30), "state": 0, "mode": "RO"},

]

simulation_i2c_regs=[
    {"bus":i2c2, "devadd":0x80, "offset":0x0, "value":POWEROFF, "def":POWEROFF, "state":0, "mode":"RW"},    #power_control_tpm_1
    {"bus":i2c2, "devadd":0x82, "offset":0x0, "value":POWEROFF, "def":POWEROFF, "state":0, "mode":"RW"},    #power_control_tpm_2
    {"bus":i2c2, "devadd":0x84, "offset":0x0, "value":POWEROFF, "def":POWEROFF, "state":0, "mode":"RW"},    #power_control_tpm_3
    {"bus":i2c2, "devadd":0x86, "offset":0x0, "value":POWEROFF, "def":POWEROFF, "state":0, "mode":"RW"},    #power_control_tpm_4
    {"bus":i2c2, "devadd":0x88, "offset":0x0, "value":POWEROFF, "def":POWEROFF, "state":0, "mode":"RW"},    #power_control_tpm_5
    {"bus":i2c2, "devadd":0x8a, "offset":0x0, "value":POWEROFF, "def":POWEROFF, "state":0, "mode":"RW"},    #power_control_tpm_6
    {"bus":i2c2, "devadd":0x8c, "offset":0x0, "value":POWEROFF, "def":POWEROFF, "state":0, "mode":"RW"},    #power_control_tpm_7
    {"bus":i2c2, "devadd":0x8e, "offset":0x0, "value":POWEROFF, "def":POWEROFF, "state":0, "mode":"RW"},    #power_control_tpm_8

    {"bus": i2c2, "devadd": 0x80, "offset": 0x4, "value": 0, "def": 0, "state": 0, "mode": "RO"},# power_control_tpm_1_fault_reg
    {"bus": i2c2, "devadd": 0x82, "offset": 0x4, "value": 0, "def": 0, "state": 0, "mode": "RO"},# power_control_tpm_2_fault_reg
    {"bus": i2c2, "devadd": 0x84, "offset": 0x4, "value": 0, "def": 0, "state": 0, "mode": "RO"},# power_control_tpm_3_fault_reg
    {"bus": i2c2, "devadd": 0x86, "offset": 0x4, "value": 0, "def": 0, "state": 0, "mode": "RO"},# power_control_tpm_4_fault_reg
    {"bus": i2c2, "devadd": 0x88, "offset": 0x4, "value": 0, "def": 0, "state": 0, "mode": "RO"},# power_control_tpm_5_fault_reg
    {"bus": i2c2, "devadd": 0x8a, "offset": 0x4, "value": 0, "def": 0, "state": 0, "mode": "RO"}, # power_control_tpm_6_fault_reg
    {"bus": i2c2, "devadd": 0x8c, "offset": 0x4, "value": 0, "def": 0, "state": 0, "mode": "RO"},# power_control_tpm_7_fault_reg
    {"bus": i2c2, "devadd": 0x8e, "offset": 0x4, "value": 0, "def": 0, "state": 0, "mode": "RO"},# power_control_tpm_8_fault_reg

    {"bus": i2c2, "devadd": 0x30, "offset": 0x03, "value": 0, "def": 0, "state": 0, "mode": "RW"},    # temperature alarm l low
    {"bus": i2c2, "devadd": 0x30, "offset": 0x04, "value": 0, "def": 0, "state": 0, "mode": "RW"},    # temperature alarm l high
    {"bus": i2c2, "devadd": 0x32, "offset": 0x03, "value": 0, "def": 0, "state": 0, "mode": "RW"},    # temperature alarm 2 low
    {"bus": i2c2, "devadd": 0x32, "offset": 0x04, "value": 0, "def": 0, "state": 0, "mode": "RW"},    # temperature alarm 2 high

    {"bus": i2c3, "devadd": 0xb0, "offset": 0x78, "value": 0, "def": 0, "state": 0, "mode": "RO"},  # psu 1 status
    {"bus": i2c3, "devadd": 0xb0, "offset": 0x78, "value": 0, "def": 0, "state": 0, "mode": "RO"},  # psu 2 status

    {"bus": i2c3, "devadd": 0xb0, "offset": 0x3b, "value": 2, "def": 2, "state": 0, "mode": "RO"},  # psu 1 fan speed
    {"bus": i2c3, "devadd": 0xb0, "offset": 0x3b, "value": 2, "def": 2, "state": 0, "mode": "RO"},  # psu 2 fan speed
]

def rw_emulator_regs_file(op,cat,name,value=None):
    if op=="r":
        f=open(CPLD_REGS_FILE,'r')
        regs = f.readlines()
        f.seek(0)
        allfile=f.read()
        f.close()
        for i in range (0,len(regs)):
            fields=regs[i].split(",")
            if fields[cpldfields.cat].split(":")[1]==cat and fields[cpldfields.name].split(":")[1]==name:
                if fields[cpldfields.state]=="state:0":
                    stringa=regs[i]
                    new_regs_line=stringa.replace("state:0","state:1")
                    if name=="TPMsPresent":
                        olddata=fields[cpldfields.value]
                        newdata="value:"+hex(random.randrange(1,255))
                        new_regs_line=new_regs_line.replace(olddata,newdata)
                    fw=open(CPLD_REGS_FILE,'w')
                    m=allfile.replace(stringa,new_regs_line)
                    fw.write(m)
                    fw.close()
                    return int(fields[cpldfields.default].split(":")[1],16)
                else:
                    return int(fields[cpldfields.value].split(":")[1],16)
    else:
        newdata="value:"+hex(value)
        f = open(CPLD_REGS_FILE, 'r')
        allfile = f.read()
        f.seek(0)
        regs = f.readlines()
        f.close()
        for i in range(0, len(regs)):
            fields = regs[i].split(",")
            if fields[cpldfields.cat].split(":")[1] == cat and fields[cpldfields.name].split(":")[1] == name:
                actualvalue=fields[cpldfields.value]
                stringa = regs[i]
                if fields[cpldfields.state] == "state:0":
                    new_regs_line = stringa.replace("state:0", "state:1")
                    final_line = new_regs_line.replace(actualvalue,newdata)
                else:
                    final_line = stringa.replace(actualvalue,newdata)
                fw = open(CPLD_REGS_FILE, 'w')
                m = allfile.replace(stringa, final_line)
                fw.write(m)
                fw.close()
                return 0



def rw_emulator_i2c_file(op,bus,devadd,offset,value=None):
    if op=="r":
        f=open(I2C_REG_FILE,'r')
        allfile=f.read()
        f.seek(0)
        regs=f.readlines()
        f.close()
        for i in range (0,len(regs)):
            fields=regs[i].split(",")
            if fields[i2cfields.devadd].split(":")[1]==devadd and fields[i2cfields.offset].split(":")[1]==offset:
                if fields[i2cfields.state]=="state:0":
                    stringa=regs[i]
                    new_regs_line=stringa.replace("state:0","state:1")
                    fw=open(I2C_REG_FILE,'w')
                    m=allfile.replace(stringa,new_regs_line)
                    fw.write(m)
                    fw.close()
                    return int(fields[i2cfields.default].split(":")[1],16)
                else:
                    return int(fields[i2cfields.value].split(":")[1],16)
    else:
        newdata="value:"+hex(value)
        f = open(I2C_REG_FILE, 'r')
        allfile = f.read()
        f.seek(0)
        regs = f.readlines()
        f.close()
        for i in range(0, len(regs)):
            fields = regs[i].split(",")
            if fields[i2cfields.bus].split(":")[1] == bus and fields[i2cfields.devadd].split(":")[1] == devadd and fields[i2cfields.offset].split(":")[1] == offset:
                actualvalue=fields[i2cfields.value]
                stringa = regs[i]
                if fields[i2cfields.state] == "state:0":
                    new_regs_line = stringa.replace("state:0", "state:1")
                    final_line = new_regs_line.replace(actualvalue,newdata)
                else:
                    final_line = stringa.replace(actualvalue,newdata)
                fw = open(I2C_REG_FILE, 'w')
                m = allfile.replace(stringa, final_line)
                fw.write(m)
                fw.close()
                return 0