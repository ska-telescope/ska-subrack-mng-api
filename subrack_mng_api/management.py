__author__ = 'Cristian Albanese'

import string
import subprocess
from subprocess import Popen, PIPE
import sys
import os
import psutil
import time
from datetime import datetime
import random
import logging
from subrack_mng_api.emulator_classes.def4emulation import *
from subrack_mng_api.version import *
from cpld_mng_api.bsp.management_bsp import eep_sec
import cpld_mng_api.bsp.management as cpld_mng
import socket
import struct
import hashlib
import shutil
import parse
from console_progressbar import ProgressBar
import tabulate

import Pyro5.api

lasttemp = 59.875

I2CDevices = ["ADT7408_1", "ADT7408_2", "EEPROM_MAC_1", "EEPROM_MAC_2", "LTC3676", "LTC4281"]

logger=logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.ERROR)

class FPGA_I2CBUS:
    i2c1 = 0
    i2c2 = 0x1
    i2c3 = 0x2


class I2CDevAdd:
    ADT7408_1 = (0x30 >> 1)
    ADT7408_2 = (0x32 >> 1)
    EEPROM_MAC_1 = (0xA0 >> 1)
    EEPROM_MAC_2 = (0xA2 >> 1)
    LTC3676 = (0x78 >> 1)
    LTC4281 = (0x88 >> 1)


class ADTRegs:
    CAPABILTY = 0x00
    CONFIGURATION = 0x01
    ALARM_TEMP_UPPER = 0x02
    REG_ALARM_TEMP_LOWER = 0x03
    CRITICAL_TEMP_TRIP = 0x04
    TEMPERATURE = 0x05

class FPGA_MdioBUS:
    CPU = 1
    CPLD = 2


ethernet_ports=[
    {'name' : 'CPU',    'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 0},# MCU U4-P0
    {'name' : 'CPLD',   'mdio_mux' : FPGA_MdioBUS.CPLD, 'port' : 0},# CPLD U5-P0
    {'name' : 'SLOT-1', 'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 1},# SLOT-1 U4-P1
    {'name' : 'SLOT-2', 'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 2},# SLOT-2 U4-P2
    {'name' : 'SLOT-3', 'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 3},# SLOT-3 U4-P3
    {'name' : 'SLOT-4', 'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 4},# SLOT-4 U4-P4
    {'name' : 'SLOT-5', 'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 5},# SLOT-5 U4-P5
    {'name' : 'SLOT-6', 'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 6},# SLOT-6 U4-P6
    {'name' : 'SLOT-7', 'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 7},# SLOT-7 U4-P7
    {'name' : 'SLOT-8', 'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 8},# SLOT-8 U4-P8
    {'name' : 'P1',     'mdio_mux' : FPGA_MdioBUS.CPLD, 'port' : 9},# U53 U5-P9
    {'name' : 'P2',     'mdio_mux' : FPGA_MdioBUS.CPU,  'port' : 9},# U52 U4-P9
    {'name' : 'P3',     'mdio_mux' : FPGA_MdioBUS.CPLD, 'port' : 5},# J8-B U5-P5
    {'name' : 'P4',     'mdio_mux' : FPGA_MdioBUS.CPLD, 'port' : 6},# J8-A U5-P6
]


smm_i2c_devices=[
    {'name': "ADT7408_1", "ICadd": 0x30 , "i2cbus_id": FPGA_I2CBUS.i2c1, "bus_size":2, "ref_add":0x6,
     "ref_val":0x11d4, "op_check":"ro", "access":"CPLD"},
    {'name': "ADT7408_2", "ICadd": 0x32, "i2cbus_id": FPGA_I2CBUS.i2c1, "bus_size": 2, "ref_add": 0x6,
     "ref_val": 0x11d4, "op_check": "ro", "access":"CPLD"},
    {'name': "LTC3676", "ICadd": 0x78, "i2cbus_id": FPGA_I2CBUS.i2c1, "bus_size": 1, "ref_add": 0x14,
     "ref_val": 0xa5, "res_val":0x0, "op_check": "rw", "access":"CPLD"},
    {'name': "LTC4281", "ICadd": 0x88, "i2cbus_id": FPGA_I2CBUS.i2c1, "bus_size": 1, "ref_add": 0x4c,
     "ref_val": 0xaa, "res_val":0x0, "op_check": "rw", "access":"CPLD"},
    {'name': "EEPROM_MAC_1", "ICadd": 0xA0, "i2cbus_id": FPGA_I2CBUS.i2c1, "bus_size": 1, "ref_add": 0x7f,
     "ref_val": 0xa5, "res_val":0xFF, "op_check": "rw", "access":"CPU"},
    {'name': "EEPROM_MAC_2", "ICadd": 0xA2, "i2cbus_id": FPGA_I2CBUS.i2c1, "bus_size": 1, "ref_add": 0x7f,
     "ref_val": 0xa5, "res_val":0xFF,"op_check": "rw", "access":"CPU"},
]

backplane_i2c_devices=[
    {'name': "ADT7470_1", "ICadd": 0x58, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x3d,
     "ref_val": 0x70, "op_check": "ro", "access":"CPLD"},
    {'name': "ADT7470_2", "ICadd": 0x5e, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x3d,
     "ref_val": 0x70, "op_check": "ro", "access":"CPLD"},
    {'name': "EEPROM", "ICadd": 0xA0, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x7f,
     "ref_val": 0xa5, "res_val": 0xFF, "op_check": "rw", "access": "CPLD"},
    {'name': "ADT7408_1", "ICadd": 0x30, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 2, "ref_add": 0x6,
     "ref_val": 0x11d4, "op_check": "ro", "access": "CPLD"},
    {'name': "ADT7408_2", "ICadd": 0x32, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 2, "ref_add": 0x6,
     "ref_val": 0x11d4, "op_check": "ro", "access": "CPLD"},
    {'name': "LTC4281_1", "ICadd": 0x80, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x30,
     "ref_val": 0x08, "res_val":0x0, "op_check": "ro", "access":"CPLD"},
    {'name': "LTC4281_2", "ICadd": 0x82, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x30,
     "ref_val": 0x08, "res_val": 0x0, "op_check": "ro", "access": "CPLD"},
    {'name': "LTC4281_3", "ICadd": 0x84, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x30,
     "ref_val": 0x08, "res_val": 0x0, "op_check": "ro", "access": "CPLD"},
    {'name': "LTC4281_4", "ICadd": 0x86, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x30,
     "ref_val": 0x08, "res_val": 0x0, "op_check": "ro", "access": "CPLD"},
    {'name': "LTC4281_5", "ICadd": 0x88, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x30,
     "ref_val": 0x08, "res_val": 0x0, "op_check": "ro", "access": "CPLD"},
    {'name': "LTC4281_6", "ICadd": 0x8a, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x30,
     "ref_val": 0x08, "res_val": 0x0, "op_check": "ro", "access": "CPLD"},
    {'name': "LTC4281_7", "ICadd": 0x8c, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x30,
     "ref_val": 0x08, "res_val": 0x0, "op_check": "ro", "access": "CPLD"},
    {'name': "LTC4281_8", "ICadd": 0x8e, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x30,
     "ref_val": 0x08, "res_val": 0x0, "op_check": "ro", "access": "CPLD"},
    {'name': "PCF8574TS_1", "ICadd": 0x40, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": None,
     "ref_val": None, "res_val": 0x0, "op_check": None, "access": "CPLD"},
    {'name': "PCF8574TS_2", "ICadd": 0x42, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": None,
     "ref_val": None, "res_val": 0x0, "op_check": None, "access": "CPLD"},
]

psm_i2c_devices=[
    {'name': "U11-PCF8574TS", "ICadd": 0x40, "i2cbus_id": FPGA_I2CBUS.i2c3, "bus_size": 1, "ref_add": None,
     "ref_val": None, "op_check": "ro", "access": "CPLD"},
    {'name': "U30-EEPROM", "ICadd": 0xA6, "i2cbus_id": FPGA_I2CBUS.i2c3, "bus_size": 1, "ref_add": 0x00,
     "ref_val": None, "op_check": "ro", "access": "CPU"},
    {'name': "J5-PSU1", "ICadd": 0xA0, "i2cbus_id": FPGA_I2CBUS.i2c3, "bus_size": 2, "ref_add": 0x00,
     "ref_val": None, "op_check": "ro", "access": "CPU"},
    {'name': "J6-PSU2", "ICadd": 0xA2, "i2cbus_id": FPGA_I2CBUS.i2c3, "bus_size": 2, "ref_add": 0x00,
     "ref_val": None, "op_check": "ro", "access": "CPU"},
]

monitored_supplies= {
    "V_SOC": {'name': "V_SOC",  "Mon": "MCU", "cat": "MCUR", "reg": "VoltageSOC",  "divider": 1000, "unit": "V", 'exp_value': {'min': 1.30, 'max': 1.40}},
    "V_ARM": {'name': "V_ARM",  "Mon": "MCU", "cat": "MCUR", "reg": "VoltageARM",  "divider": 1000, "unit": "V", 'exp_value': {'min': 1.30, 'max': 1.40}},
    "V_DDR": {'name': "V_DDR",  "Mon": "MCU", "cat": "MCUR", "reg": "VoltageDDR",  "divider": 1000, "unit": "V", 'exp_value': {'min': 1.30, 'max': 1.40}},
    "V_2V5": {'name': "V_2V5",  "Mon": "MCU", "cat": "MCUR", "reg": "Voltage2V5",  "divider": 1000, "unit": "V", 'exp_value': {'min': 2.40, 'max': 2.55}},
    "V_1V0": {'name': "V_1V0",  "Mon": "MCU", "cat": "MCUR", "reg": "Voltage1V0",  "divider": 1000, "unit": "V", 'exp_value': {'min': 0.95, 'max': 1.05}},
    "V_1V1": {'name': "V_1V1",  "Mon": "MCU", "cat": "MCUR", "reg": "Voltage1V1",  "divider": 1000, "unit": "V", 'exp_value': {'min': 1.05, 'max': 1.15}},
    "V_CORE": {'name': "V_CORE", "Mon": "MCU", "cat": "MCUR", "reg": "VoltageVCORE", "divider": 1000, "unit": "V",'exp_value': {'min': 1.18, 'max': 1.22}},
    "V_1V5": {'name': "V_1V5",  "Mon": "MCU", "cat": "MCUR", "reg": "Voltage1V5",  "divider": 1000, "unit": "V", 'exp_value': {'min': 1.48, 'max': 1.52}},
    "V_3V3": {'name': "V_3V3",  "Mon": "MCU", "cat": "MCUR", "reg": "Voltage3V3",  "divider": 1000, "unit": "V", 'exp_value': {'min': 3.25, 'max': 3.35}},
    "V_5V": {'name': "V_5V",   "Mon": "MCU", "cat": "MCUR", "reg": "Voltage5V",  "divider": 1000, "unit": "V",'exp_value': {'min': 4.95, 'max': 5.05}},
    "V_3V": {'name': "V_3V",   "Mon": "MCU", "cat": "MCUR", "reg": "Voltage3V",  "divider": 1000, "unit": "V", 'exp_value': {'min': 2.95, 'max': 3.35}},
    "V_2V8": {'name': "V_2V8",  "Mon": "MCU", "cat": "MCUR", "reg": "Voltage2V8", "divider": 1000, "unit": "V",'exp_value': {'min': 2.75, 'max': 2.85}},
}

TPM_PRESENT_MASK = [0x1, 0x2, 0x4, 0x8, 0x80, 0x40, 0x20, 0x10]

print_debug = False
devices='/sys/bus/platform/devices/'
categories = {
    "FPGA_FW" : {
        'path' : '8000000.skamngfpga',
        },
    "UserReg" : {
        'path' : '8000f00.skamnguserreg',
        },
    "MCUR" : {
        'path' : '8030000.skamngmcuregs',
        },
    "Led" : {
        'path' : '8000400.skamngled',
        },
    "HKeep" : {
        'path' : '8000500.skamnghkregs',
        },
    "ETH" : {
        'path' : '8000100.skamngethregs',
        },
    "Fram" : {
        'path' : '8090000.skamngframregs',
        },
    "FPGA_I2C" : {
        'path' : '8010000.skamngfpgai2c',
        },
    "Lock" : {
        'path' : '80c0000.skamnglockregs',
        },
    "CtrlRegs" : {
        'path' : '8000900.skamngctrlregs',
        },
    "CpldUart" : {
        'path' : '8070000.skamngcplduartregs',
        },
    "Mdio" : {
        'path' : '8060000.skamngmdio',
        },
    }

Error_p = "ERROR"

FpgaFwVersionReg_list = []
MCUReg_list = []
UserLedReg_list = []
HKeepRegs_list = []
EthRegs_list = []
UserReg_list = []
FramRegs_list = []
LockRegs_list = []
CtrlRegs_list = []
CpldUart_list = []

def exec_cmd(cmd,dir=None,verbose=True, exclude_line="", tee_file = None):
    start_time = time.time()
    try:
        # if tee_file is not None:
        #     cmd = cmd + " | tee -a " + tee_file
        if verbose:
            print("Exec command: \"" + cmd + "\"")
        if dir is None:
            child = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell = True)
        else:
            child = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell = True, cwd=dir)
        out = ""
        err = ""
        n_lines=0
        while child.poll() is None:
            line = child.stdout.readline()
            line = line.decode("utf-8")
            n_lines+=1
            if line:
                if verbose:
                    #if exclude_line not in line or exclude_line == "":
                        print(line.strip())
                out += line
        returncode = child.returncode
        if verbose:
            print(n_lines, returncode)
            if n_lines==0 and out!="":
                lines = out.splitlines()
                for l in lines:
                    print(l)
        #return {'out':out,'returncode':returncode}
        return out,returncode
    except KeyboardInterrupt:
        print("...CTRL+C...")
        raise NameError("exec_cmd fails: \""+cmd+"\"")


def run(command):
    if sys.version_info[0]<3:
        running = False
        process = Popen(command, stdout=PIPE, shell=True)
        time.sleep(0.1)
        # while(process.poll() is None):
        #    running=True
        #    output = process.stdout.readline()
        #    print output,
        output = process.communicate()[0]
        # print output,
    else:
        output = subprocess.getoutput(command)
    return output


def get_cat(name):
    # cat=name[0:(string.find(name,"."))]
    cat = name
    if cat in categories:
        categ=os.path.join(devices,categories[name]['path'],'parameters/')
    else:
        categ = Error_p
    if print_debug:
        logger.debug("from get_cat: name " + name)
        logger.debug("from get_cat: cat " + cat)
        logger.debug("from get_cat: category " + categ)
    return categ


def translate_reg(name):
    # cat=name[0:(string.find(name,"."))]
    cat = name[0:name.find(".")]
    if cat in categories:
        categ=os.path.join(devices,categories[cat]['path'],'parameters/')
    else:
        categ = Error_p
    if print_debug:
        logger.debug("from translate_reg: name " + name)
        logger.debug("from translate_reg: cat " + cat)
        logger.debug("from translate_reg: category " + categ)
    # return categ+name[(string.find(name,"."))+1:]
    return categ + name[name.find(".") + 1:]


def reg_name(name):
    # reg=name[(string.find(name,".")+1):len(name)-1]
    reg = name[(name.find(".") + 1):len(name) - 1]


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

PAGE_SIZE = 512

def loadBitstream(filename, pagesize):
    print ("Open Bistream file %s" % (filename))
    with open(filename, "rb") as f:
        dump = bytearray(f.read())
    bitstreamSize = len(dump)

    pages = bitstreamSize // pagesize
    if (pages * pagesize) != bitstreamSize:
        pages = pages + 1
    print("Loading %s (%d bytes) = %d * %d bytes pages" % (filename, bitstreamSize, pages, pagesize))
    s = pages * pagesize
    tmp = bytearray(s)
    for i in range(bitstreamSize):
        tmp[i] = dump[i]
    for i in range(s - bitstreamSize):
        tmp[i + bitstreamSize] = 0xff
    return tmp, bitstreamSize, s

CPULOCK_UNLOCK_VAL = 0xfffffff

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

class mcu2cplduartbuff():
    rxbuff = []
    txbuff = []
    rxusedflag = False
    txusedflag = False


### Management Class
# This class contain methods to permit access to all registers connected to the
# management CPU (iMX6) mapped in filesystem
@Pyro5.api.expose
@Pyro5.server.behavior(instance_mode="single")
class Management():
    def __init__(self, simulation=False, cpld_timeout=10, get_board_info = True):
        self.mcuuart = mcu2cplduartbuff()
        self.data = []
        self.simulation = simulation
        self.eep_sec = eep_sec
        seq=smm_i2c_devices
        key="name"
        self.smm_i2c_devices_dict=dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))
        if self.simulation == False:
            self.get_fpga_fw_version()
            # set gpio for I2C control Request
            cmd = "ls -l /sys/class/gpio/"
            gpiolist = str(run(cmd))
            gpios = gpiolist.splitlines()
            gpioexist = False
            for l in range(0, len(gpios)):
                if gpios[l].find("gpio134") != -1:
                    gpioexist = True
                    break
            if gpioexist == False:
                cmd = "echo 134 > /sys/class/gpio/export"
                run(cmd)
            cmd = "echo out > /sys/class/gpio/gpio134/direction"
            run(cmd)
            cmd = "echo 1 > /sys/class/gpio/gpio134/value"
            run(cmd)
            self.create_all_regs_list()
            self.CpldMng = cpld_mng.MANAGEMENT(ip=self.get_cpld_actual_ip(), port="10000", timeout=cpld_timeout)
        import ska_low_smm_bios.bios
        self.hw_rev=self.get_hardware_revision()
        self.BIOS_REV_list = ska_low_smm_bios.bios.bios_get_dict(hw_rev=self.hw_rev)
        self.board_info = None
        if get_board_info:
            self.board_info=self.get_board_info()


    def __del__(self):
        self.data = []

    def ip2long(self, ip):
        """
        Convert an IP string to long
        """
        packed_ip = socket.inet_aton(ip)
        return struct.unpack("!L", packed_ip)[0]
    
    def long2ip(self, ip):
        """
        Convert long to IP string
        """
        return socket.inet_ntoa(struct.pack("!I", ip))

    ###create_all_regs_list
    # This method permit to fill all categories
    # register lists (<category_name>_list variable)
    def create_all_regs_list(self):
        for key,value in categories.items():
            cmd = "ls -l " + get_cat(key)
            regs = str(run(cmd))
            # print regs
            lines = regs.splitlines()
            value['list']=[]
            for l in range(0, len(lines)):
                if lines[l].find("root") != -1:
                    value['list'].append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
            # print(key,"_list:",value['list'])

    ###dump_categories
    # This method permit to print
    # all available registers categories
    def dump_categories(self):
        result=[]
        for key in categories.items():
            result.append(key)
            print(key)
        return result

    ###read
    # This method implements read
    # operation of selected register
    # @param[in] name name of register it must have following format <category_name>.<register_name>
    # return read register value
    def read(self, name):
        if self.simulation == True:
            reg_category = name.split(".")[0]
            reg_name = name.split(".")[1]
            el = [element for element in simulation_regs if
                  (element.get("cat", "") == reg_category and element.get("name", "") == reg_name)]
            if el[0].get("mode") == "RO":
                if el[0].get("state") == 0:
                    val = el[0].get("def")
                    el[0]["state"] = 1
                else:
                    val = el[0].get("value")
                # print("Read: " + name + ", " + hex(val))
                return int(val)
            else:
                val = rw_emulator_regs_file("r", reg_category, reg_name)
                return int(val)
        else:
            reg = translate_reg(name)
            if reg != Error_p:
                if print_debug:
                    logger.debug("Opening file")
                fo = open(reg, "r")
                value = fo.readline()
                value = value[0:len(value) - 1]
                fo.close()
            else:
                value = 0  # self.lastError = res
            if print_debug:
                logger.debug("Read: " + name + ", " + hex(value))
            read_val = int(value)
            if read_val < 0:
                read_val = read_val + (1 << 32)
            return read_val


    ###write
    # This method implements write
    # operation of selected register
    # @param[in] name: name of register it must have following format <category_name>.<register_name>
    # @param[in] value: value will be write in selected register
    def write(self, name, value):
        if self.simulation == True:
            reg_category = name.split(".")[0]
            reg_name = name.split(".")[1]
            el = [element for element in simulation_regs if
                  (element.get("cat", "") == reg_category and element.get("name", "") == reg_name)]
            if el[0].get("mode") == "RO":
                if el[0].get("state") == 0:
                    el[0]["state"] = 1
                el[0]["value"] = value
            else:
                rw_emulator_regs_file("w", reg_category, reg_name, value)
        else:
            if print_debug:
                logger.debug("Write: " + name + ", " + hex(value))
            reg = translate_reg(name)
            if print_debug:
                logger.debug("register: " + reg)
            if reg != Error_p:
                if print_debug:
                    logger.debug("Opening file")
                fo = open(reg, "w")
                fo.write(str(value))
                fo.close()
                self.lastError = 0
            else:
                self.lastError = "Register " + reg + " Not Exist"  # value = value[0:len(res)-1]

    ### get_fpga_fw_version
    # This method return the FPGA Fw version, version buid year and build date
    # return version: version of FW
    # return builddate: date and hour of FW build
    # return buildyear: year of FW build
    def get_fpga_fw_version(self):
        version = self.read("FPGA_FW.FirmwareVersion")
        str_version="0x{:08x}".format(version & 0xffffffff)
        builddate = self.read("FPGA_FW.FirmwareBuildLow")
        buildyear = self.read("FPGA_FW.FirmwareBuildHigh")
        str_date = "{:04x}".format(buildyear&0xffff)+"/"
        str_date+= "{:02x}".format((builddate&0xff000000)>>24)+"/"
        str_date+= "{:02x}".format((builddate&0xff0000)>>16)+"-"
        str_date+= "{:02x}".format((builddate&0xff00)>>8)+":"
        str_date+= "{:02x}".format((builddate&0xff))
        return str_version, str_date

    def get_bios(self):
        bios_dict={}
        bios_dict['rev']="v?.?.?"
        bios_dict['cpld']=hex(self.read("FPGA_FW.FirmwareVersion")) + "_" + hex(self.read("FPGA_FW.FirmwareBuildHigh") << 32 | self.read("FPGA_FW.FirmwareBuildLow"))
        bios_dict['mcu']=hex(self.read("MCUR.McuFWBuildVersion")) + "_" + hex(self.read("MCUR.McuFWBuildDate") << 32 | self.read("MCUR.McuFWBuildTime"))
        bios_dict['uboot']="NA"
        uboot_release = run("sudo dd if=/dev/mmcblk0boot0 | strings | grep U-Boot")
        for line in uboot_release.splitlines():
            r=parse.parse("U-Boot {} ({} {} {} - {} {})",line)
            if r is not None:
                bios_dict['uboot']=r[0]
                break
        bios_dict['krn']=run("uname -r")
        string=""
        _first_key = True
        for key,value in bios_dict.items():
            if key != 'rev':
                if not _first_key:
                    string +='-'
                string += key + "_" + value
                _first_key = False
        
        
        
        
        for BIOS_REV in self.BIOS_REV_list:
            if BIOS_REV[1] == string:
                bios_dict['rev']="v%s"%BIOS_REV[0]
                break

        final_string = bios_dict['rev'] + " (%s)" % string
        return final_string, bios_dict

    def get_hardware_revision(self):
        logger.debug("get_hardware_revision")
        hw_rev_arr = self.get_field("HARDWARE_REV")
        hw_rev = 0
        for byte in hw_rev_arr:
            hw_rev = hw_rev * 256 + byte
        logger.debug("get_hardware_revision 0x%x"%hw_rev)
        if hw_rev == 0xffffff or hw_rev == 0x0:
            raise Exception("Could not read HARDWARE_REV from EEPROM, returned: " + hex(hw_rev))
        return hw_rev

    def get_field(self, key):
        if self.eep_sec[key]["type"] == "ip":
            return self.long2ip(self.eep_rd32(self.eep_sec[key]["offset"]))
        elif self.eep_sec[key]["type"] == "bytearray":
            arr = bytearray()
            for offset in range(self.eep_sec[key]["size"]):
                arr.append(self.eep_rd8(self.eep_sec[key]["offset"]+offset))
            return arr
        elif self.eep_sec[key]["type"] == "string":
            return self.rd_string(self.eep_sec[key])
        elif self.eep_sec[key]["type"] == "uint":
            val = 0
            for offset in range(self.eep_sec[key]["size"]):
                val = val * 256 + self.eep_rd8(self.eep_sec[key]["offset"]+offset)
            return val
        
    def set_field(self, key, value, override_protected=False):
        if self.eep_sec[key]["protected"] is False or override_protected:
            if self.eep_sec[key]["type"] == "ip":
                self.eep_wr32(self.eep_sec[key]["offset"], self.ip2long(value))
            elif self.eep_sec[key]["type"] == "bytearray":
                for offset in range(self.eep_sec[key]["size"]):
                    self.eep_wr8(self.eep_sec[key]["offset"] + offset,
                             ((value & (0xff << (8*(self.eep_sec[key]["size"]-1-offset))))
                              >> (8*(self.eep_sec[key]["size"]-1-offset))) & 0xff)
            elif self.eep_sec[key]["type"] == "string":
                self.wr_string(self.eep_sec[key], value)
            elif self.eep_sec[key]["type"] == "uint":
                val = value
                for offset in range(self.eep_sec[key]["size"]):
                    self.eep_wr8(self.eep_sec[key]["offset"]+offset, val & 0xff)
                    val = val >> 8
        else:
            print("Writing attempt on protected sector %s" % key)

    def eep_rd8(self, offset, release_lock = True):
        dev=self.smm_i2c_devices_dict['EEPROM_MAC_1']
        return self.read_i2c(dev["i2cbus_id"],dev["ICadd"]>>1,offset,"b",release_lock=release_lock)

    def eep_rd16(self, offset):
        rd = 0
        release_lock = False
        for n in range(2):
            if n == 2-1:
                release_lock = True
            rd = rd << 8
            rd = rd | self.eep_rd8(offset+n, release_lock = release_lock)
        return rd

    def eep_rd32(self, offset):
        rd = 0
        release_lock = False
        for n in range(4):
            if n == 4-1:
                release_lock = True
            rd = rd << 8
            rd = rd | self.eep_rd8(offset+n, release_lock = release_lock)
        return rd
    
    def wr_string(self, partition, string):
        return self._wr_string(partition["offset"], string, partition["size"])

    def _wr_string(self, offset, string, max_len=16):
        addr = offset
        for i in range(len(string)):
            self.eep_wr8(addr, ord(string[i]), release_lock = False)
            addr += 1
            if addr >= offset + max_len:
                break
        if addr < offset + max_len:
            self.eep_wr8(addr, ord("\n"), release_lock = True)
        else:
            self.eep_rd8(addr, release_lock = True)

    def rd_string(self, partition):
        return self._rd_string(partition["offset"], partition["size"])

    def _rd_string(self, offset, max_len=16):
        addr = offset
        string = ""
        for i in range(max_len):
            byte = self.eep_rd8(addr, release_lock = False)
            if byte == ord("\n") or byte == 0xff:
                break
            string += chr(byte)
            addr += 1
        self.eep_rd8(addr, release_lock = True)
        return string
    
    def eep_wr8(self, offset, data, release_lock = True):
        dev=self.smm_i2c_devices_dict['EEPROM_MAC_1']
        return self.write_i2c(dev["i2cbus_id"],dev["ICadd"]>>1,offset,"b",data, release_lock = release_lock)

    def eep_wr16(self, offset, data):
        release_lock = False
        for n in range(2):
            if n == 2-1:
                release_lock = True
            self.eep_wr8(offset+n, (data >> 8*(1-n)) & 0xFF,release_lock=release_lock)
            
        return

    def eep_wr32(self, offset, data):
        release_lock = False
        for n in range(4):
            if n == 4-1:
                release_lock = True
            self.eep_wr8(offset+n, (data >> 8*(3-n)) & 0xFF,release_lock=release_lock)
        return

    def get_mac(self,mac):
        mac_str = ""
        for i in range(0,len(mac)-1):
            mac_str += '{0:02x}'.format(mac[i])+":"
        mac_str += '{0:02x}'.format(mac[len(mac)-1])
        return mac_str

    def get_cpu_mac(self):
        mac=(self.read("ETH.Mac1_H")<<32)+self.read("ETH.Mac1_L")
        res=bytearray()
        for i in range(6):
            res.append((mac>>8*(5-i))&0xff)
        return res

    def detect_cpu_ip(self):
        cmd = "ip -f inet addr show eth0"
        ret = run(cmd)
        lines = ret.splitlines()
        found = False
        cpu_ip = None
        netmask = None
        for r in range(0, len(lines)):
            if str(lines[r]).find("inet") != -1:
                _cpu_ip = str(lines[r]).split(" ")[5]
                cpu_ip = _cpu_ip.split("/")[0]
                netmask = _cpu_ip.split("/")[1]
                netmask = self.long2ip(~(2**(32-int(netmask))-1) & 0xffffffff)
                found = True
                break
        
        gateway = None
        gateway_str=run('ip route | grep default')
        if gateway_str != '':
            gateway_str = gateway_str.split()
            if len(gateway_str) >= 5:
                gateway = gateway_str[2]
        if gateway is None:
            logger.error("detect_cpu_ip - Cannot detect Gateway!")
            
        if found is False:
            logger.error("detect_cpu_ip - Cannot detect!")
        return cpu_ip,netmask,gateway


    def get_board_info(self):
        bios_string,bios_dict=self.get_bios()
        mng_info={}
        mng_info["EXT_LABEL_SN"] = self.get_field("EXT_LABEL_SN")
        mng_info["EXT_LABEL_PN"] = self.get_field("EXT_LABEL_PN")
        mng_info["SN"] = self.get_field("SN")
        mng_info["PN"] = self.get_field("PN")
        mng_info["SMB_UPS_SN"] = self.get_field("UPS_SMB_SN")
        
        pcb_rev = self.get_field("PCB_REV")
        if pcb_rev == 0xff:
            pcb_rev_string = ""
        else:
            pcb_rev_string = str(pcb_rev)
        hw_rev = self.get_field("HARDWARE_REV")
        mng_info["HARDWARE_REV"] = "v" + str(hw_rev[0]) + "." + str(hw_rev[1]) + "." + str(hw_rev[2]) + pcb_rev_string
        if self.get_field("BOARD_MODE") == 0x1:
            mng_info["BOARD_MODE"] = "SUBRACK"
        elif self.get_field("BOARD_MODE") == 0x2:
            mng_info["BOARD_MODE"] = "CABINET"
        else:
            mng_info["BOARD_MODE"] = "UNKNOWN"
            # print("Board Mode Read value ", self.get_field("BOARD_MODE"))
        for key,value in bios_dict.items():
            if key == 'rev':
                mng_info['bios'] = value
            else:
                mng_info['bios_'+key] = value
        mng_info["OS"] = run('cat /etc/issue.net')
        mng_info["OS_rev"] = run('sudo git -C /etc describe --tag --dirty')
        root = run('mount | head -n 1 | cut -d\  -f1')
        if root == "/dev/mmcblk1p2":
            mng_info["OS_root"] = "uSD"
        elif root == "/dev/mmcblk0p2":
            mng_info["OS_root"] = "EMMC0"
        elif root == "/dev/mmcblk0p4":
            mng_info["OS_root"] = "EMMC1"
        else:
            mng_info["OS_root"] = "unknown"

        boot_sel = self.get_field("BOOT_SEL")
        mng_info["BOOT_SEL_KRN"] = boot_sel & 0x1
        mng_info["BOOT_SEL_FS"] = (boot_sel & 0x2) >> 1
        mng_info["CPLD_ip_address"] = self.long2ip(self.read("ETH.IP"))
        mng_info["CPLD_netmask"] = self.long2ip(self.read("ETH.Netmask"))
        mng_info["CPLD_gateway"] = self.long2ip(self.read("ETH.Gateway"))
        mng_info["CPLD_ip_address_eep"] = self.get_field("ip_address")
        mng_info["CPLD_netmask_eep"] = self.get_field("netmask")
        mng_info["CPLD_gateway_eep"] = self.get_field("gateway")
        mng_info["CPLD_MAC"] = self.get_mac(self.get_field("MAC"))
        mng_info["CPU_ip_address"] = self.detect_cpu_ip()[0]
        mng_info["CPU_netmask"] = self.detect_cpu_ip()[1]
        mng_info["CPU_MAC"] = self.get_mac(self.get_cpu_mac())


        return mng_info

    ### get_housekeeping_flag
    # This method return selected housekeeping regs/flag
    # @param[in] name: name of register/flag will be read
    # return flag_value: selected flag value
    def get_housekeeping_flag(self, name):
        flag_value = self.read("HKeep." + name)
        return flag_value

    ### set_polling_time
    # This method select the devices polling time period of MCU in ms
    # @param[in] pooll_time: polling time in ms
    def set_polling_time(self, poll_time):
        self.write("MCUR.McuPollingTime", poll_time)

    ### get_polling_time
    # This method return the devices polling time period of MCU in ms
    # return regval: polling time in ms
    def get_polling_time(self):
        polltime = self.read("MCUR.McuPollingTime")
        logger.info("Actual polling time: " + str('%.2f' % (polltime)) + " ms")
        return polltime

    def dump_registers(self,key=None):
        result={}
        if key is None:
            for key,category in categories.items():
                result[key]={}
                for reg in category['list']:
                    reg_name=key+"."+reg
                    value = self.read(reg_name)
                    print(reg_name + " = " + hex(value & 0xffffffff) + "(%d)"%value)
                    result[key][reg]=value
        else:
            category=categories[key]
            result[key]={}
            for reg in category['list']:
                reg_name=key+"."+reg
                value = self.read(reg_name)
                print(reg_name + " = " + hex(value & 0xffffffff) + "(%d)"%value)
                result[key][reg]=value
        return result

    ### test_eim_access
    # This method permit to test the access on EIM bus from CPU
    # @param[in] iteration: number of iteration of the tests pattern are reads and wrtite and verifyed
    # @return errors: test result, 0 test passed, 1 to 4 error detected in correspondig test pattern check
    # @return i: iterations executed
    def test_eim_access(self, iteration=1000):
        errors = 0
        patterns = [0x0, 0xffffffff, 0x5555aaaa, 0xaaaa5555]
        for i in range(0, iteration):
            for k in range(0, len(patterns)):
                self.write("UserReg.UserReg0", patterns[k])
                rd_data = self.read("UserReg.UserReg0")
                if rd_data != patterns[k]:
                    logger.error("test_eim_access: ERROR at iteration i, expected %x, read %x " % (i, patterns[k], rd_data))
                    errors = k+1
                    return errors, i
        return errors, i
    
    ### test_ucp_access
    # This method permit to test the access on UCP bus from CPU
    # @param[in] iteration: number of iteration of the tests pattern are reads and wrtite and verifyed
    # @return errors: test result, 0 test passed, 1 to 4 error detected in correspondig test pattern check
    # @return i: iterations executed
    def test_ucp_access(self, iteration=1000):
        reg_add = 0xf04 #"UserReg.UserReg1"
        errors = 0
        patterns = [0x0, 0xffffffff, 0x5555aaaa, 0xaaaa5555]
        for i in range(0, iteration):
            for k in range(0, len(patterns)):
                self.CpldMng.write_register(reg_add, patterns[k])
                rd_data = self.CpldMng.read_register(reg_add)
                if rd_data != patterns[k]:
                    logger.error("test_ucp_access: ERROR at iteration i, expected %x, read %x " % (i, patterns[k], rd_data))
                    errors = k+1
                    return errors, i
        return errors, i


    ### get_mcu_reg
    # This method return selected MCU register value
    # @param[in] name: name of register will be read
    # return regvalue_value: selected flag value
    def get_mcu_reg(self, name):
        regvalue = self.read("MCUR." + name)
        return hex(regvalue & 0xffffffff)

    ### dump_mcu_regs_all
    # This method print all MCU Registers values
    def dump_mcu_regs_all(self):
        cat=categories['MCUR']
        for reg in cat['list']:
            i=0
            reg_name="MCUR."+name
            reg_value = self.read(reg_name)
            if (i > 6 and i < 19):
                print(reg_name + " = " + str('%.2f' % (float(reg_value) / 1000)))
            elif (i >= 19 and i < (len(cat['list']) - 1)):
                print(reg_name + " = " + str('%.2f' % (reg_value)))
            elif (i == (len(cat['list']) - 1)):
                print(reg_name + " = " + str('%.2f' % (float(reg_value) / 10)))
            else:
                print(reg_name + " = " + hex(reg_value & 0xffffffff))

    # get_cpld_actual_ip
    # This method retrieve the IP Adddress assigned to CPLD on board
    # return ipadd:ipaddress string
    def get_cpld_actual_ip(self):
        ip = self.read("ETH.IP")
        logger.info("Read ip: %s" % hex(ip))
        ipadd = []
        ipadd.append((ip & 0xff000000) >> 24)
        ipadd.append((ip & 0x00ff0000) >> 16)
        ipadd.append((ip & 0x0000ff00) >> 8)
        ipadd.append((ip & 0x000000ff))
        ipstring = str(ipadd[0]) + "." + str(ipadd[1]) + "." + str(ipadd[2]) + "." + str(ipadd[3])
        logger.info("ipstring %s" % ipstring)
        return ipstring

    ###get_fram_reg
    # This method return selected FPGA Ram register value
    # @param[in] name: name of register will be read
    # return regvalue_value: selected flag value
    def get_fram_reg(self, name):
        regvalue = self.read("Fram." + name)
        return hex(regvalue & 0xffffffff)

    ###list_i2c_devadd
    # This method print all name and addresses devices connected to I2C bus accessible from CPU
    def list_i2c_devadd(self):
        for i in range(0, len(I2CDevices)):
            logger.info("Device: " + vars(I2CDevAdd).keys()[i + 1] + ", add: " + hex(vars(I2CDevAdd).values()[i + 1]))

    ###read_i2c
    # This method implements read on i2c bus directly from CPU
    # @param[in] bus_id: bus index where device is connected on
    # @param[in] device_add: device address
    # @param[in] reg_offset: offset of device register
    # @param[in] size_type: type of access (b byte, w word 16b)
    # return value: read register value
    # Note: this operation require to stop the MCU I2C access during read to arbitrate access, it's make using gpio signal
    # from CPU and MCU
    def read_i2c(self, bus_id, device_add, reg_offset, size_type, release_lock = True):
        # logger.debug(bus_id)
        cmd = "echo 0 > /sys/class/gpio/gpio134/value"
        # logger.debug(cmd)
        run(cmd)
        retry = 0
        while (retry < 1000):
            value=self.read("MCUR.GPReg3")
            if (value == 0x12c0dead):
                break
            retry = retry + 1
            time.sleep(0.001)
        if retry == 1000:
            logger.error("read_i2c - Maxretry on lock (MCUR.GPReg3)")
            cmd = "echo 1 > /sys/class/gpio/gpio134/value"
            run(cmd)
            time.sleep(0.1)
            self.write("Lock.CPULock", CPULOCK_UNLOCK_VAL)
            os.remove("/run/lock/mngfpgai2c.lock")
            return 0
        #logger.error("Maxretry read_i2c fpga access (MCUR.GPReg3) %d"%retry)
        cmd = "sudo i2cget -y -f " + str(bus_id) + " " + hex(device_add) + " " + hex(reg_offset) + " " + size_type
        value = run(cmd)
        if release_lock:
            cmd = "echo 1 > /sys/class/gpio/gpio134/value"
            run(cmd)
        if value == 'Error: Read failed':
            return None
        return int(value,16)

    ###write_i2c
    # This method implements write on i2c bus directly from CPU
    # @param[in] bus_id: bus index where device is connected on
    # @param[in] device_add: device address
    # @param[in] reg_offset: offset of device register
    # @param[in] size_type: type of access (b byte, w word 16b)
    # Note: this operation require to stop the MCU I2C access during read to arbitrate access, it's make using gpio signal
    # from CPU and MCU
    def write_i2c(self, bus_id, device_add, reg_offset, size_type, data, release_lock = True):
        cmd = "echo 0 > /sys/class/gpio/gpio134/value"
        run(cmd)
        time.sleep(0.02)
        while (1):
            if (self.read("MCUR.GPReg3") == 0x12c0dead):
                break
        cmd = "sudo i2cset -y -f " + str(bus_id) + " " + hex(device_add) + " " + hex(reg_offset) + " " + hex(
            data) + " " + size_type
        value = run(cmd)
        if release_lock:
            cmd = "echo 1 > /sys/class/gpio/gpio134/value"
            run(cmd)
        return value

    ###fpgai2c_op
    # This method implements operation on i2c2 and i2c3 bus devices
    # @param[in] ICadd: address of IC2 Device
    # @param[in] wrbytenum: number of byte will be write
    # @param[in] rdbytenum: number of byte will be read
    # @param[in] datatx: data to write
    # @param[in] i2cbus_id: select i2cbus where operation will be made
    # return data,status: data in case of a read opeartion, and operation status, 0 operation succesfull
    # Note: this operation require to stop the MCU I2C access during read to arbitrate access, it's make using gpio signal
    # from CPU and MCU
    def fpgai2c_op(self, ICadd, wrbytenum, rdbytenum, datatx, i2cbus_id):
        logger.debug("I2C OP 0x%x 0x%x 0x%x 0x%x 0x%x" % (ICadd, wrbytenum, rdbytenum, datatx, i2cbus_id))
        MAXRETRY = 100
        ICadd = ICadd >> 1
        thispid = os.getpid()
        timeout = False
        # print("Start I2C OP")
        inittime = time.time()
        # check if device is locked from another process
        if os.path.exists("/run/lock/mngfpgai2c.lock") == True:
            start = time.time()
            # wait the unlock or timeout of 5 sec
            while (1):
                if (os.path.exists("/run/lock/mngfpgai2c.lock") == False):
                    break
                now = time.time()
                if (now - start > 5):
                    fo = open("/run/lock/mngfpgai2c.lock", "r")
                    lockedpid = fo.readline()
                    fo.close()
                    delta = time.time()
                    logger.debug("fpgai2c_op - len lockedpid = %d, lockedpid val %s, elapsed time %d" % (
                        len(lockedpid), lockedpid, delta - inittime))
                    if len(lockedpid) != 0:
                        if check_pid(int(lockedpid)) == False:
                            os.remove("/run/lock/mngfpgai2c.lock")
                            break
                        else:
                            timeout = True
                        break
                    else:
                        os.remove("/run/lock/mngfpgai2c.lock")
        if timeout:
            logger.error("fpgai2c_op - TIMEOUT")
            return 0xff, -1
        else:
            fo = open("/run/lock/mngfpgai2c.lock", "w")
            fo.write(str(thispid))
            fo.close()

        self.write("Lock.CPULock", 0x8010000)
        start = time.time()
        while (1):
            lockvalue = self.read("Lock.CPULock")
            if lockvalue == 0x8010000:
                # print "CPU Locked"
                break
            now = time.time()
            if (now - start > 5):
                os.remove("/run/lock/mngfpgai2c.lock")
                logger.error("timeout locking cpu")
                return 0xff, -1
        # command=(rdbytenum<<24)|(wrbytenum<<16)|(i2cbus_id)|(ICadd>>1)cat /sy  bus
        # datatx_n=((datatx&0xff)<<24)|((datatx&0xff00>>8)<<24)|((datatx&0xff0000>>16)<<16)|((datatx&0xff000000>>24))
        # print "Write txdata swapped %x " %datatx

        command = (rdbytenum << 12) | (wrbytenum << 8) | (i2cbus_id << 16) | (ICadd)
        # print "Command %x" %command
        cmd = "echo 0 > /sys/class/gpio/gpio134/value"
        run(cmd)
        time.sleep(0.001)
        retry = 0
        while (retry < 1000):
            value=self.read("MCUR.GPReg3")
            if (value == 0x12c0dead):
                break
            retry = retry + 1
            time.sleep(0.001)
        if retry == 1000:
            logger.error("fpgai2c_op -  Maxretry on lock (MCUR.GPReg3)")
            cmd = "echo 1 > /sys/class/gpio/gpio134/value"
            run(cmd)
            time.sleep(0.1)
            self.write("Lock.CPULock", CPULOCK_UNLOCK_VAL)
            os.remove("/run/lock/mngfpgai2c.lock")
            return 0xff, 0x1
        # else:
        #     logger.error("Maxretry i2c fpga access (MCUR.GPReg3) %d"%retry)

        self.write("FPGA_I2C.twi_wrdata", datatx)
        if print_debug:
            logger.debug("fpgai2c_op - command = " + hex(command))
        if ICadd == (0xA0>>1):
            self.CpldMng.bsp.i2c_set_passwd_no_mcu_rst()
        self.write("FPGA_I2C.twi_command", command)
        
        retry = 0
        while (retry < MAXRETRY):
            status = self.read("FPGA_I2C.twi_status")
            if (status == 0):
                break
            else:
                if status == 2 or status == 3:
                    logger.error("fpgai2c_op - Not Acknowledge detected")
                    cmd = "echo 1 > /sys/class/gpio/gpio134/value"
                    run(cmd)
                    time.sleep(0.1)
                    self.write("Lock.CPULock", CPULOCK_UNLOCK_VAL)
                    os.remove("/run/lock/mngfpgai2c.lock")
                    return 0xff, status
                elif status == 1:
                    retry = retry + 1
                    time.sleep(0.001)
        if retry == MAXRETRY:
            logger.error("fpgai2c_op - Maxretry i2c fpga access ")
            cmd = "echo 1 > /sys/class/gpio/gpio134/value"
            run(cmd)
            time.sleep(0.1)
            self.write("Lock.CPULock", CPULOCK_UNLOCK_VAL)
            os.remove("/run/lock/mngfpgai2c.lock")
            return 0xff, 0x1
        datarx = self.read("FPGA_I2C.twi_rdata")
        # print "Read data %x " %datarx
        if (i2cbus_id != FPGA_I2CBUS.i2c3):
            if (rdbytenum > 1):
                tempbyte0 = datarx & 0xff
                tempbyte1 = (datarx & 0xff00) >> 8
                tempbyte2 = (datarx & 0xff0000) >> 16
                tempbyte3 = (datarx & 0xff000000) >> 24
                datarx = 0x0
                if (rdbytenum == 2):
                    datarx = ((tempbyte0 << 8) + tempbyte1)
                if (rdbytenum == 3):
                    datarx = ((tempbyte0 << 16) + (tempbyte1 << 8) + tempbyte2)
                if (rdbytenum == 4):
                    datarx = ((tempbyte0 << 24) + (tempbyte1 << 16) + (tempbyte2 << 8) + tempbyte3)

        # datarx=((datarx_r&0xff)<<24)|((datarx_r&0xff00>>8)<<24)|((datarx_r&0xff0000>>16)<<16)|((datarx_r&0xff000000>>24))
        # print "Read data swapped %x " %datarx
        cmd = "echo 1 > /sys/class/gpio/gpio134/value"
        run(cmd)
        time.sleep(0.001)
        self.write("Lock.CPULock", CPULOCK_UNLOCK_VAL)
        os.remove("/run/lock/mngfpgai2c.lock")
        logger.debug("fpgai2c_op - End I2C OP")
        return datarx, 0

    def fpgai2c_write8(self, ICadd, reg_add, datatx, i2cbus_id):
        if self.simulation == True:
            el = [element for element in simulation_i2c_regs if (
                    element.get("devadd", "") == ICadd and element.get("offset", "") == reg_add and element.get(
                "bus", "") == i2cbus_id)]
            if el[0].get("mode") == "RO":
                el[0]["value"] = datatx
                return 0
            else:
                if i2cbus_id == 0:
                    i2cbus = "i2c1"
                elif i2cbus_id == 1:
                    i2cbus = "i2c2"
                elif i2cbus_id == 2:
                    i2cbus = "i2c3"
                rw_emulator_i2c_file("w", i2cbus, hex(ICadd), hex(reg_add), datatx)
                return 0
        else:
            data2wr = (datatx << 8) | (reg_add & 0xFF)
            data, status = self.fpgai2c_op(ICadd, 2, 1, data2wr, i2cbus_id)
            return status

    def fpgai2c_read8(self, ICadd, reg_add, i2cbus_id):
        i2cbus = "i2c1"
        if self.simulation == True:
            el = [element for element in simulation_i2c_regs if (
                    element.get("devadd", "") == ICadd and element.get("offset", "") == reg_add and element.get(
                "bus", "") == i2cbus_id)]
            if el[0].get("mode") == "RO":
                if len(el) != 0:
                    return el[0].get("value") & 0xff, 0
                else:
                    return 0, -1
            else:
                if i2cbus_id == 0:
                    i2cbus = "i2c1"
                elif i2cbus_id == 1:
                    i2cbus = "i2c2"
                elif i2cbus_id == 2:
                    i2cbus = "i2c3"
                val = rw_emulator_i2c_file("r", i2cbus, hex(ICadd), hex(reg_add))
                return val, 0
        else:
            if reg_add is None:
                data, status = self.fpgai2c_op(ICadd, 0, 1, 0x0, i2cbus_id)
            else:
                data2wr = (reg_add & 0xFF)
                data, status = self.fpgai2c_op(ICadd, 1, 1, data2wr, i2cbus_id)
            return data, status

    def fpgai2c_write16(self, ICadd, reg_add, datatx, i2cbus_id):
        if self.simulation == True:
            el = [element for element in simulation_i2c_regs if (
                    element.get("devadd", "") == ICadd and element.get("offset", "") == reg_add and element.get(
                "bus", "") == i2cbus_id)]
            if el[0].get("mode") == "RO":
                el[0]["value"] = datatx & 0xffff
                return 0
            else:
                if i2cbus_id == 0:
                    i2cbus = "i2c1"
                elif i2cbus_id == 1:
                    i2cbus = "i2c2"
                elif i2cbus_id == 2:
                    i2cbus = "i2c3"
                rw_emulator_i2c_file("w", i2cbus, hex(ICadd), hex(reg_add), datatx & 0xffff)
                return 0
        else:
            if i2cbus_id == FPGA_I2CBUS.i2c3:
                # data2wr=((datatx&0xff00)>>8)|((datatx&0x00ff)<<8)
                data2wr = (datatx << 8) | (reg_add & 0xFF)
            else:
                data2wr = ((datatx & 0xff00) >> 8) | ((datatx & 0x00ff) << 8)
                data2wr = (data2wr << 8) | (reg_add & 0xFF)
            data, status = self.fpgai2c_op(ICadd, 3, 1, data2wr, i2cbus_id)
            return status

    def fpgai2c_read16(self, ICadd, reg_add, i2cbus_id):
        if self.simulation == True:
            el = [element for element in simulation_i2c_regs if (
                    element.get("devadd", "") == ICadd and element.get("offset", "") == reg_add and element.get(
                "bus", "") == i2cbus_id)]
            if el[0].get("mode") == "RO":
                if len(el) != 0:
                    return el[0].get("value") & 0xffff, 0
                else:
                    return 0, -1
            if i2cbus_id == 0:
                i2cbus = "i2c1"
            elif i2cbus_id == 1:
                i2cbus = "i2c2"
            elif i2cbus_id == 2:
                i2cbus = "i2c3"
            val = rw_emulator_i2c_file("r", i2cbus, hex(ICadd), hex(reg_add))
            return val & 0xffff, 0
        else:
            data2wr = (reg_add & 0xFF)
            data, status = self.fpgai2c_op(ICadd, 1, 2, data2wr, i2cbus_id)
            if i2cbus_id == FPGA_I2CBUS.i2c3:
                datar = data
            else:
                # datar=((data&0xff00)>>8)|((data&0x00ff)<<8)
                datar = data
            return datar, status


    def check_i2c_board_devices_access(self, board="SMB"):
        result = []
        wr_op_passed = False
        if board == "BACKPLANE":
            dev_list = backplane_i2c_devices
            self.write("CtrlRegs.BkplOnOff", 1)
        elif board == "PSU_ADAPTER":
            dev_list = psm_i2c_devices
        elif board == "SMB":
            dev_list = smm_i2c_devices
        else:
            logger.error("Invalid board parameter, accepted SMB, BACKPLANE or PSU_ADAPTER")
            return None
        for i in range(0, len(dev_list)):
            logger.info("Device: %s" %dev_list[i]["name"])
            if dev_list[i]["access"] == "CPLD":
                if dev_list[i]["op_check"] == "ro":
                    retval=0
                    if dev_list[i]["bus_size"] == 2:
                        retval,state = self.fpgai2c_read16(dev_list[i]["ICadd"], dev_list[i]["ref_add"],
                                                           dev_list[i]["i2cbus_id"])
                    else:
                        retval,state = self.fpgai2c_read8(dev_list[i]["ICadd"], dev_list[i]["ref_add"],
                                                          dev_list[i]["i2cbus_id"])
                    if state != 0:
                        result.append({"name":dev_list[i]["name"],"test_result": "FAILED",
                                        "expected": dev_list[i]["ref_val"],
                                        "read": None})
                        logger.info("FAILED, checking dev: %s, no ACK reveived" % (dev_list[i]["name"]))
                        continue
                    if dev_list[i]["ref_val"] is not None:
                        if retval != dev_list[i]["ref_val"]:
                            result.append({"name":dev_list[i]["name"],"test_result": "FAILED",
                                        "expected": dev_list[i]["ref_val"],
                                        "read": retval})
                            logger.info("FAILED, checking dev: %s, read value %x, expected %x" % (dev_list[i]["name"],
                                                                                                retval, dev_list[i]["ref_val"]))
                        else:
                            result.append({"name":dev_list[i]["name"],"test_result": "PASSED",
                                        "expected": dev_list[i]["ref_val"],
                                        "read": retval})
                            logger.info("PASSED, checking dev: %s, read value %x, expected %x" % (dev_list[i]["name"],
                                                                                                retval, dev_list[i]["ref_val"]))
                    else:
                        result.append({"name":dev_list[i]["name"],"test_result": "PASSED",
                                        "expected": dev_list[i]["ref_val"],
                                        "read": retval})
                        logger.info("PASSED, checking dev: %s, read value %x, nothing expected" % (dev_list[i]["name"], retval))
                if dev_list[i]["op_check"] == "rw":
                    retval=0
                    if dev_list[i]["bus_size"] == 2:
                        logger.info("Writing16...")
                        self.fpgai2c_write16(dev_list[i]["ICadd"], dev_list[i]["ref_add"],
                                             dev_list[i]["ref_val"],dev_list[i]["i2cbus_id"])
                        logger.info("reading16...")
                        retval,state = self.fpgai2c_read16(dev_list[i]["ICadd"], dev_list[i]["ref_add"],
                                                           dev_list[i]["i2cbus_id"])

                    else:
                        logger.info("Writing8...")
                        self.fpgai2c_write8(dev_list[i]["ICadd"], dev_list[i]["ref_add"],
                                            dev_list[i]["ref_val"], dev_list[i]["i2cbus_id"])
                        logger.info("reading8...")
                        retval,state = self.fpgai2c_read8(dev_list[i]["ICadd"], dev_list[i]["ref_add"],
                                                          dev_list[i]["i2cbus_id"])
                    if retval != dev_list[i]["ref_val"]:
                        result.append({"name":dev_list[i]["name"],"test_result": "FAILED",
                                       "expected": dev_list[i]["ref_val"],
                                       "read": retval})
                        logger.info("FAILED, checking dev: %s, read value %x, expected %x" % (dev_list[i]["name"],
                                                                                              retval,
                                                                                              dev_list[i]["ref_val"]))
                    else:

                        wr_op_passed = True
                        result.append({"name":dev_list[i]["name"],"test_result": "PASSED",
                                       "expected": dev_list[i]["ref_val"],
                                       "read": retval})
                        logger.info("PASSED, checking dev: %s, read value %x, expected %x" % (dev_list[i]["name"],
                                                                                              retval,
                                                                                              dev_list[i]["ref_val"]))
                    if wr_op_passed == True:
                        logger.info("Restoring value")
                        if dev_list[i]["bus_size"] == 2:
                            self.fpgai2c_write16(dev_list[i]["ICadd"], dev_list[i]["ref_add"],
                                                 dev_list[i]["res_val"],dev_list[i]["i2cbus_id"])
                        else:
                            self.fpgai2c_write8(dev_list[i]["ICadd"], dev_list[i]["ref_add"],
                                                dev_list[i]["res_val"], dev_list[i]["i2cbus_id"])
            elif dev_list[i]["access"] == "CPU":
                if dev_list[i]["op_check"] == "ro":
                    retval = 0
                    if dev_list[i]["bus_size"] == 2:
                        retval = self.read_i2c(dev_list[i]["i2cbus_id"],dev_list[i]["ICadd"] >> 1,
                                               dev_list[i]["ref_add"],"w")
                    else:
                        retval = self.read_i2c(dev_list[i]["i2cbus_id"],dev_list[i]["ICadd"] >> 1,
                                               dev_list[i]["ref_add"],"b")
                    if retval is None:
                        result.append({"name":dev_list[i]["name"],"test_result": "FAILED",
                                        "expected": dev_list[i]["ref_val"],
                                        "read": retval})
                        logger.info("FAILED, checking dev: %s, no ACK reveived" % (dev_list[i]["name"]))
                        continue
                    if dev_list[i]["ref_val"] is not None:
                        if retval != dev_list[i]["ref_val"]:
                            result.append({"name":dev_list[i]["name"],"test_result": "FAILED",
                                        "expected": dev_list[i]["ref_val"],
                                        "read": retval})
                            logger.info("FAILED, checking dev: %s, read value %x, expected %x" % (dev_list[i]["name"],
                                                                                                retval,
                                                                                                dev_list[i]["ref_val"]))
                        else:
                            result.append({"name":dev_list[i]["name"],"test_result": "PASSED",
                                        "expected": dev_list[i]["ref_val"],
                                        "read": retval})
                            logger.info("PASSED, checking dev: %s, read value %x, expected %x" % (dev_list[i]["name"],
                                                                                                retval,
                                                                                                dev_list[i]["ref_val"]))
                    else:
                        result.append({"name":dev_list[i]["name"],"test_result": "PASSED",
                                        "expected": dev_list[i]["ref_val"],
                                        "read": retval})
                        logger.info("PASSED, checking dev: %s, read value %x, nothing expected" % (dev_list[i]["name"], retval))
                if dev_list[i]["op_check"] == "rw":
                    retval = 0
                    if dev_list[i]["bus_size"] == 2:
                        logger.info("Writing16...")
                        self.write_i2c(dev_list[i]["i2cbus_id"],dev_list[i]["ICadd"] >> 1,
                                       dev_list[i]["ref_add"],"w",dev_list[i]["ref_val"])
                        logger.info("reading16...")
                        retval = self.read_i2c(dev_list[i]["i2cbus_id"],dev_list[i]["ICadd"] >> 1,
                                               dev_list[i]["ref_add"],"w")
                    else:
                        logger.info("Writing8...")
                        self.write_i2c(dev_list[i]["i2cbus_id"],dev_list[i]["ICadd"] >> 1,
                                       dev_list[i]["ref_add"],"b",dev_list[i]["ref_val"])
                        logger.info("reading8...")
                        retval = self.read_i2c(dev_list[i]["i2cbus_id"],dev_list[i]["ICadd"] >> 1,
                                               dev_list[i]["ref_add"],"b")
                    if retval != dev_list[i]["ref_val"]:
                        result.append({"name":dev_list[i]["name"],"test_result": "FAILED",
                                       "expected": dev_list[i]["ref_val"],
                                       "read": retval})
                        logger.info("FAILED, checking dev: %s, read value %x, expected %x" % (dev_list[i]["name"],
                                                                                              retval,
                                                                                              dev_list[i]["ref_val"]))
                    else:

                        wr_op_passed = True
                        result.append({"name":dev_list[i]["name"],"test_result": "PASSED",
                                       "expected": dev_list[i]["ref_val"],
                                       "read": retval})
                        logger.info("PASSED, checking dev: %s, read value %x, expected %x" % (dev_list[i]["name"],
                                                                                              retval,
                                                                                              dev_list[i]["ref_val"]))
                    if wr_op_passed == True:
                        logger.info("Restoring value")
                        if dev_list[i]["bus_size"] == 2:
                            self.write_i2c(dev_list[i]["i2cbus_id"], dev_list[i]["ICadd"] >> 1,
                                           dev_list[i]["ref_add"], "w", dev_list[i]["res_val"])
                        else:
                            self.write_i2c(dev_list[i]["i2cbus_id"], dev_list[i]["ICadd"] >> 1,
                                           dev_list[i]["ref_add"], "b", dev_list[i]["res_val"])
            else:
                pass
        return result
    def cpu_runtime_mem_test(self):
        """
        method used to exexute a ddr test while OS is running
        :return dictionary with all phases test results
        """
        results = []
        errors = 0
        cmd = "sudo memtester 32M 1"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("cpu_runtime_mem_test: error while execute command")
            results.append({"DDR TEST": "FAILED"})
            return results
        lines = out.splitlines()
        #for l in range(0,len(lines)):
        #    res = parse.parse("  {}: {}", lines[l])
        #    if res != None:
        #       results.append({res[0].split(" ")[0] : res[1]})
        #       if res[1] != "ok":
        #               errors += 1
        if lines[len(lines)-1] != "Done.":
            errors += 1
        if errors != 0:
            results.append({"DDR TEST": "FAILED"})
        else:
            results.append({"DDR TEST": "PASSED"})
        return results

    def get_monitored_board_supplies_list(self):
        measures = []
        for key, value in monitored_supplies.items():
            measures.append(value["name"])
        return measures

    def get_monitored_board_supplies(self, measure):
        f_voltage = float("nan")
        for key, value in monitored_supplies.items():
            if measure in value["name"]:
                voltage = self.read("%s.%s" % (value["cat"], value["reg"]))
                f_voltage = float(voltage / value["divider"])
                f_voltage = round(f_voltage, 2)
                break
        if measure == "V_3V":
            #workaround to fix MCU bug on resistor partitor (1000-925 instead of 1000-1150) for V_3V
            f_voltage = f_voltage / (1150 / ( 1000 + 1150))
            f_voltage = f_voltage * (925 / ( 1000 + 925))
        f_voltage = round(f_voltage,2)
        return f_voltage

    def check_board_supplies(self):
        results = []
        test_pass = "FAILED"
        for key, value in monitored_supplies.items():
            voltage = self.read("%s.%s" % (value["cat"], value["reg"]))
            f_voltage = float(voltage / value["divider"])
            f_voltage = round(f_voltage, 2)
            if f_voltage < value["exp_value"]["min"] or f_voltage > value["exp_value"]["max"]:
                test_pass = "FAILED"
            else:
                test_pass = "PASSED"
            results.append({"name":value["name"], "get": f_voltage, "min": value["exp_value"]["min"], "max": value["exp_value"]["max"], "result":test_pass })
        return results



    def mdio_read22(self, mux, phy_adr, register):
        self.write("Mdio.CFG_REG0", 0xc000 | ((0x3 & mux) << 10) | ((0x1f & phy_adr) << 5))
        self.write("Mdio.ADR_REG1", register)
        value = self.read("Mdio.RAW_REG2") & 0xffff
        return value

    def mdio_write22(self, mux, phy_adr, register, value):
        self.write("Mdio.CFG_REG0", 0xc000 | ((0x3 & mux) << 10) | ((0x1f & phy_adr) << 5))
        self.write("Mdio.ADR_REG1", register)
        self.write("Mdio.RAW_REG2", value)

    def set_SFP(self,mdio_mux=FPGA_MdioBUS.CPLD):
        logger.info("set_SFP")
        # /* Set Ports in 1000Base-X
        self.mdio_write22(mdio_mux, 9, 0x0, 0x9)
        # /* P9
        self.mdio_write22(mdio_mux, 0x1c, 25, 0xF054)
        self.mdio_write22(mdio_mux, 0x1c, 24, 0x8124)
        self.mdio_write22(mdio_mux, 0x1c, 25, 0x400c)
        self.mdio_write22(mdio_mux, 0x1c, 24, 0x8524)
        self.mdio_write22(mdio_mux, 0x1c, 25, 0xF054)
        self.mdio_write22(mdio_mux, 0x1c, 24, 0x8124)
        self.mdio_write22(mdio_mux, 0x1c, 25, 0x4000)
        self.mdio_write22(mdio_mux, 0x1c, 24, 0x8524)
        # /*Start configuring ports for traffic
        # /*Clear power down bit and reset SERDES P9
        self.mdio_write22(mdio_mux, 0x1c, 25, 0x2000)
        self.mdio_write22(mdio_mux, 0x1c, 24, 0x8124)
        self.mdio_write22(mdio_mux, 0x1c, 25, 0xa040)
        self.mdio_write22(mdio_mux, 0x1c, 24, 0x8524)
        # /*Fix 1000Base-X AN advertisement
        # /*write45 4.2004.5 to 1
        # /* ADDR 0x09
        self.mdio_write22(mdio_mux, 0x1c, 25, 0x2004)
        self.mdio_write22(mdio_mux, 0x1c, 24, 0x8124)
        self.mdio_write22(mdio_mux, 0x1c, 25, 0x20)
        self.mdio_write22(mdio_mux, 0x1c, 24, 0x8524)
        # /*Enable Forwarding on ports:
        self.mdio_write22(mdio_mux, 9, 4, 0x007F)
        # get_port_cfg(9, mdio_mux)

    def GetMngTemp(self, sens_id):
        if sens_id < 1 or sens_id > 2:
            logger.error("Error Invalid ID")
            return 0
        temperature = self.read("Fram.Adt" + str(sens_id) + "TempValue")
        if (temperature & 0x1000) >> 12 == 1:
            temp = float((temperature & 0xfff - 4096)) / 16
        else:
            temp = float((temperature & 0xfff)) / 16
        temp = round(temp, 2)
        return temp

    # ##get_voltage_smb
    # This method return the input voltage 12V0 voltage measured by the LTC4281 power control
    # return vout: voltage value in V
    def get_voltage_smb(self):
        dev = self.smm_i2c_devices_dict["LTC4281"]
        data_h = self.read("Fram.LTCVsourceH")
        data_l = self.read("Fram.LTCVsourceL")
        voltage = ((data_h << 8) & 0xff00) | (data_l & 0xff)
        vout = float(voltage * 16.64) / 65535
        vout = round(vout, 2)
        if print_debug:
            logger.info("voltage, " + str(vout))
        return vout

    # ##check_input_voltage_smb
    # This method check expected value of input voltage 12V0
    # return results: dictionary with status an value of operation
    def check_input_voltage_smb(self):
        vout = self.get_voltage_smb()
        vref = 12
        results = []
        if vout < (vref - (vref / 100 * 5)) or vout > ((vref + (vref / 100 * 5))):
            test_pass = "FAILED"
        else:
            test_pass = "PASSED"
        results.append({"name": "12V0", "get": vout, "min": (vref - (vref / 100 * 5)), "max": (vref + (vref / 100 * 5)),
                        "result": test_pass})
        return results


    # SW UPDATE METHODS SECTION
    def flash_uboot(self, uboot_file):
        """
        method used to flash the u-boot bootloader
        :param uboot_file: u-boot binary file absolute path
        :return status of the operation, 0 PASSED, !=0 FAILED
        """
        logging.info("Flashing U-BOOT... ")
        if os.path.isfile(uboot_file) is False:
            logging.error("flash_uboot: invalid u-boot file path, file not found")
            return 1
        uboot_length = os.path.getsize(uboot_file)
        cmd = "echo 0 > /sys/block/mmcblk0boot0/force_ro"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_uboot: error while disabling force_ro flag")
            return 2
        cmd = "sudo dd if=" + uboot_file + " of=/dev/mmcblk0boot0 bs=1024 seek=1"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_uboot: error while writing uboot binary")
            return 3
        cmd = "sudo dd if=/dev/mmcblk0boot0 of=/tmp/dumped_uboot bs=1 skip=1024 count=%s" %uboot_length
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_uboot: error while dump write uboot")
            return 4
        md5_write_uboot = hashlib.md5(open("/tmp/dumped_uboot", 'rb').read()).hexdigest()
        md5_upd_uboot = hashlib.md5(open(uboot_file, 'rb').read()).hexdigest()
        if md5_write_uboot != md5_upd_uboot:
            logging.error("flash_uboot: error while enabling force_ro flag")
            return 5
        cmd = "echo 1 > /sys/block/mmcblk0boot0/force_ro"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_uboot: error while enabling force_ro flag")
            return 6
        logging.info("flash_uboot: OPERATION SUCCESSFULLY COMPLETED")
        return 0

    def fuse_setting(self):
        """
        method used to configure CPU Fuse to boot from flashed bootlaoder
        :return status of the operation, 0 PASSED, !=0 FAILED
        """
        error = 0
        logging.info("FUSE Setting... ")
        cmd = "echo 0x00000010 > /sys/fsl_otp/HW_OCOTP_CFG5"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("fuse_setting: error while writing fuse HW_OCOTP_CFG5")
            return 1
        cmd = "echo 0x0002060 > /sys/fsl_otp/HW_OCOTP_CFG4"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("fuse_setting: error while writing fuse HW_OCOTP_CFG4")
            return 2
        cmd = "sudo  mmc bootpart enable 1 1 /dev/mmcblk0boot0"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("fuse_setting: error while writing bootpart")
            return 3
        cmd = "sudo mmc bootbus set single_backward x1 x8 /dev/mmcblk0boot0"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("fuse_setting: error while writing bootbus")
            return 4
        cmd = "cat /sys/fsl_otp/HW_OCOTP_CFG5"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("fuse_setting: error while reading HW_OCOTP_CFG5")
            return 5
        else:
            out = out[:len(out)-1]
            if out != "0x10":
                logging.error("fuse_setting: HW_OCOTP_CFG5 different form expected, read %s, expected 0x10" %out )
                error += 10
        cmd = "cat /sys/fsl_otp/HW_OCOTP_CFG4"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("fuse_setting: error while reading HW_OCOTP_CFG4")
            return 6
        else:
            out = out[:len(out)-1]
            if out != "0x2060":
                logging.error("fuse_setting: HW_OCOTP_CFG4 different form expected, read %s, expected 0x2060" %out )
                error += 20
        if error == 0:
            logging.info("SETTING FUSE: OPERATION SUCCESSFULLY COMPLETED")
        else:
            logging.error("SETTING FUSE: OPERATION FAILED")
        return error

    def set_krn_boot_partition(self, part):
        """
        method used to set the flash partition where u-boot search the kernel image
        :param part: value of teh partition where u-boot search the kernel image, acceppted EMMC0 or EMMC1
        :return status of the operation, 0 PASSED, !=0 FAILED
        """
        logging.info("Setting kernel boot partition...")
        if part == "EMMC0":
            partition = 0
        elif part == "EMMC1":
            partition = 1
        else:
            logging.error("set_krn_boot_partition: invalid device accepted EMMC0 or EMMC1")
            return 1
        boot_sel = self.get_field("BOOT_SEL")
        boot_sel = (boot_sel & 0x2) | partition
        self.set_field("BOOT_SEL", boot_sel)
        boot_sel_n = self.get_field("BOOT_SEL")
        if boot_sel_n != boot_sel:
            logging.error("set_krn_boot_partition: operation failed expected %d returned %" %(boot_sel, boot_sel_n) )
            return 2
        else:
            logging.info("set_krn_boot_partition: operation successfully completed")
            return 0

    def set_fs_boot_partition(self, part):
        """
        method used to set the flash partition where u-boot search the FileSystem of OS
        :param part: value of teh partition where u-boot search the FileSystem, acceppted EMMC0 or EMMC1
        :return status of the operation, 0 PASSED, !=0 FAILED
        """
        if part == "EMMC0":
            partition = 0
        elif part == "EMMC1":
            partition = 1
        else:
            logging.error("set_krn_boot_partition: invalid device accepted EMMC0 or EMMC1")
            return 1
        boot_sel = self.get_field("BOOT_SEL")
        boot_sel = (boot_sel & 0x1) | (partition << 1)
        self.set_field("BOOT_SEL", boot_sel)
        boot_sel_n = self.get_field("BOOT_SEL")
        if boot_sel_n != boot_sel:
            logging.error("set_krn_boot_partition: operation failed expected %d returned %" % (boot_sel, boot_sel_n))
            return 2
        else:
            logging.info("set_krn_boot_partition: operation successfully completed")
            return 0

    def flash_fs_image(self, fs_image_path, device):
        """
        method used to set the flash FileSystem image on selected device and partition
        :param fs_image_path: path of tar.gz fs file image
        :param device: disk device and partition where image will be placed, accepted EMMC0, EMMC1
        :return status of the operation, 0 PASSED, !=0 FAILED
        """
        logging.info("Flash FS image started operation take some minutes... ")
        if os.path.isfile(fs_image_path) is False:
            logging.error("flash_fs_image: invalid FS image file path, file not found")
            return 1
        if device == "EMMC0":
            dev = "/dev/mmcblk0p2"
        elif device == "EMMC1":
            dev = "/dev/mmcblk0p4"
        else:
            logging.error("flash_fs_image: invalid device accepted EMMC0 or EMMC1")
            return 1
        cmd = "mount"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_fs_image: error while mount command execution")
            return 2
        outl = out.splitlines()
        for k in range(0, len(outl)):
            if outl[k].find("/dev/mmcblk") != -1:
                if outl[k].split(" ")[0] == dev:
                    logging.error("flash_fs_image: selected device is already mounted and in use select different")
                    return 3
        cmd = "sudo mkfs.ext4 %s" %dev
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_fs_image: error while formatting partition %s"%dev)
            return 4
        cmd = "sudo mount %s /mnt/" %dev
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_fs_image: error while mount command execution")
            return 5
        logging.info("flash_fs_image: starting unzip image")
        cmd = "sudo tar --xattrs --xattrs-include=* -xvzf %s -C /mnt/" %fs_image_path
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_fs_image: error while unzip execution")
            return 6
        cmd = "sudo umount /mnt"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("flash_fs_image: error while umount execution")
            return 7
        logging.info("flash_fs_image: operation succefully completed")
        return 0
    
    def emmc_get_size(self):
        """
        method used to return eMMC size in GB
        :return eMMC size in GB
        """
        cmd = "lsblk"
        out, retcode = exec_cmd(cmd, verbose=False)
        if retcode != 0:
            logging.error("emmc_get_size: error while get emmc size")
            return None
        else:
            outl = out.splitlines()
            r = outl[1]
            size = parse.parse("mmcblk0      179:0    0 {}G  0 disk ", r)
            size = size[0]
            size = size.replace(",", ".")

        logging.info("emmc_config: detected EMMC size of %s G" % size)
        emmc_size = float(size)
        return emmc_size

    def emmc_config(self, layout_file):
        """
        method used to flash first time the CPU kernel
        :param layout_file: EMMC layout file
        :return status of the operation, 0 PASSED, !=0 FAILED
        """
        logging.info("EMMC Configuration started... ")
        if os.path.isfile(layout_file) is False:
            logging.warning("emmc_config: invalid layout file path, file not found at %s"%layout_file)
            layout_file = os.path.join(os.path.dirname(__file__),layout_file)
            if os.path.isfile(layout_file) is False:
                logging.error("emmc_config: invalid layout file path, file not found at %s"%layout_file)
                return 1
        cmd = "lsblk"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("emmc_config: error while get emmc size")
            return 6
        else:
            outl = out.splitlines()
            r = outl[1]
            size = parse.parse("mmcblk0      179:0    0 {}G  0 disk ", r)
            size = size[0]
            size = size.replace(",", ".")

        logging.info("emmc_config: detected EMMC size of %s G" % size)
        emmc_size = float(size)
        sector_size_max = 14680064
        if emmc_size < 10:
            sector_size_max = 8134656

        f = open(layout_file, 'r')
        lines = f.readlines()
        for l in range(5, len(lines)):
            p_size = parse.parse("/dev/mmcblk0p{}: start={}, size={}, type={}",lines[l])
            if int(p_size[2]) > sector_size_max:
                logging.error("emmc_config: invalid layout file wrong partition size ")
                return 10
        cmd = "sudo sfdisk /dev/mmcblk0 < " + layout_file
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("emmc_config: error while partion creating")
            return 2
        cmd = "sudo mkfs.vfat /dev/mmcblk0p1"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("emmc_config: error while formatting partition p1")
            return 3
        cmd = "sudo mkfs.ext4 /dev/mmcblk0p2"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("emmc_config: error while formatting partition p2")
            return 4
        cmd = "sudo mkfs.vfat /dev/mmcblk0p3"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("emmc_config: error while formatting partition p2")
            return 5
        cmd = "sudo mkfs.ext4 /dev/mmcblk0p4"
        out, retcode = exec_cmd(cmd, verbose=True)
        if retcode != 0:
            logging.error("emmc_config: error while formatting partition p1")
            return 3
        cmd = "lsblk"
        out, retcode = exec_cmd(cmd, verbose=True)
        time.sleep(2)
        find_count = 0
        if retcode != 0:
            logging.error("emmc_config: error while formatting partition p2")
            return 5
        else:
            outl = out.splitlines()
            for k in range(0,len(outl)):
                if outl[k].find("0p1") != -1:
                    find_count += 1
                if outl[k].find("0p2") != -1:
                    find_count += 1
                if outl[k].find("0p3") != -1:
                    find_count += 1
                if outl[k].find("0p4") != -1:
                    find_count += 1
                if find_count == 4:
                    partition_ok = True
                    break
            if partition_ok is False:
                logging.error("emmc_config: EMMC Configuration Failed, not all expected partition detected")
                return 5
            else:
                logging.info("emmc_config: EMMC Configuration SUCCESSFULLY COMPLETED")
                return 0


    def write_kernel(self, zImage_path, dtb_path, dest_device=None):
        """
        method used to flash first time the CPU kernel
        :param zImage_path: path of the zImage file to be used for the write
        :param dtb_path: path of the device-tree file to be used for the write
        :param dest_device: memory where the write must be executed, accepted value are: uSD or EMMC0 or EMMC1
        :return status of the operation, 0 PASSED, !=0 FAILED
        """

        dev = ""
        if dest_device == "uSD":
            dev = "/dev/mmcblk1p1"
        elif dest_device == "EMMC0":
            dev = "/dev/mmcblk0p1"
        elif dest_device == "EMMC1":
            dev = "/dev/mmcblk0p3"
        elif dest_device is None:
            cp_cmd = "mount"
            out, retcode = exec_cmd(cp_cmd, verbose=True)
            if retcode != 0:
                logging.error("write_kernel: ")
                return 1
            else:
                outl = out.splitlines()
                for k in range(0, len(outl)):
                    if outl[k].find("/dev/mmcblk") != -1:
                        dev = outl[k].split(" ")[0]
                        break
                if dev == "":
                    logging.error("write_kernel: unable to detect valid mounted device")
                    return 2

        else:
            logging.error("write_kernel: invalid dest_device parameter, accepted uSD or EMMC")
            return 3
        logging.info("Write kernel in %s started... " % dev)
        if os.path.isfile(zImage_path) is False:
            logging.error("write_kernel: invalid zImage file path, file not found")
            return 4
        if os.path.isfile(dtb_path) is False:
            logging.error("write_kernel: invalid dtb file path, file not found")
            return 5

        mount_cmd = "sudo mount " + dev + " /mnt"
        out, retcode = exec_cmd(mount_cmd, verbose=True)
        if retcode != 0:
            logging.error("write_kernel: error while mounting kernel partition")
            return 6

        md5_upd_kernel = hashlib.md5(open(zImage_path, 'rb').read()).hexdigest()
        md5_upd_dtb = hashlib.md5(open(dtb_path, 'rb').read()).hexdigest()

        cp_cmd = "sudo cp " + zImage_path + " /mnt/zImage"
        out, retcode = exec_cmd(cp_cmd, verbose=True)
        if retcode != 0:
            logging.error("write_kernel: error while kernel copy")
            return 7
        cp_cmd = "sudo cp " + dtb_path + " /mnt/ska-management.dtb"
        out, retcode = exec_cmd(cp_cmd, verbose=True)
        if retcode != 0:
            logging.error("write_kernel: error while device-tree copy")
            return 8

        md5_cpd_kernel = hashlib.md5(open("/mnt/zImage", 'rb').read()).hexdigest()
        md5_cpd_dtb = hashlib.md5(open("/mnt/ska-management.dtb", 'rb').read()).hexdigest()
        error_k = False
        error_d = False

        if md5_cpd_kernel != md5_upd_kernel:
            logging.error("write_kernel: failed kernel write, corrupted image present")
            error_k = True
        if md5_cpd_dtb != md5_upd_dtb:
            logging.error("write_kernel: failed dtb write, corrupted device tree present")
            error_d = True

        if error_k or error_d:
            logging.error("write_kernel: WRITE PROCEDURE FAILED")
            return 9
        else:
            umount_cmd = "sudo umount /mnt"
            out, retcode = exec_cmd(umount_cmd, verbose=True)
            logging.info("write_kernel: WRITE PROCEDURE SUCCESSFULLY COMPLETE")
            return 0

    def update_cpld(self,cpld_fw):
        print("Using CPLD bitfile {}".format(cpld_fw))
        starttime = time.time()
        cpld_FW_start_add=0x10000
        ec = self.CpldMng.spiflash.firmwareProgram(0,cpld_fw,cpld_FW_start_add,erase_size=0x70000)
        endtime = time.time()
        delta = endtime - starttime
        if ec==0:
            print("Bitstream write complete")
            print("elapsed time " + str(delta) + "s")
            return 0
        else:
            print("Error detected while bitsream writing in flash")
            return 1
    
    def update_mcu(self,mcu_fw,verbose=False):
        logging.info("Using MCU bitfile {}".format(mcu_fw))
        memblock, bitstreamSize, size = loadBitstream(mcu_fw, PAGE_SIZE)
        # Read bitfile and cast as a list of unsigned integers
        formatted_bitstream = list(struct.unpack_from('I' * (len(memblock) // 4), memblock))
        cmd = ""
        page = 0
        dataw = []
        print ("Start Samba Monitor")
        self.CpldMng.mcuuart.start_mcu_sam_ba_monitor()
        print("Start FW loading in Flash")
        start = time.time()
        pre = start
        # ERASE sector cmd
        cmd_erase = [flash_cmd.ERASESECT0, flash_cmd.ERASESECT1, flash_cmd.ERASESECTL]
        dataw = []
        rxdata = []
        for w in range(0, 3):
            cmd = cmd_erase[w]
            print("erase cmd %s" % cmd)
            for i in range(0, len(cmd)):
                dataw.append(ord(cmd[i]))
            state = self.CpldMng.mcuuart.uart_send_buffer(dataw)
            time.sleep(0.7)

        print("Start time %.6f" %start)
        bw=0
        if verbose:
            pb = ProgressBar(total=100,prefix='', suffix='', decimals=1, length=50, fill='#', zfill='-')
        for i in range(len(formatted_bitstream)):
            if verbose:
                pb.print_progress_bar(i*100/len(formatted_bitstream))
            data = formatted_bitstream[i] & 0xFFFFFFFF
            cmd = "W" + hex(0x400000 + i * 4)[2:] + "," + hex(data)[2:len(hex(data))] + "#"
            dataw = []
            for k in range(0, len(cmd)):
                dataw.append(ord(cmd[k]))
            state = self.CpldMng.mcuuart.uart_send_buffer(dataw)
            if state != 0:
                print("ERROR: TIMEOUT Occurred during write")
                return 1
            bw = bw + 4
            # if i != 0 and i % 127 == 0:
            if bw == 512:
                wp_data = flash_cmd.WRITEPAGE_ARG | (page << 8)
                wp_cmd = flash_cmd.WRITEPAGEERASE_CMD + "," + hex(wp_data)[2:len(hex(wp_data))] + "#"
                print ("wp_command: %s" % wp_cmd)
                print ("Write page %d of %d" % (page,len(formatted_bitstream)))
                now = time.time()
                print ("Elapsed time for page write %.6f" % (now - pre))
                pre = now
                page = page + 1
                dataw = []
                for k in range(0, len(wp_cmd)):
                    dataw.append(ord(wp_cmd[k]))
                state = self.CpldMng.mcuuart.uart_send_buffer(dataw)
                if state != 0:
                    print("ERROR: TIMEOUT Occurred during write")
                    return 1
                time.sleep(0.5)
                bw = 0
        end = time.time()
        print ("Elapsed time %.6f" %(end-start))
        # set GPNVM
        print("Setting MCU to start from Flash")
        cmd = flash_cmd.SETGPNVM
        dataw = []
        rxdata = []
        for i in range(0, len(cmd)):
            dataw.append(ord(cmd[i]))
        state = self.CpldMng.mcuuart.uart_send_buffer(dataw)
        if state != 0:
            print("ERROR: TIMEOUT Occurred during write")
            return 1
        time.sleep(0.5)
        # reset MCU
        print("resetting MCU...")
        self.CpldMng.mcuuart.reset_mcu()
        return 0

    def update_kernel(self, zImage_path, dtb_path, dest_device="uSD"):
        """
        method used to update the CPU kernel
        :param zImage_path: path of the zImage file to be used for the update
        :param dtb_path: path of the device-tree file to be used for the update
        :param dest_device: memory where the update must be executed, accepted value are: uSD or EMMC
        :return status of the operation, 0 PASSED, !=0 FAILED
        """
        dev = ""
        if dest_device == "uSD":
            dev = "/dev/mmcblk1p1"
        elif dest_device == "EMMC0":
            dev = "/dev/mmcblk0p1"
        elif dest_device == "EMMC1":
            dev = "/dev/mmcblk0p3"
        elif dest_device is None:
            cp_cmd = "mount"
            out, retcode = exec_cmd(cp_cmd, verbose=True)
            if retcode != 0:
                logging.error("write_kernel: failed to get mount")
                return 1
            else:
                outl = out.splitlines()
                for k in range(0, len(outl)):
                    if outl[k].find("/dev/mmcblk") != -1:
                        root = outl[k].split(" ")[0]
                        parsed_root = parse.parse("/dev/mmcblk{}p{}",root)
                        blk=int(parsed_root[0])
                        part=int(parsed_root[1])-1
                        dev="/dev/mmcblk%dp%d"%(blk,part)
                        break
                if dev == "":
                    logging.error("write_kernel: unable to detect valid mounted device")
                    return 2

        else:
            logging.error("write_kernel: invalid dest_device parameter, accepted uSD or EMMC")
            return 3
        logging.info("Write kernel in %s started... " % dev)

        if os.path.isfile(zImage_path) is False:
            logging.error("update_kernel: invalid zImage file path, file not found")
            logging.error(zImage_path)
            return 4
        if os.path.isfile(dtb_path) is False:
            logging.error("update_kernel: invalid dtb file path, file not found")
            logging.error(dtb_path)
            return 5

        mount_cmd = "sudo mount " + dev + " /mnt"
        out, retcode = exec_cmd(mount_cmd, verbose=True)
        if retcode != 0:
            logging.error("update_kernel: error while mounting kernel partition")
            return 6

        md5_actual_kernel = hashlib.md5(open("/mnt/zImage", 'rb').read()).hexdigest()
        md5_actual_dtb = hashlib.md5(open("/mnt/ska-management.dtb", 'rb').read()).hexdigest()
        md5_upd_kernel = hashlib.md5(open(zImage_path, 'rb').read()).hexdigest()
        md5_upd_dtb = hashlib.md5(open(dtb_path, 'rb').read()).hexdigest()
        os.mkdir("/tmp/recovery_kernel/")

        cp_cmd = "sudo cp /mnt/zImage /tmp/recovery_kernel/"
        out, retcode = exec_cmd(cp_cmd, verbose=True)
        if retcode != 0:
            logging.error("update_kernel: error while restore kernel copy")
            return 7
        cp_cmd = "sudo cp /mnt/ska-management.dtb /tmp/recovery_kernel/"
        out, retcode = exec_cmd(cp_cmd, verbose=True)
        if retcode != 0:
            logging.error("update_kernel: error while restore  device-tree copy")
            return 8

        cp_cmd = "sudo cp " + zImage_path + " /mnt/zImage"
        out, retcode = exec_cmd(cp_cmd, verbose=True)
        if retcode != 0:
            logging.error("update_kernel: error while kernel copy")
            return 9
        cp_cmd = "sudo cp " + dtb_path + " /mnt/ska-management.dtb"
        out, retcode = exec_cmd(cp_cmd, verbose=True)
        if retcode != 0:
            logging.error("update_kernel: error while device-tree copy")
            return 10

        md5_cpd_kernel = hashlib.md5(open("/mnt/zImage",'rb').read()).hexdigest()
        md5_cpd_dtb = hashlib.md5(open("/mnt/ska-management.dtb",'rb').read()).hexdigest()
        error_k = False
        error_d = False

        if md5_cpd_kernel != md5_upd_kernel:
            if md5_cpd_kernel == md5_actual_kernel:
                logging.error("update_kernel: failed kernel write, old kernel still present")
            else:
                logging.error("update_kernel: failed kernel write, corrupted image present")
            error_k = True
        if md5_cpd_dtb != md5_upd_dtb:
            if md5_cpd_dtb == md5_actual_dtb:
                logging.error("update_kernel: failed dtb write, old device tree still present")
            else:
                logging.error("update_kernel: failed dtb write, corrupted device tree present")
            error_d = True

        if error_k or error_d:
            logging.info("Error Detected in operation trying to recovery to old version")
            cp_cmd = "sudo cp /tmp/recovery_kernel/zImage /mnt/"
            out, retcode = exec_cmd(cp_cmd, verbose=True)
            if retcode != 0:
                logging.error("update_kernel: error while kernel copy")
                return 11
            cp_cmd = "sudo cp /tmp/recovery_kernel/ska-management.dtb /mnt/"
            out, retcode = exec_cmd(cp_cmd, verbose=True)
            if retcode != 0:
                logging.error("update_kernel: error while device-tree copy")
                return 12

            md5_cpd_kernel = hashlib.md5(open("/mnt/zImage", 'rb').read()).hexdigest()
            md5_cpd_dtb = hashlib.md5(open("/mnt/ska-management.dtb", 'rb').read()).hexdigest()
            error_rk = False
            error_rd = False
            if md5_cpd_kernel != md5_actual_kernel:
                logging.error("update_kernel: failed kernel restore")
                error_rk = True
            if md5_cpd_dtb != md5_upd_dtb:
                logging.error("update_kernel: failed dtb restore")
                error_rd = True

        if error_k or error_d:
            logging.error("update_kernel: UPDATE PROCEDURE FAILED")
            return 13
        else:
            umount_cmd = "sudo umount /mnt"
            out, retcode = exec_cmd(umount_cmd, verbose=True)
            umount_cmd = "rm -rf /tmp/recovery_kernel"
            out, retcode = exec_cmd(umount_cmd, verbose=True)
            logging.info("update_kernel: UPDATE PROCEDURE SUCCESSFULLY COMPLETE")
            return 0

    # Uart CPLD2MCU

    # uart2mcu_write
    # This method implements write operation form CPLD to MCU uart
    # @param[in] data_w: data to be write on MCU
    # return op_status: status of operation, 0 operation succesfull, 1 failed, timeout occour
    def uart2mcu_write(self, data_w):
        self.write("CpldUart.TxData", data_w)
        self.write("CpldUart.Rnw", 0)
        op_status = 0
        start = time.time()
        while (1):
            if self.read("CpldUart.Status") & 0x1 == 0:
                if self.read("CpldUart.Status") & 0x2 == 0x2:
                    self.write("CpldUart.Rnw", 1)
                    self.mcuuart.rxbuff.append(self.read("CpldUart.RxData"))
                    self.mcuuart.rxusedflag = False
                break
            else:
                now = time.time()
                # print("[uart2mcu_write] time now %d" %now)
                if (now - start > 10):
                    op_status = 1
                    break
        return op_status, self.mcuuart.rxbuff

    def uart2mcu_write_then_read(self, data_w, lenr=None):
        op_status = 0
        start = time.time()
        rxbuff = []
        logger.debug("[uart2mcu_write] time start %.6f" % start)
        for i in range(0, len(data_w)):
            self.write("CpldUart.TxData", data_w[i])
            self.write("CpldUart.Rnw", 0)
            now = time.time()
            logger.debug("[uart2mcu_write] time now %.6f" % now)
            # if i<len(data_w)-1:
            """
            while (1):
                if self.read("CpldUart.Status") & 0x1 == 0:
                    now_while = time.time()
                    print("[uart2mcu_write] time now_while %.6f" %now_while)
                    break
                else:
                    now = time.time()
                    # print("[uart2mcu_write] time now %d" %now)
                    if (now - start > 1):
                        op_status = 1
                        return op_status,rxbuff
            """
            # else:
            #    while (1):
            #        if self.read("CpldUart.Status")&0x2==0x2:
            #            self.write("CpldUart.Rnw", 1)
            #            rxbuff.append(self.read("CpldUart.RxData"))
            #        else:
            #            now= time.time()
            #            #print("[uart2mcu_write] time now %d" %now)
            #            if (now-start>1):
            #                #op_status=1
            #                break
        return op_status, rxbuff

    # uart2mcu_write
    # This method implements write operation form CPLD to MCU uart
    # @param[in] data_w: data to be write on MCU
    # return op_status: status of operation, 0 operation succesfull, 1 failed, timeout occour
    def uart2mcu_write_single(self, data_w):
        self.write("CpldUart.TxData", data_w)
        self.write("CpldUart.Rnw", 0)
        op_status = 0
        start = time.time()
        while (1):
            if self.read("CpldUart.Status") & 0x1 == 0:
                # if self.read("CpldUart.Status")&0x2==0x2:
                #     self.write("CpldUart.Rnw", 1)
                #     self.mcuuart.rxbuff.append(self.read("CpldUart.RxData"))
                #     self.mcuuart.rxusedflag=False
                break
            else:
                now = time.time()
                # print("[uart2mcu_write] time now %d" %now)
                if (now - start > 10):
                    op_status = 1
                    break
        return op_status

    # uart2mcu_write
    # This method implements write operation form CPLD to MCU uart
    # return rxdata: read data from MCU uart
    # return op_status: status of operation, 0 operation succesfull, 1 failed, timeout occour
    def uart2mcu_read(self):
        op_status = 0
        start = time.time()
        rxdata = 0
        # self.mcuuart.rxbuff
        # self.mcuuart.rxusedflag=True
        # self.mcuuart.rxbuff=[]

        while (1):
            if (self.read("CpldUart.Status") & 0x2) == 0x2:
                self.write("CpldUart.Rnw", 0x1)
                rxdata = self.read("CpldUart.RxData")
                logger.debug("uart2mcu_read")
                break
            else:
                now = time.time()
                if now - start > 30:
                    logger.debug("[uart2mcu_read] time now %d" % now)
                    op_status = 1
                    break
        logger.debug("Exit from uart2mcu_read")
        return rxdata, op_status

    # uart2mcu_read_buff
    # This method implements write operation form CPLD to MCU uart
    # return rxdata: read data from MCU uart
    # return op_status: status of operation, 0 operation succesfull, 1 failed, timeout occour
    def uart2mcu_read_buff(self):
        op_status = 0
        start = time.time()
        rxdata = self.mcuuart.rxbuff
        self.mcuuart.rxusedflag = True
        self.mcuuart.rxbuff = []
        while (1):
            if (self.read("CpldUart.Status") & 0x2) == 0x2:
                self.write("CpldUart.Rnw", 0x1)
                rxdata.append(self.read("CpldUart.RxData"))
                break
            else:
                now = time.time()
                if now - start > 10:
                    # print("[uart2mcu_read] time now %d" % now)
                    op_status = 1
                    break
        return rxdata, op_status

    def uart2mcu_havedata(self):
        if (self.read("CpldUart.Status") & 0x2) == 0x2:
            return True
        else:
            return False

    # start_mcu_sam_ba_monitor
    # This method request to MCU to set uart
    # return rxdata: read data from MCU uart
    # return op_status: status of operation, 0 operation succesfull, 1 failed, timeout occour
    def start_mcu_sam_ba_monitor(self):
        # logger.debug("Start MCU Monitor")
        op_status = 0
        self.write("MCUR.GPReg0", 0xb007)
        start = time.time()
        time.sleep(0.2)
        while (1):
            if self.read("MCUR.GPReg0") == 0x5e7:
                # logger.debug("MCU Ready for Reset")
                self.write("CtrlRegs.McuReset", 0)
                time.sleep(0.01)
                self.write("CtrlRegs.McuReset", 1)
                time.sleep(0.1)
                break
            else:
                now = time.time()
                if now - start > 20:
                    op_status = 1
                    break
        return op_status

    def close(self):
        self.__del__()
