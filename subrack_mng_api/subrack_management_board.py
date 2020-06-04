__author__ = 'Cristian Albanese'
import string
from subprocess import Popen, PIPE
import sys
import os
import time
from datetime import datetime
from subrack_mng_api.management import *
from subrack_mng_api.backplane import *
import logging
from pyaavs.tile import Tile


TPMInfo_t={
"ip_address":       "",
"netmask":          "",
"gateway":          "",
"SN":               "",
"PN":               "",
"BOARD_MODE":       "",# 0 ada, 0xff no-ada
"HARDWARE_REV":     "",# v00.00.00
"SITE_LOCATION":    "",
"CABINET_LOCATION": "",
"SUBRACK_LOCATION": "",
"SLOT_LOCATION":    "",
"MAC":              "",#READ-ONLY
}


class SubrackInvalidParameter(Exception):
    """ Define an exception which occurs when an invalid parameter is provided
    to a function or class method """
    pass

class SubrackInvalidCmd(Exception):
    """ Define an exception which occurs when an invalid command is provided
    to a function or class method """
    pass

class SubrackExecFault(Exception):
    """ Define an exception which occurs when an error occur when
    a function or class method  fails"""
    pass


class SubrackOperationalStates:
    INIT=0
    STANDBY=1,
    DISABLE=2,
    ON=3,
    ALARM=4,
    FAULT=5,
    OFF=6
class SubrackAdminModes:
    ONLINE=0,
    MAINTEINANCE=1,
    OFFLINE=2,
    NOT_FITTED=3


class SubrackHealtState: #to be clarify
    OK=0,
    DEGRADED =1,
    FAILED=2

subrack_slot_config_file="/etc/SKA/subrack_slot.conf"

def detect_ip(tpm_slot_id):
    try:
        f = open(subrack_slot_config_file, "r")
    except:
        print("Configuration File not Found")
        return 1
    cfg_lines = f.readlines()
    f.close()
    subrack_cpu_ip = cfg_lines[0].split(":")[1]
    subrack_cpld_ip = cfg_lines[1].split(":")[1]
    subrack_tpm_first_ip = cfg_lines[2].split(":")[1]
    subrack_netmask = cfg_lines[4].split(":")[1]
    tpm_ip_part = []
    for i in range(0, 3):
        tpm_ip_part.append(subrack_tpm_first_ip.split(".")[i])
    tpm_last_part = subrack_tpm_first_ip.split(".")[3]
    tpm_new_last = str(int(tpm_last_part) + tpm_slot_id-1)
    tpm_board_ip=tpm_ip_part[0]+"."+tpm_ip_part[1]+"."+tpm_ip_part[2]+"."+tpm_new_last
    return tpm_board_ip,subrack_cpu_ip




###Subrack Management Board Class
#This class implements methods to manage and to monitor the subrack management board
class SubrackMngBoard:
    def __init__(self,**kwargs):
        self._simulation=kwargs.get("simulation")
        self.data = []
        self.Mng = Management(self._simulation)
        self.Bkpln = Backplane(self.Mng,self._simulation)
        self.mode = 0
        self.status = 0
        self.first_config = False

    def __del__(self):
        self.data = []


    ###GetTPMInfo
    #@brief method to get info about TPM board present on subrack
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    #@return TPM_INFO
    def GetTPMInfo(self,tpm_slot_id):
        prev_onoff = 0
        if self.GetTPMPresent()&(1<<(tpm_slot_id-1))!=0:
            if self.Bkpln.is_tpm_on(tpm_slot_id)==False:
                if self.Bkpln.pwr_on_tpm(tpm_slot_id)!=0:
                    raise SubrackExecFault("Error:TPM Power on Failed")
            else:
                prev_onoff=1
        else:
            raise SubrackInvalidCmd("TPM not present")
        tpm_ip,subrack_cpu_ip=detect_ip(tpm_slot_id)
        logging.info("TPM IP: %s, CPU IP: %s" %(tpm_ip,subrack_cpu_ip))
        tile = Tile(ip=tpm_ip, lmc_ip=subrack_cpu_ip)
        tile.connect()
        tpm_info=tile.get_board_info()
        if prev_onoff==0:
            if self.Bkpln.pwr_off_tpm(tpm_slot_id)!=0:
                raise SubrackExecFault("Error:TPM Power on Failed")
        logging.info(tpm_info)
        return tpm_info


    ###GetTPMTemperature
    #@brief method to get temperature of onboard TPM selected board present on subrack
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    #@return tpm_temperature
    def GetTPMTemperature(self,tpm_slot_id,forceread=False):
        prev_onoff = 0
        if self.GetTPMPresent()&(1<<(tpm_slot_id-1))!=0:
            if forceread==True:
                    if self.GetTPMOnOffVect()&(1<<(tpm_slot_id-1))!=0:
                            #self.Bkpln.is_tpm_on(tpm_slot_id)==False:
                        if self.Bkpln.pwr_on_tpm(tpm_slot_id)!=0:
                            raise SubrackExecFault("Error:TPM Power on Failed")
                        else:
                            prev_onoff=1
                    else:
                        return 0
                        #raise SubrackInvalidCmd("TPM not present")
            else:
                #raise SubrackExecFault("TPM was Powered OFF and read isn't forced")
                return 0
        tpm_ip,subrack_cpu_ip=detect_ip(tpm_slot_id)
        logging.info("TPM IP: %s, CPU IP: %s" %(tpm_ip,subrack_cpu_ip))
        tile = Tile(ip=tpm_ip, lmc_ip=subrack_cpu_ip)
        tile.connect()
        tile["board.regfile.enable.adc"]=1
        tpm_temp=tile.tpm_monitor.get_temperature()
        if prev_onoff==0:
            if self.Bkpln.pwr_off_tpm(tpm_slot_id)!=0:
                raise SubrackExecFault("Error:TPM Power on Failed")
        logging.info(tpm_temp)
        return tpm_temp


    ###GetTPMMCUTemperature
    #@brief method to get temperature of onboard TPM selected board present on subrack
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    #@return tpm_sn
    #@return tpm_hw_rev
    #@return tpm_bios
    def GetTPMMCUTemperature(self,tpm_slot_id,forceread=False):
        prev_onoff = 0
        if self.GetTPMPresent()&(1<<(tpm_slot_id-1))!=0:
            if forceread==True:
                if self.GetTPMOnOffVect()&(1<<(tpm_slot_id-1))!=0:
                        #self.Bkpln.is_tpm_on(tpm_slot_id)==False:
                    if self.Bkpln.pwr_on_tpm(tpm_slot_id)!=0:
                        raise SubrackExecFault("Error:TPM Power on Failed")
                    else:
                        prev_onoff=1
                else:
                    raise SubrackInvalidCmd("TPM not present")
            else:
                raise SubrackExecFault("TPM was Powered OFF and read isn't forced")
        tpm_ip,subrack_cpu_ip=detect_ip(tpm_slot_id)
        logging.info("TPM IP: %s, CPU IP: %s" %(tpm_ip,subrack_cpu_ip))
        tile = Tile(ip=tpm_ip, lmc_ip=subrack_cpu_ip)
        tile.connect()
        tile["board.regfile.enable.adc"]=1
        tpm_mcu_temp=tile.tpm_monitor.get_mcu_temperature()
        if prev_onoff==0:
            if self.Bkpln.pwr_off_tpm(tpm_slot_id)!=0:
                raise SubrackExecFault("Error:TPM Power on Failed")
        logging.info(tpm_mcu_temp)
        return tpm_mcu_temp




    ###GetTPMInfo
    #@brief method Initizlize the Subrack after installation: create board  configuration table
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    #@return vector of tpm positional, 1 TPM detected, 0 no TPM inserted, bit 7:0, bit 0 slot 1, bit 7 slot 8
    def SubrackInitialConfiguration(self):
        self.mode = "INIT"
        print("TO BE DEFINED")

    ###GetTPMPresent
    #@brief method to get info about TPM board present on subrack
    #@return TpmDetected: vector of tpm positional, 1 TPM detected, 0 no TPM inserted, bit 7:0, bit 0 slot 1, bit 7 slot 8
    def GetTPMPresent(self):
        TpmDetected=self.Mng.get_housekeeping_flag("TPMsPresent")
        return TpmDetected

    ###GetTPmOnOffGetTpmOnOffVect
    #@brief method to get Power On status of inserted tpm, 0 off or not present, 1 power on
    #@return vector of poweron status for slots, bits 7:0, bit 0 slot 1, bit 7 slot 8, 1 TPM power on, 0 no TPM inserted or power off
    def GetTPMOnOffVect(self):
        onoffvect=0
        reg=self.Mng.read("Fram.TPM_SUPPLY_STATUS")
        tpmison_vect=reg&0xff
        return tpmison_vect

    def GetTPMSupplyFault(self):
        reg=self.Mng.read("Fram.TPM_SUPPLY_STATUS")
        tpmsupplyfault=(reg&0xff00)>>8
        return tpmsupplyfault

    #GetTPMPowerLoad
    #@brief method to get power consuptin of selected tpm (providing subrack index slot of tpm)
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    def GetTPMPower(self,tpm_slot_id,force=True):
        if self.GetTPMPresent()&(1<<(tpm_slot_id-1))!=0 or force:
            pwr=self.Bkpln.get_power_tpm(tpm_slot_id)
            return pwr
        else:
            raise SubrackInvalidCmd("Impossible to get Power Value, TPM is not present")

    #GetTPMCurrent
    #@brief method to get current consuptin of selected tpm (providing subrack index slot of tpm)
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    def GetTPMCurrent(self,tpm_slot_id,force=True):
        if self.GetTPMPresent()&(1<<(tpm_slot_id-1))!=0  or force:
            pwr=self.Bkpln.get_power_tpm(tpm_slot_id)
            volt=self.Bkpln.get_voltage_tpm(tpm_slot_id)
            if volt==0:
                volt = self.Bkpln.get_voltage_tpm(tpm_slot_id)
                curr=0
            else:
                curr=float(pwr/volt)
            curr=round(curr,3)
            return curr
        else:
            raise SubrackInvalidCmd("Impossible to get Power Value, TPM is not present")

    #GetTPMVoltage
    #@brief method to get power consuptin of selected tpm (providing subrack index slot of tpm)
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    def GetTPMVoltage(self,tpm_slot_id,force=True):
        if self.GetTPMPresent()&(1<<(tpm_slot_id-1))!=0 or force:
            volt=self.Bkpln.get_voltage_tpm(tpm_slot_id)
            return volt
        else:
            raise SubrackInvalidCmd("Impossible to get Voltage Value, TPM is not present")

    #GetSubrackTemperatures
    #@brief method to get temperatures from sensors placed on backplane and subrack-management boards
    #return temp_mng1 temperature value of management sensor 1
    #return temp_mng2 temperature value of management sensor 2
    #return temp_bck1 temperature value of backplane sensor 1
    #return temp_bck2 temperature value of backplane sensor 2
    def GetSubrackTemperatures(self):
        temp_mng1 = self.Mng.GetMngTemp(1)
        temp_mng2 = self.Mng.GetMngTemp(2)
        temp_bck1,stat1 = self.Bkpln.get_sens_temp(1)
        temp_bck2,stat2 = self.Bkpln.get_sens_temp(2)
        return temp_mng1,temp_mng2,temp_bck1,temp_bck2

    #PowerOn TPM
    #@brief method to power on selected tpm
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    def PowerOnTPM(self,tpm_slot_id,force=False):
        if self.GetTPMPresent()&(1<<(tpm_slot_id-1))==0 and not force:
            logging.error("ERROR: TPM not present in selected slot")
            raise SubrackExecFault("ERROR: TPM not present in selected slot")
        else:
            if self.Bkpln.pwr_on_tpm(tpm_slot_id):
                logging.error("Power TPM on slot %d failed" %tpm_slot_id)
                raise SubrackExecFault("ERROR: power on TPM command failed")


    #PowerOff TPM
    #@brief method to power off selected tpm
    #@param[in]: subrack slot index for selected TPM, accepted value 1-8
    def PowerOffTPM(self,tpm_slot_id,force=False):
        if self.GetTPMPresent()&(1<<(tpm_slot_id-1))==0 and not force:
            logging.error("ERROR: TPM not present in selected slot")
            raise SubrackExecFault("ERROR: TPM not present in selected slot")
        else:
            if self.Bkpln.pwr_off_tpm(tpm_slot_id):
                logging.error("Power TPM off slot %d failed" %tpm_slot_id)
                raise SubrackExecFault("ERROR: power off TPM command failed")


    def SetFanSpeed(self,fan_id,speed_pwm_perc):
        status=self.Bkpln.set_bkpln_fan_speed(fan_id,speed_pwm_perc)
        if status==1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        elif status==2:
            raise SubrackExecFault("ERROR: Command Failed FanMode must be Manual!!")
        elif status>0:
            raise SubrackExecFault("ERROR: Command Failed unexpected status")


    def GetFanSpeed(self,fan_id):
        rpm,pwm_perc,status = self.Bkpln.get_bkpln_fan_speed(fan_id)
        #print ("rpm %d, pwm_perc %d" %(rpm,pwm_perc))
        if status == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        return rpm, pwm_perc

    def SetFanMode(self,fan_id_blk,auto_mode):
        if self.Bkpln.set_bkpln_fan_mode(fan_id_blk,auto_mode)==1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")

    def GetFanMode(self,fan_id):
        auto_mode,status = self.Bkpln.get_bkpln_fan_mode(fan_id)
        #print("auto_mode %d, status %d" % (auto_mode, status))
        if status == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        return auto_mode

    def PllInitialize(self):
        if self._simulation==False:
            cmd = "bash ./pll_cfg.sh"
            res=run(cmd)
            lines=res.splitlines()
            r=lines[len(lines)-1]
            print("pll res = %s" %r)
            if r!="0x33":
                print ("ERROR: PLL configuration failed, PLL not locked")
            #raise SubrackExecFault("ERROR: PLL configuration failed, PLL not locked")
        else:
            r = "0x33"
            print("pll res = %s" % r)
            if r != "0x33":
                print ("ERROR: PLL configuration failed, PLL not locked")


    def GetPSVout(self,ps_id):
        if ps_id>2 or ps_id<0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        vout=self.Bkpln.get_ps_vout(ps_id)
        return vout

    def GetPSIout(self,ps_id):
        if ps_id>2 or ps_id<0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        vout=self.Bkpln.get_ps_iout(ps_id)
        return vout

    def GetPSPower(self,ps_id):
        if ps_id>2 or ps_id<0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        vout=self.Bkpln.get_ps_power(ps_id)
        return vout

    def GetPSFanSpeed(self,ps_id):
        if ps_id>2 or ps_id<0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        fanspeed,status = self.Bkpln.get_ps_fanspeed(ps_id)
        if status!=0:
            raise SubrackExecFault("ERROR: Get PS Fan speed operation failed")
        else:
            return fanspeed

    def SetPSFanSpeed(self,ps_id,speed_percent):
        if ps_id>2 or ps_id<0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        status = self.Bkpln.set_ps_fanspeed(ps_id,speed_percent)
        if status!=0:
            raise SubrackExecFault("ERROR: Set PS Fan speed operation failed")




    def close(self):
        self.__del__()
