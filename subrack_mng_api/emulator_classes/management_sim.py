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
from subrack_mng_api.emulator_classes.def4emulation import *


### Management Class
#This class contain methods to permit access to all registers connected to the
#management CPU (iMX6) mapped in filesystem
class Management_sim():
    def __init__(self):
        self.data = []

    def __del__(self):
        self.data = []

    def GetMngTemp(self,sens_id):
        if sens_id <1 or sens_id >2:
            print("Error Invalid ID")
            return 0
        temperature=self.read("Fram.Adt"+str(sens_id)+"TempValue")
        if (temperature & 0x1000)>>12==1:
            temp = float((temperature&0xfff - 4096)) / 16
        else:
            temp = float((temperature & 0xfff) )/16
        temp=round(temp,2)
        return temp
#        temperature=random.triangular(MAX_TEMP_RANGE_SIM_VALUE,MAX_TEMP_RANGE_SIM_VALUE)
#        return temperature

    ###get_fpga_fw_version
    #This method return the FPGA Fw version, version buid year and build date
    #return version: version of FW
    #return builddate: date and hour of FW build
    #return buildyear: year of FW build
    def get_fpga_fw_version(self):
        version=self.read("FPGA_FW.FirmwareVersion")
        builddate=self.read("FPGA_FW.FirmwareBuildLow")
        buildyear=self.read("FPGA_FW.FirmwareBuildHigh")
        print("Current FPGA FW version: " + hex(version&0xffffffff)[2:])
        print("Build Date: " + hex(buildyear)[2:] + "-" + hex(builddate)[2:])
        return hex(version), hex(buildyear), hex(builddate)


    ###read
    #This method implements read
    #operation of selected register
    #@param[in] name name of register it must have following format <category_name>.<register_name>
    #return read register value
    def read(self, name):
        reg_category=name.split(".")[0]
        reg_name=name.split(".")[1]
        el= [element for element in simulation_regs if (element.get("cat","")==reg_category and element.get("name","")==reg_name)]
        if el[0].get("mode")=="RO":
            if el[0].get("state") == 0:
                val = el[0].get("def")
                el[0]["state"]=1
            else:
                val = el[0].get("value")
            #print("Read: " + name + ", " + hex(val))
            return int(val)
        else:
            val=rw_emulator_regs_file("r",reg_category,reg_name)
            return int(val)

    ###write
    #This method implements write
    #operation of selected register
    #@param[in] name: name of register it must have following format <category_name>.<register_name>
    #@param[in] value: value will be write in selected register
    def write(self, name, value):
        reg_category=name.split(".")[0]
        reg_name=name.split(".")[1]
        el= [element for element in simulation_regs if (element.get("cat","")==reg_category and element.get("name","")==reg_name)]
        if el[0].get("mode") == "RO":
            if el[0].get("state") == 0:
                el[0]["state"]=1
            el[0]["value"]=value
        else:
            rw_emulator_regs_file("w",reg_category,reg_name,value)

    def get_housekeeping_flag(self, name):
        flag_value = self.read("HKeep."+name)
        return flag_value


    def fpgai2c_write8(self,ICadd, reg_add,datatx,i2cbus_id ):
        #print datatx
        el=[element for element in simulation_i2c_regs if (element.get("devadd","")==ICadd and element.get("offset","")==reg_add and element.get("bus","")==i2cbus_id)]
        if el[0].get("mode")=="RO":
            el[0]["value"]=datatx
            return 0
        else:
            if i2cbus_id==0:
                i2cbus="i2c1"
            elif i2cbus_id==1:
                i2cbus = "i2c2"
            elif i2cbus_id == 2:
                i2cbus = "i2c3"
            rw_emulator_i2c_file("w", i2cbus, hex(ICadd),hex(reg_add), datatx)
            return 0



    def fpgai2c_read8(self,ICadd, reg_add,i2cbus_id ):
        #el=[element for element in simulation_i2c_regs if (element.get("devadd","")==ICadd and element.get("offset","")==reg_add and element.get("i2cbus","")==i2cbus_id)]
        el = [element for element in simulation_i2c_regs if (element.get("devadd", "") == ICadd and element.get("offset", "") == reg_add and element.get("bus","") == i2cbus_id)]
        if el[0].get("mode")=="RO":
            if len(el)!=0:
                return el[0].get("value")&0xff,0
            else:
                return 0,-1
        else:
            if i2cbus_id==0:
                i2cbus="i2c1"
            elif i2cbus_id==1:
                i2cbus = "i2c2"
            elif i2cbus_id == 2:
                i2cbus = "i2c3"
            val=rw_emulator_i2c_file("r", i2cbus, hex(ICadd),hex(reg_add))
            return val,0

        #el=[element for element in simulation_i2c_regs if (element.get("devadd", "") == ICadd and element.get("offset", "") == reg_add and element.get("bus","") == i2cbus_id)]

    def fpgai2c_write16(self,ICadd, reg_add,datatx,i2cbus_id ):
        el=[element for element in simulation_i2c_regs if (element.get("devadd","")==ICadd and element.get("offset","")==reg_add and element.get("bus","")==i2cbus_id)]
        if el[0].get("mode")=="RO":
            el[0]["value"]=datatx&0xffff
            return 0
        else:
            if i2cbus_id == 0:
                i2cbus = "i2c1"
            elif i2cbus_id == 1:
                i2cbus = "i2c2"
            elif i2cbus_id == 2:
                i2cbus = "i2c3"
            rw_emulator_i2c_file("w", i2cbus, hex(ICadd), hex(reg_add), datatx&0xffff)
            return 0

    def fpgai2c_read16(self,ICadd, reg_add,i2cbus_id ):
        el=[element for element in simulation_i2c_regs if (element.get("devadd","")==ICadd and element.get("offset","")==reg_add and element.get("bus","")==i2cbus_id)]
        if el[0].get("mode") == "RO":
            if len(el)!=0:
                return el[0].get("value")&0xffff,0
            else:
                return 0,-1
        if i2cbus_id == 0:
            i2cbus = "i2c1"
        elif i2cbus_id == 1:
            i2cbus = "i2c2"
        elif i2cbus_id == 2:
            i2cbus = "i2c3"
        val = rw_emulator_i2c_file("r", i2cbus, hex(ICadd), hex(reg_add))
        return val&0xffff, 0


    def close(self):
        self.__del__()
