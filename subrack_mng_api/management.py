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

lasttemp = 59.875

I2CDevices = ["ADT7408_1", "ADT7408_2", "EEPROM_MAC_1", "EEPROM_MAC_2", "LTC3676", "LTC4281"]


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


TPM_PRESENT_MASK = [0x1, 0x2, 0x4, 0x8, 0x80, 0x40, 0x20, 0x10]

print_debug = False
categories = ["FPGA_FW", "UserReg", "MCUR", "Led", "HKeep", "ETH", "Fram", "FPGA_I2C", "ONEWIRE", "CtrlRegs",
              "CpldUart"]

FpgaI2C_p = "/sys/bus/platform/devices/8010000.skamngfpgai2c/parameters/"  # file system path to FPGA I2C Regs
FpgaI2CReg_names = [
    "twi_command",
    "twi_rbyte",
    "twi_wrbyte",
    "twi_status",
    "twi_irq",
    "twi_irq_en",
    "twi_wrdata",
    "twi_rdata"
]

# FirmwareBuildHigh  FirmwareBuildLow   FirmwareVersion
FpgaFwVersion_p = "/sys/bus/platform/devices/8000000.skamngfpga/parameters/"  # file system path to FPGA FW Version Regs

UserReg_p = "/sys/bus/platform/devices/8000a00.skamnguserreg/parameters/"  # file system path to FPGA User Regs
UserReg_names = [
    "UserReg0",
    "UserReg1",
    "UserReg2",
    "UserReg3"
]

CtrlRegs_p = "/sys/bus/platform/devices/8000900.skamngctrlregs/parameters/"  # file system path to CTRL Regs
CtrlRegs_names = [
    "McuReset",
    "McuPollingTime",
    "EIMHadd",
    "BkplOnOff"
]

MCURegs_p = "/sys/bus/platform/devices/8030000.skamngmcuregs/parameters/"  # file system path to MCU Regs Mirrored in FPGA
MCUReg_names = [
    "McuFWBuildVersion",
    "McuFWBuildTime",
    "McuFWBuildDate",
    "GPReg0",
    "GPReg1",
    "GPReg2",
    "GPReg3",
    "VoltageSOC",
    "VoltageARM",
    "VoltageDDR",
    "Voltage2V5",
    "Voltage1V0",
    "Voltage1V1",
    "VoltageVCORE",
    "Voltage1V5",
    "Voltage3V3",
    "Voltage5V",
    "Voltage3V",
    "Voltage2V8",
    "BuckRegTemp",
    "MCUTemp"
]

UserLed_p = "/sys/bus/platform/devices/8000400.skamngled/parameters/"  # file system path to FPGA User Led Control Regs
UserLedReg_names = [
    "Led_Tpm_A",
    "Led_Tpm_K",
    "Led_User_A",
    "Led_User_K"
]

HKeepRegs_p = "/sys/bus/platform/devices/8000500.skamnghkregs/parameters/"  # file system path to FPGA House Keeping Regs
HKeep_flag_names = [
    "PsntMux",
    "TPMsPresent",
    "PPSMux",
    "HKTempReg",
    "TempAlarm2",
    "TempAlarm1",
    "HKVoltagesReg",
    "PowerGoodBuck2",
    "PowerGood1V5",
    "ResetOutputBuck1",
    "PowerGoodBuck1",
    "PowerGoodStepDown",
    "IRQBuck1",
    "HSwapCtrlPowerinAlert",
    "HKFanReg",
    "FanAAlert",
    "FanBAlert",
    "TPMAAlert",
    "TPMBAlert",
    "TPMFanAlert",
]

EthRegs_p = "/sys/bus/platform/devices/8000100.skamngethregs/parameters/"  # file system path to FPGA ETH Regs

LockRegs_p = "/sys/bus/platform/devices/80c0000.skamnglockregs/parameters/"  # file system path to FPGA LOCK Regs
LockRegs_names = [
    "MCULock",
    "UCPLock",
    "CPULock"
]

CpldUart_p = "/sys/bus/platform/devices/8070000.skamngcplduartregs/parameters/"  # file system path to CPLDUART Regs
CpldUart_names = [
    "Rnw",
    "TxData",
    "RxData",
    "Status"
]

OneWireRegs_p = "/sys/bus/platform/devices/80b0000.skamngmonewireregs/parameters/"  # file system path to ONEWIRE Regs
OneWirwRegs_names = [
    "Command1WM",
    "Data1WM",
    "Int1WM",
    "IntEn1WM",
    "Clock1WM",
    "Mux1WM"
]

FramRegs_p = "/sys/bus/platform/devices/8090000.skamngframregs/parameters/"  # fpgaram register

Error_p = "ERROR"

FpgaFwVersionReg_list = []
MCUReg_list = []
UserLedReg_list = []
HKeepRegs_list = []
EthRegs_list = []
UserReg_list = []
FramRegs_list = []
OneWire_list = []
LockRegs_list = []
CtrlRegs_list = []
CpldUart_list = []


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
    if cat == "FPGA_FW":
        categ = FpgaFwVersion_p
    elif cat == "UserReg":
        categ = UserReg_p
    elif cat == "MCUR":
        categ = MCURegs_p
    elif cat == "Led":
        categ = UserLed_p
    elif cat == "HKeep":
        categ = HKeepRegs_p
    elif cat == "ETH":
        categ = EthRegs_p
    elif cat == "Fram":
        categ = FramRegs_p
    elif cat == "FPGA_I2C":
        categ = FpgaI2C_p
    elif cat == "Lock":
        categ = LockRegs_p
    elif cat == "ONEWIRE":
        categ = OneWireRegs_p
    elif cat == "CtrlRegs":
        categ = CtrlRegs_p
    elif cat == "CpldUart":
        categ = CpldUart_p
    else:
        categ = Error_p
    if print_debug:
        print("from get_cat: name " + name)
        print("from get_cat: cat " + cat)
        print("from get_cat: category " + categ)
    return categ


def translate_reg(name):
    # cat=name[0:(string.find(name,"."))]
    cat = name[0:name.find(".")]
    if cat == "FPGA_FW":
        categ = FpgaFwVersion_p
    elif cat == "UserReg":
        categ = UserReg_p
    elif cat == "MCUR":
        categ = MCURegs_p
    elif cat == "Led":
        categ = UserLed_p
    elif cat == "HKeep":
        categ = HKeepRegs_p
    elif cat == "ETH":
        categ = EthRegs_p
    elif cat == "Fram":
        categ = FramRegs_p
    elif cat == "FPGA_I2C":
        categ = FpgaI2C_p
    elif cat == "Lock":
        categ = LockRegs_p
    elif cat == "ONEWIRE":
        categ = OneWireRegs_p
    elif cat == "CtrlRegs":
        categ = CtrlRegs_p
    elif cat == "CpldUart":
        categ = CpldUart_p
    else:
        categ = Error_p
    if print_debug:
        print("from get_cat: name " + name)
        print("from get_cat: cat " + cat)
        print("from get_cat: category " + categ)
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


CPULOCK_UNLOCK_VAL = 0xfffffff


class mcu2cplduartbuff():
    rxbuff = []
    txbuff = []
    rxusedflag = False
    txusedflag = False


### Management Class
# This class contain methods to permit access to all registers connected to the
# management CPU (iMX6) mapped in filesystem
class Management():
    def __init__(self, simulation):
        self.mcuuart = mcu2cplduartbuff()
        self.data = []
        self.simulation = simulation
        if self.simulation == False:
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

    def __del__(self):
        self.data = []

    ###create_all_regs_list
    # This method permit to fill all categories
    # register lists (<category_name>_list variable)
    def create_all_regs_list(self):
        for i in range(0, len(categories)):
            cmd = "ls -l " + get_cat(categories[i])
            regs = str(run(cmd))
            # print regs
            lines = regs.splitlines()
            for l in range(0, len(lines)):
                if lines[l].find("root") != -1:
                    if categories[i] == "FPGA_FW":
                        FpgaFwVersionReg_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "UserReg":
                        UserReg_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "MCUR":
                        MCUReg_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "Led":
                        UserLedReg_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "HKeep":
                        HKeepRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "ETH":
                        EthRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "Fram":
                        FramRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "Lock":
                        LockRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "ONEWIRE":
                        OneWire_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "CtrlRegs":
                        CtrlRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                    elif categories[i] == "CpldUart":
                        CpldUart_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])

        print("FpgaFwVersionReg_list:", FpgaFwVersionReg_list)
        print("UserReg_list:", UserReg_list)
        print("MCUReg_list:", MCUReg_list)
        print("UserLedReg_list:", UserLedReg_list)
        print("HKeepRegs_list:", HKeepRegs_list)
        print("EthRegs_list:", EthRegs_list)
        print("FramRegs_list:", FramRegs_list)
        print("LockRegs_list:", LockRegs_list)
        print("OneWireRegs_list:", OneWire_list)
        print("CtrlRegs_list:", CtrlRegs_list)
        print("CpldUart_list:", CpldUart_list)

    ###create_regs_list
    # This method permit to fill selected categories
    # register lists (<category_name>_list variable)
    # @param[in] categories: categories name
    def create_regs_list(self, categories):
        cmd = "ls -l " + get_cat(categories)
        regs = str(run(cmd))
        #print(regs)
        lines = regs.splitlines()
        print(len(lines))
        for l in range(0, len(lines)):
            #print(lines[l])
            if lines[l].find("root") != -1:
                if categories == "FPGA_FW":
                    FpgaFwVersionReg_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "UserReg":
                    UserReg_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "MCUR":
                    MCUReg_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "Led":
                    UserLedReg_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "HKeep":
                    HKeepRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "ETH":
                    EthRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "Fram":
                    FramRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "Lock":
                    LockRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "ONEWIRE":
                    OneWire_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "CtrlRegs":
                    CtrlRegs_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])
                elif categories == "CpldUart":
                    CpldUart_list.append(lines[l].split(" ")[len(lines[l].split(" ")) - 1])

        print("FpgaFwVersionReg_list:", FpgaFwVersionReg_list)
        print("UserReg_list:", UserReg_list)
        print("MCUReg_list:", MCUReg_list)
        print("UserLedReg_list:", UserLedReg_list)
        print("HKeepRegs_list:", HKeepRegs_list)
        print("EthRegs_list:", EthRegs_list)
        print("FramRegs_list:", FramRegs_list)
        print("LockRegs_list:", LockRegs_list)
        print("OneWireRegs_list:", OneWire_list)
        print("CtrlRegs_list:", CtrlRegs_list)
        print("CpldUart_list:", CpldUart_list)

    ###dump_categories
    # This method permit to print
    # all available registers categories
    def dump_categories(self):
        for i in range(0, len(categories)):
            print(categories[i])

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
                    print("Opening file")
                fo = open(reg, "r")
                value = fo.readline()
                value = value[0:len(value) - 1]
                fo.close()
            else:
                value = 0  # self.lastError = res
            if print_debug:
                print("Read: " + name + ", " + hex(value))
            return int(value)

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
                print("Write: " + name + ", " + hex(value))
            reg = translate_reg(name)
            if print_debug:
                print("register: " + reg)
            if reg != Error_p:
                if print_debug:
                    print("Opening file")
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
        builddate = self.read("FPGA_FW.FirmwareBuildLow")
        buildyear = self.read("FPGA_FW.FirmwareBuildHigh")
        print("Current FPGA FW version: " + hex(version & 0xffffffff)[2:])
        print("Build Date: " + hex(buildyear)[2:] + "-" + hex(builddate)[2:])
        return hex(version), hex(buildyear), hex(builddate)

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
        print("Actual polling time: " + str('%.2f' % (polltime)) + " ms")
        return polltime

    ### dump_housekeeping_flags_all
    # This method print all HouseKeeping registers/flags values
    def dump_housekeeping_flags_all(self):
        for i in range(0, len(HKeep_flag_names)):
            flag_value = self.read("HKeep." + HKeep_flag_names[i])
            print(HKeep_flag_names[i] + " = " + hex(flag_value & 0xffffffff))

    ### dump_fpga_userreg_all
    # This method print all FPGA User Registers  values
    def dump_fpga_userreg_all(self):
        for i in range(0, len(UserReg_names)):
            flag_value = self.read("UserReg." + UserReg_names[i])
            print(UserReg_names[i] + " = " + hex(flag_value & 0xffffffff))

    ### dump_userled_all
    # This method print all FPGA User Leds  values
    def dump_userled_all(self):
        for i in range(0, len(UserLedReg_names)):
            flag_value = self.read("Led." + UserLedReg_names[i])
            print(UserLedReg_names[i] + " = " + hex(flag_value & 0xffffffff))

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
        for i in range(0, len(MCUReg_names)):
            reg_value = self.read("MCUR." + MCUReg_names[i])
            if (i > 6 and i < 19):
                print(MCUReg_names[i] + " = " + str('%.2f' % (float(reg_value) / 1000)))
            elif (i >= 19 and i < (len(MCUReg_names) - 1)):
                print(MCUReg_names[i] + " = " + str('%.2f' % (reg_value)))
            elif (i == (len(MCUReg_names) - 1)):
                print(MCUReg_names[i] + " = " + str('%.2f' % (float(reg_value) / 10)))
            else:
                print(MCUReg_names[i] + " = " + hex(reg_value & 0xffffffff))

    ### dump_fram_regs_all
    # This method print all FPGA Ram Registers values
    def dump_fram_regs_all(self):
        self.create_regs_list("Fram")
        for i in range(0, len(FramRegs_list)):
            reg_value = self.read("Fram." + FramRegs_list[i])
            print(FramRegs_list[i] + " = " + str('%.2f' % (reg_value)))

    ###dump_onewire_regs_all
    # This method print all OneWire Registers values
    def dump_onewire_regs_all(self):
        self.create_regs_list("ONEWIRE")
        for i in range(0, len(OneWire_list)):
            reg_value = self.read("ONEWIRE." + OneWire_list[i])
            print(OneWire_list[i] + " = " + hex(reg_value & 0xff))

    # get_cpld_actual_ip
    # This method retrieve the IP Adddress assigned to CPLD on board
    # return ipadd:ipaddress string
    def get_cpld_actual_ip(self):
        ip = self.read("ETH.IP")
        print ("Read ip: %s" % hex(ip))
        ipadd = []
        ipadd.append((ip & 0xff000000) >> 24)
        ipadd.append((ip & 0x00ff0000) >> 16)
        ipadd.append((ip & 0x0000ff00) >> 8)
        ipadd.append((ip & 0x000000ff))
        ipstring = str(ipadd[0]) + "." + str(ipadd[1]) + "." + str(ipadd[2]) + "." + str(ipadd[3])
        print("ipstring %s" % ipstring)
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
            print("Device: " + vars(I2CDevAdd).keys()[i + 1] + ", add: " + hex(vars(I2CDevAdd).values()[i + 1]))

    ###read_i2c
    # This method implements read on i2c bus directly from CPU
    # @param[in] bus_id: bus index where device is connected on
    # @param[in] device_add: device address
    # @param[in] reg_offset: offset of device register
    # @param[in] size_type: type of access (b byte, w word 16b)
    # return value: read register value
    # Note: this operation require to stop the MCU I2C access during read to arbitrate access, it's make using gpio signal
    # from CPU and MCU
    def read_i2c(self, bus_id, device_add, reg_offset, size_type):
        cmd = "echo 0 > /sys/class/gpio/gpio134/value"
        run(cmd)
        time.sleep(0.02)
        while (1):
            if (self.read("MCUR.GPReg3") == 0x12c0dead):
                break
        cmd = "i2cget -y -f " + str(bus_id) + " " + hex(device_add) + " " + hex(reg_offset) + " " + size_type
        value = run(cmd)
        print(value)
        cmd = "echo 1 > /sys/class/gpio/gpio134/value"
        run(cmd)
        return value

    ###write_i2c
    # This method implements write on i2c bus directly from CPU
    # @param[in] bus_id: bus index where device is connected on
    # @param[in] device_add: device address
    # @param[in] reg_offset: offset of device register
    # @param[in] size_type: type of access (b byte, w word 16b)
    # Note: this operation require to stop the MCU I2C access during read to arbitrate access, it's make using gpio signal
    # from CPU and MCU
    def write_i2c(self, bus_id, device_add, reg_offset, size_type, data):
        cmd = "echo 0 > /sys/class/gpio/gpio134/value"
        run(cmd)
        time.sleep(0.02)
        while (1):
            if (self.read("MCUR.GPReg3") == 0x12c0dead):
                break
        cmd = "i2c_set -y -f " + str(bus_id) + " " + hex(device_add) + " " + hex(reg_offset) + " " + hex(
            data) + " " + size_type
        value = run(cmd)
        print(value)
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
                    print("len lockedpid = %d, lockedpid val %s, elapsed time %d" % (
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
                print("timeout locking cpu")
                return 0xff, -1
        # command=(rdbytenum<<24)|(wrbytenum<<16)|(i2cbus_id)|(ICadd>>1)cat /sy  bus
        # datatx_n=((datatx&0xff)<<24)|((datatx&0xff00>>8)<<24)|((datatx&0xff0000>>16)<<16)|((datatx&0xff000000>>24))
        # print "Write txdata swapped %x " %datatx
        command = (rdbytenum << 12) | (wrbytenum << 8) | (i2cbus_id << 16) | (ICadd)
        # print "Command %x" %command
        cmd = "echo 0 > /sys/class/gpio/gpio134/value"
        run(cmd)
        time.sleep(0.01)
        while (1):
            if (self.read("MCUR.GPReg3") == 0x12c0dead):
                break
        self.write("FPGA_I2C.twi_wrdata", datatx)
        if print_debug:
            print("fpgai2c_op command = " + hex(command))
        self.write("FPGA_I2C.twi_command", command)
        time.sleep(0.1)
        retry = 0
        while (retry < MAXRETRY):
            status = self.read("FPGA_I2C.twi_status")
            if (status == 0):
                break
            else:
                if status == 2 or status == 3:
                    print("Not Acknowledge detected")
                    cmd = "echo 1 > /sys/class/gpio/gpio134/value"
                    run(cmd)
                    time.sleep(0.1)
                    self.write("Lock.CPULock", CPULOCK_UNLOCK_VAL)
                    os.remove("/run/lock/mngfpgai2c.lock")
                    return 0xff, status
                elif status == 1:
                    retry = retry + 1
                    time.sleep(0.01)
        if retry == MAXRETRY:
            print("Maxretry i2c fpga access ")
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
        time.sleep(0.01)
        self.write("Lock.CPULock", CPULOCK_UNLOCK_VAL)
        os.remove("/run/lock/mngfpgai2c.lock")
        logging.debug("End I2C OP")
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

    def GetMngTemp(self, sens_id):
        if sens_id < 1 or sens_id > 2:
            print("Error Invalid ID")
            return 0
        temperature = self.read("Fram.Adt" + str(sens_id) + "TempValue")
        if (temperature & 0x1000) >> 12 == 1:
            temp = float((temperature & 0xfff - 4096)) / 16
        else:
            temp = float((temperature & 0xfff)) / 16
        temp = round(temp, 2)
        return temp

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
        print("[uart2mcu_write] time start %.6f" % start)
        for i in range(0, len(data_w)):
            self.write("CpldUart.TxData", data_w[i])
            self.write("CpldUart.Rnw", 0)
            now = time.time()
            print("[uart2mcu_write] time now %.6f" % now)
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
                print ("uart2mcu_read")
                break
            else:
                now = time.time()
                if now - start > 30:
                    print("[uart2mcu_read] time now %d" % now)
                    op_status = 1
                    break
        print ("Exit from uart2mcu_read")
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
        print ("Start MCU Monitor")
        op_status = 0
        self.write("MCUR.GPReg0", 0xb007)
        start = time.time()
        time.sleep(0.2)
        while (1):
            if self.read("MCUR.GPReg0") == 0x5e7:
                print("MCU Ready for Reset")
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

    # One Wire Section methods
    def OneWire_Set_CLK(self, clkvalue):
        print("Setting OneWire CLK... ")
        self.write("ONEWIRE.Clock1WM", clkvalue)

    def OneWire_Get_CLK(self):
        clk = self.read("ONEWIRE.Clock1WM")
        print("OneWire CLK Reg: %x " % (int(clk) & 0xf))

    def OneWire_ResetCmd(self):
        self.write("ONEWIRE.Command1WM", 0x1)
        dt = datetime.now()
        starttime = dt.microsecond
        while (1):
            dt = datetime.now()
            timenow = dt.microsecond
            if (timenow - starttime) > 10000000:
                print("Error Timeout")
                return -1
            else:
                result = self.read("ONEWIRE.Int1WM")
                if (result & 0x1) == 0x1:
                    return 0

    def OneWire_AccelerateModeCmd(self):
        self.write("ONEWIRE.Command1WM", 0x2)
        dt = datetime.now()
        starttime = dt.microsecond
        time.sleep(0.01)

    def OneWire_WriteByte(self, wr_data):
        # print "wrdata " + str(wr_data)
        self.write("ONEWIRE.Data1WM", wr_data)
        dt = datetime.now()
        starttime = dt.microsecond
        while True:
            dt = datetime.now()
            timenow = dt.microsecond
            if (timenow - starttime) > 10000000:
                print("Error Timeout")
                return -1
            else:
                result = self.read("ONEWIRE.Int1WM")
                if (result & 0xC) == 0xC:
                    return 0

    def OneWire_ReadByte(self):
        if (self.OneWire_WriteByte(0xFF)) != 0:
            print("Read Failed")
            return -1
        dt = datetime.now()
        starttime = dt.microsecond
        while True:
            dt = datetime.now()
            timenow = dt.microsecond
            if (timenow - starttime) > 10000000:
                print("Error Timeout")
                return -1
            else:
                result = self.read("ONEWIRE.Int1WM")
                if (result & 0x10) == 0x10:
                    result = self.read("ONEWIRE.Data1WM")
                    return (result & 0xff), 0

    def OneWire_ReadByte_d(self, d):
        if (self.OneWire_WriteByte(d)) != 0:
            print("Read Failed")
            return -1
        # dt = datetime.now()
        # starttime=dt.microsecond
        result = self.read("ONEWIRE.Data1WM")
        return (result & 0xff), 0

    def OneWire_SelectMux(self, mux):
        self.write("ONEWIRE.Mux1WM", mux)
        dt = datetime.now()
        starttime = dt.microsecond
        time.sleep(0.01)
        # print "mux: " + str(mux)

    def OneWire_MatchRom(self, id):
        idhex = [id[i:i + 2] for i in range(0, len(id), 2)]
        # print idhex
        self.OneWire_WriteByte(0x55)
        for i in range(0, 8):
            self.OneWire_WriteByte(int(idhex[i], 16))
            # print i
        return 0

    def OneWire_ReadScratchpad(self):
        paddata = []
        # print "Read scratch pad"
        self.OneWire_WriteByte(0xBE)
        for i in range(0, 9):
            data, status = self.OneWire_ReadByte_d(0xff)
            paddata.append(data)
        # print paddata
        return paddata

    def OneWire_StartConversion(self):
        self.OneWire_SelectMux(0x08)  # all boards
        temp = []
        self.OneWire_ResetCmd()
        self.OneWire_WriteByte(0xCC)
        # match_rom(dev_id_codes)

        self.OneWire_WriteByte(0x44)
        # time.sleep(0.5)
        # while(1):
        #     data,status=Mng.OneWire_ReadByte_d(0x0)
        #     if data!=0:
        #         break
        #     else:
        #         time.sleep(0.001)
        time.sleep(1.25)

    ###OneWire_ReadTemperature
    # This method implements a read temperature from selected onewire device on selected TPM
    # @param[in] mux: id of iTPM board where onewire devices is
    # @param[in] id: univoque id of selected onewire device
    # @param[out] temp_f: float value of temperature in Celsius degree
    def OneWire_ReadTemperature(self, mux, id):
        global lasttemp
        # Convert ID string to [hex] byte array
        idhex = id.decode("hex")
        # print "Entered"
        # Select Mux
        self.OneWire_SelectMux(mux)
        # print "Mux selected"
        # Bus reset
        self.OneWire_ResetCmd()
        # Select IC (Match ROM)
        self.OneWire_MatchRom(id)
        # print "Mux: " + str(mux) + " - id: " + str(id)
        # time.sleep(0.5)
        # print "Rom Matched"
        # Read Temp
        temp = self.OneWire_ReadScratchpad()
        # print temp
        # print "Len of sctrachpad: %d" %(len(temp))
        temp_msb = int(temp[1])  # Sign byte + lsbit
        temp_lsb = int(temp[0])  # Temp data plus lsb

        temp_tot = int((temp_msb << 8) + temp_lsb)

        # print "temptot: " + str(temp_tot)
        # time.sleep(1)

        temp_f = float(0.0)

        if (temp_tot >= 0x800):  # Negative Temp
            if (temp_tot & 0x0001):
                temp_f += 0.06250
            if (temp_tot & 0x0002):
                temp_f += 0.12500
            if (temp_tot & 0x0004):
                temp_f += 0.25000
            if (temp_tot & 0x0008):
                temp_f += 0.50000
            temp_tot = (temp_tot >> 4) & 0x00FF
            temp_tot -= 0x0001
            temp_tot = ~temp_tot
            temp_f = temp_f - float(temp_tot & 0xFF)
        else:  # Posiive Temp
            temp_f += (temp_tot >> 4) & 0x0FF
            if (temp_tot & 0x0001):
                temp_f += 0.06250
            if (temp_tot & 0x0002):
                temp_f += 0.12500
            if (temp_tot & 0x0004):
                temp_f += 0.25000
            if (temp_tot & 0x0008):
                temp_f += 0.50000

        if temp_msb <= 0x80:
            temp_lsb = temp_lsb / 2
        temp_msb = temp_msb & 0x80
        if temp_msb >= 0x80:
            temp_lsb = (~temp_lsb) + 1  # twos complement
        if temp_msb >= 0x80:
            temp_lsb = (temp_lsb / 2)  # shift to get whole degree
        if temp_msb >= 0x80:
            temp_lsb = ((-1) * temp_lsb)  # add sign bit

        # Check Bug 60
        if temp_f == 59.875:
            if temp_f > (lasttemp + 3):
                temp_f = lasttemp
            elif temp_f < (lasttemp - 3):
                temp_f = lasttemp

        lasttemp = temp_f;

        # print "Temperature read in C: %f" % temp_f
        return temp_f

    def OneWire_LoadIDs(self):
        w, h = 8, 3
        dev_table = [[0 for x in range(h)] for y in range(w)]

        w_it = 0
        h_it = 0

        # print dev_table

        filepath = 'boards-1wire-ids.txt'
        with open(filepath) as fp:
            # print "File Opened"
            line = fp.readline()
            # print "Read Line"
            while line:
                if line[0] != "#":
                    # print "Not a comment" + str(w_it) + " " + str(h_it)
                    dev_table[w_it][h_it] = line.rstrip()
                    h_it += 1
                    if h_it == 3:
                        h_it = 0
                        w_it += 1
                    if w_it == 8:
                        fp.close()
                        return dev_table
                    else:
                        line = fp.readline()
                else:
                    # print "Comment" + str(line[0])
                    # time.sleep(1)
                    line = fp.readline()

    def close(self):
        self.__del__()
