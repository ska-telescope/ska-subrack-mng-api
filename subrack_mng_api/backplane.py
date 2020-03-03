__author__ = 'Cristian Albanese'
import string
from subprocess import Popen, PIPE
import sys
import os
import time
from management import *

print_debug=False

class BackplaneInvalidParameter(Exception):
    """ Define an exception which occurs when an invalid parameter is provided
    to a function or class method """
    pass



power_supply_i2c_offset=[0x0,0x2,0x4,0x6,0x8,0xa,0xc,0xe]
#mng=MngBoard()
### Backplane Board Class
#This class contain methods to permit access to major functionality
#of backplane board from management CPU (iMX6) via registers mapped in filesystem
class Backplane():
    def __init__(self, Management_b):
        self.data = []
        self.mng = Management_b
    def __del__(self):
        self.data = []

    ######BACKPLANE TPM POWER CONTROL FUNCTIONS

    ###reset_pwr_fault_reg
    #This method reset the Bacplane TMP Power Controller fault register
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    def reset_pwr_fault_reg(self,tpm_id):
        i2c_add=0x80+power_supply_i2c_offset[tpm_id-1]
        status=self.mng.fpgai2c_write8(i2c_add,0x04,0x00,FPGA_I2CBUS.i2c2)#reset alarms

    ###pwr_on_tpm
    #This method power on the selected TPM board
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    #return status: status of operation
    def pwr_on_tpm(self,tpm_id):
        i2c_add=0x80+power_supply_i2c_offset[tpm_id-1]
        #print "I2C ADD "+hex(i2c_add)
        status=self.mng.fpgai2c_write8(i2c_add,0x04,0x00,FPGA_I2CBUS.i2c2)#reset alarms
        if(status!=0):
            print("Error writing on device " + hex(i2c_add))
            return status
        status=self.mng.fpgai2c_write8(i2c_add,0x00,0xBB,FPGA_I2CBUS.i2c2)#power on tpm
        if(status!=0):
            print("Error writing on device " + hex(i2c_add))
        else:
            if self.is_tpm_on(tpm_id):
                status=0
            else:
                status = 1
        return status

    ###pwr_off_tpm
    #This method power off the selected TPM board
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    #return status: status of operation
    def pwr_off_tpm(self,tpm_id):
        i2c_add=0x80+power_supply_i2c_offset[tpm_id-1]
        #print "I2C ADD "+hex(i2c_add)
        status=self.mng.fpgai2c_write8(i2c_add,0x00,0xB3,FPGA_I2CBUS.i2c2)#power off tpm
        if(status!=0):
            print("Error writing on device " + hex(i2c_add))
        else:
            if self.is_tpm_on(tpm_id)==False:
                status=0
            else:
                status = 1
        return status


    ###is_tpm_on
    #This method detect if the selected TPM board power control has powewred on the TPM
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    #return status: status of operation: True board is turned on, False board is turned off
    def is_tpm_on(self,tpm_id):
        i2c_add=0x80+power_supply_i2c_offset[tpm_id-1]
        data,status=self.mng.fpgai2c_read8(i2c_add,0x00,FPGA_I2CBUS.i2c2)
        if print_debug:
            print("is_tpm_on " + hex(data&0xff))
        if ((data&0xff)==0xbb):
            if print_debug:
                print("tpm on")
            return True
        else:
            if print_debug:
                print("tpm off")
            return False


    ###get_power_tpm
    #This method return the selected TPM board power control power value provided to TPM board
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    #return pwr: power value in W
    def get_power_tpm(self,tpm_id):
        power=self.mng.read("Fram.LTC4281_B"+str(tpm_id)+"_power")
        pwr=float(power*0.04*16.64*65536)/((65535*65535)*0.0025)
        pwr=round(pwr,3)
        if print_debug:
            print("power, "+str(pwr))
        return pwr

    ###get_voltage_tpm
    #This method return the selected TPM board power control voltage value provided to TPM board
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    #return vout: voltage value in V
    def get_voltage_tpm(self,tpm_id):
        voltage=self.mng.read("Fram.LTC4281_B"+str(tpm_id)+"_Vsource")
        vout=float(voltage*16.64)/(65535)
        vout=round(vout,3)
        if print_debug:
            print("voltage, " + str(vout))
        return vout

    ###get_pwr_fault_log
    #This method return the selected TPM board power control fault_log register value
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    #return status: status of operation
    #return data: register value
    def get_pwr_fault_log(self,tpm_id):
        i2c_add=0x80+power_supply_i2c_offset[tpm_id-1]
        data,status=self.mng.fpgai2c_read16(i2c_add,0x04,FPGA_I2CBUS.i2c2)
        if status==0:
            if data==0:
                print("No fault detected ")
            else:
                if data&0x1==0x1:
                    print("Over Voltage Detected")
                if data&0x2==0x2:
                    print("Under Voltage Detected")
                if data&0x4==0x4:
                    print("Over Current Detected")
                if data&0x8==0x8:
                    print("Power Bad Detected")
                if data&0x10==0x10:
                    print("On Fault Detected")
                if data&0x20==0x20:
                    print("FET Short Detected")
                if data&0x40==0x40:
                    print("FET Bad Fault Detected")
                if data&0x80==0x80:
                    print("EEPROM Done Detected")
        return data,status


    ###pwr_set_ilimt
    #This method set the selected TPM board power control I limit configuration register
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    #@param[in] cfg: configuration value (accepted value:0 to 7, minimal to maximum power selection)
    #return status: status of operation
    def pwr_set_ilimt(self,tpm_id,cfg):
        if cfg>7:
            print("Wrong parameter, accepted value from 0 to 7")
            status=1
            return status
        else:
            i2c_add=0x80+power_supply_i2c_offset[tpm_id-1]
            data,status=self.mng.fpgai2c_read8(i2c_add,0x11,FPGA_I2CBUS.i2c2)
            datatowr=int(data)|(cfg<<5)
            status=self.mng.fpgai2c_write8(i2c_add,0x11,datatowr,FPGA_I2CBUS.i2c2)
            return status

    ###pwr_set_ilimt
    #This method get the selected TPM board power control I limit configuration register
    #@param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    #return status: status of operation
    #return cfg: actual configuration value
    def pwr_get_ilimt(self,tpm_id):
        i2c_add=0x80+power_supply_i2c_offset[tpm_id-1]
        data,status=self.mng.fpgai2c_read8(i2c_add,0x11,FPGA_I2CBUS.i2c2)
        cfg=(data&0xE0)>>5
        return cfg,status


    #####BACKPLANE TEMPERATURE SENSORS FUNCTIONS
    #This method set a low alarm temperature value of selected temperature sensor
    #@param[in] sens_id: id of the selected sensor
    #@param[in] temp_alarm: temperature value
    #return status: status of operation
    def set_sens_temp_alarm_l(self,sens_id,temp_alarm):
        i2c_add=0x30+(sens_id-1)*2
        status=self.mng.fpgai2c_write16(i2c_add,0x03,temp_alarm,FPGA_I2CBUS.i2c2) #reset alarms
        return status


    #This method set an high alarm temperature value of selected temperature sensor
    #@param[in] sens_id: id of the selected sensor
    #@param[in] temp_alarm: temperature value
    #return status: status of operation
    def set_sens_temp_alarm_h(self,sens_id,temp_alarm):
        i2c_add=0x30+(sens_id-1)*2
        status=self.mng.fpgai2c_write16(i2c_add,0x04,temp_alarm,FPGA_I2CBUS.i2c2) #reset alarms
        return status

    #This method get the low alarm temperature value of selected temperature sensor
    #@param[in] sens_id: id of the selected sensor
    #return temperature: temperature value
    #return status: status of operation
    def get_sens_temp_alarm_l(self,sens_id):
        i2c_add=0x30+(sens_id-1)*2
        temperature,status=self.mng.fpgai2c_read16(i2c_add,0x03,FPGA_I2CBUS.i2c2)#read temperature alarm l
        return temperature,status

    #This method get the high alarm temperature value of selected temperature sensor
    #@param[in] sens_id: id of the selected sensor
    #return temperature: temperature value
    #return status: status of operation
    def get_sens_temp_alarm_h(self,sens_id):
        i2c_add=0x30+(sens_id-1)*2
        temperature,status=self.mng.fpgai2c_read16(i2c_add,0x04,FPGA_I2CBUS.i2c2)#read temperature alarm h
        return temperature,status


    #This method get the temperature value of selected temperature sensor placed on backplane board
    #@param[in] sens_id: id of the selected sensor
    #return temperature: temperature value
    #return status: status of operation
    def get_sens_temp(self,sens_id):
        if sens_id <1 or sens_id >2:
            print("Error Invalid ID")
            return 0xff,0x1
        temperature=self.mng.read("Fram.ADT7408_B"+str(sens_id)+"_temp")
        if (temperature & 0x1000)>>12==1:
            temp = float((temperature&0xfff - 4096)) / 16
        else:
            temp = float((temperature & 0xfff) )/16
        temp=round(temp,2)
        return temp,0x0


    ######BACKPLANE FAN FUNCTIONS

    #This method get the get_bkpln_fan_speed
    #@param[in] fan_id: id of the selected fan accepted value: 1-4
    #return fanrpm: fan rpm value
    #return fan_bank_pwm: pwm value of selected fan
    #return status: status of operation
    def get_bkpln_fan_speed(self, fan_id):
        if fan_id<1 or fan_id>4:
            print("Error Invalid Fan ID ")
            return 0,0,1
        fan = self.mng.read("Fram.FAN"+str(fan_id)+"_TACH")
        fanpwmreg = self.mng.read("Fram.FAN_PWM")
        #fan_settings = (fanpwmreg >> 24) & 0xff
        if fan_id<3:
            fan_bank = (fanpwmreg & 0xff)
        else:
            fan_bank = (fanpwmreg >> 8) & 0xff
        fan_bank_pwm = (float(fan_bank) / 255) * 100
        fan_bank_pwm_i =round(fan_bank_pwm,0)
        if fan==0xffff:
            fanrpm=0
        else:
            fanrpm=(90000 * 60)/fan
        return fanrpm,fan_bank_pwm_i,0



    #This method set the_bkpln_fan_speed
    #@param[in] fan_id: id of the selected fan accepted value: 1-4
    #@param[in] speed_pwm_perc: percentage value of fan RPM  (MIN 0=0% - MAX 100=100%)
    #return status: status of operation
    #@note settings of fan speed is possible only if fan mode is manual
    def set_bkpln_fan_speed(self,fan_id,speed_pwm_perc):
        if fan_id<1 or fan_id>4:
            print("Error Invalid Fan ID ")
            return 1
        fanpwmreg = self.mng.read("Fram.FAN_PWM")
        if fan_id>2:
            auto_mode=(fanpwmreg&0x02000000)>>25
        else:
            auto_mode = (fanpwmreg & 0x01000000) >> 24
        if auto_mode==1:
            print("Invalid command auto mode is Enable")
            return 2
        else:
            regval=((0xFF/100)*speed_pwm_perc)&0xff
            if fan_id>2:
                val=(fanpwmreg&0x0FFFF00)|(regval<<8)
            else:
                val=(fanpwmreg&0x00FFFF00)|regval
            self.mng.write("Fram.FAN_PWM",regval)
            return 0


    #This method get the_bkpln_fan_mode
    #@param[in] fan_id: id of the selected fan accepted value: 1-4
    #return fan mode: functional fan mode: auto or manual
    #return status: status of operation
    def get_bkpln_fan_mode(self,fan_id):
        if fan_id<1 or fan_id>4:
            print("Error Invalid Fan ID ")
            return 0,1
        fanpwmreg = self.mng.read("Fram.FAN_PWM")
        if fan_id>2:
            auto_mode=(fanpwmreg&0x02000000)>>25
        else:
            auto_mode = (fanpwmreg & 0x01000000) >> 24
        return auto_mode,0


    #This method get the_bkpln_fan_mode
    #@param[in] fan_id: id of the selected fan accepted value: 1-4
    #return fan mode: functional fan mode: auto or manual
    #return status: status of operation
    def set_bkpln_fan_mode(self,fan_id,auto_mode):
        if fan_id<1 or fan_id>4:
            print("Error Invalid Fan ID ")
            return 1
        fanpwmreg = self.mng.read("Fram.FAN_PWM")
        if auto_mode==1:
            if fan_id>2:
                self.mng.write("Fram.FAN_PWM",fanpwmreg|0x01000000)
            else:
                self.mng.write("Fram.FAN_PWM",fanpwmreg|0x01000000)
        else:
            if fan_id>2:
                self.mng.write("Fram.FAN_PWM",fanpwmreg&0xFFFFFF)
            else:
                self.mng.write("Fram.FAN_PWM",fanpwmreg&0xFFFFFF)
        return 0



    #####POWER SUPPLY FUNCTIONS

    #This method get the selected power supply status register
    #@param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    #return status_reg: register value
    #return status: status of operation
    def get_ps_status(self,ps_id):
        i2c_add=0xb0+((ps_id-1)*2)
        status_reg,status=self.mng.fpgai2c_read8(i2c_add,0x78,FPGA_I2CBUS.i2c3)
        return status_reg,status


    #This method get the selected power supply vout value evaluated on read from vout register
    #@param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    #return v: vout value
    def get_ps_vout(self,ps_id):
        vout=self.mng.read("Fram.PSU"+str(ps_id-1)+"_Vout")
        v=float(vout*pow(2,-9))
        v=round(v,3)
        return v

    #This method get the selected power supply iout value evaluated on read from iout register
    #@param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    #return i: iout value
    #return status: status of operation
    def get_ps_iout(self,ps_id):
        iout=self.mng.read("Fram.PSU"+str(ps_id-1)+"_Vout")
        i=float((iout&0x7FF)*pow(2,-3))
        i=round(i,3)
        return i

    #This method get the selected power supply power value evaluated on read from iout and vout registers
    #@param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    #return pw: power value
    #return status: status of operation
    def get_ps_power(self,ps_id):
        i=self.get_ps_iout(ps_id)
        v=self.get_ps_vout(ps_id)
        pw=float(v*i)
        pw=round(pw,3)
        return pw


    #This method set the fan_spped
    #@param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    #@param[in] speed_cmd: command value (MIN 0=0% - MAX 100=100%, Fan Speed = speed_cmd*21000RPM/100,Write request is executed only if the desired Fanspeed is greater than what is required by the PSU. )
    #return status: status of operation
    def set_ps_fanspeed(self,ps_id,speed_cmd):
        i2c_add=0xb0+((ps_id-1)*2)
        if speed_cmd>100 or speed_cmd<0:
            status=-2
            print("Error[set_ps_fanspeed]: Invalid speed parameter")
            return status
        status=self.mng.fpgai2c_write16(i2c_add,0x3B,speed_cmd,FPGA_I2CBUS.i2c3)
        return status

    #This method get the fan_spped
    #@param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    #return speed_param: speed reg value (MIN 0=0% - MAX 100=100%, Fan Speed = speed_cmd*21000RPM/100,Write request is executed only if the desired Fanspeed is greater than what is required by the PSU. )
    #return status: status of operation
    def get_ps_fanspeed(self,ps_id):
        i2c_add=0xb0+((ps_id-1)*2)
        speed_param,status=self.mng.fpgai2c_read16(i2c_add,0x3B,FPGA_I2CBUS.i2c3)
        return speed_param,status

    def close(self):
        self.__del__()
