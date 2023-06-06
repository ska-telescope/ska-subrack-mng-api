__author__ = 'Cristian Albanese'
import string
from subprocess import Popen, PIPE
import sys
import os
import time
from subrack_mng_api import management
from subrack_mng_api.management import FPGA_I2CBUS
print_debug = False
import Pyro5.api
import logging
logger=logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)

class BackplaneInvalidParameter(Exception):
    """ Define an exception which occurs when an invalid parameter is provided
    to a function or class method """
    pass


power_supply_i2c_offset = [0x0,0x2,0x4,0x6,0x8,0xa,0xc,0xe]

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
    {'name': "LTC4281_1", "ICadd": 0x80, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x4c,
     "ref_val": 0xaa, "res_val":0x0, "op_check": "rw", "access":"CPLD"},
    {'name': "LTC4281_2", "ICadd": 0x82, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x4c,
     "ref_val": 0xaa, "res_val": 0x0, "op_check": "rw", "access": "CPLD"},
    {'name': "LTC4281_3", "ICadd": 0x84, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x4c,
     "ref_val": 0xaa, "res_val": 0x0, "op_check": "rw", "access": "CPLD"},
    {'name': "LTC4281_4", "ICadd": 0x86, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x4c,
     "ref_val": 0xaa, "res_val": 0x0, "op_check": "rw", "access": "CPLD"},
    {'name': "LTC4281_5", "ICadd": 0x88, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x4c,
     "ref_val": 0xaa, "res_val": 0x0, "op_check": "rw", "access": "CPLD"},
    {'name': "LTC4281_6", "ICadd": 0x8c, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x4c,
     "ref_val": 0xaa, "res_val": 0x0, "op_check": "rw", "access": "CPLD"},
    {'name': "LTC4281_7", "ICadd": 0x8e, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": 0x4c,
     "ref_val": 0xaa, "res_val": 0x0, "op_check": "rw", "access": "CPLD"},
    {'name': "PCF8574TS_1", "ICadd": 0x40, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": None,
     "ref_val": None, "res_val": 0x0, "op_check": None, "access": "CPLD"},
    {'name': "PCF8574TS_2", "ICadd": 0x40, "i2cbus_id": FPGA_I2CBUS.i2c2, "bus_size": 1, "ref_add": None,
     "ref_val": None, "res_val": 0x0, "op_check": None, "access": "CPLD"},
]

def twos_comp(val, bits):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val

#Decode/encode Linear data format => X=Y*2^N
def _decodePMBus(message):
    messageN = message >> 11
    messageY = message & 0b0000011111111111
    message = messageY*(2.0**(twos_comp(messageN, 5))) #calculate real values (everything but VOUT works)
    return message

# mng=MngBoard()
# ## Backplane Board Class
# This class contain methods to permit access to major functionality
# of backplane board from management CPU (iMX6) via registers mapped in filesystem
@Pyro5.api.expose
@Pyro5.server.behavior(instance_mode="single")
class Backplane():
    def __init__(self, Management_b, simulation):
        self.data = []
        self.mng = Management_b
        self.simulation = simulation
        self.ps_vout_mode=[]
        self.ps_vout_n=[]
        for i in range(2):
            vout,status=self.get_ps_vout_mode(i+1)
            self.ps_vout_mode.append(vout)
            self.ps_vout_n.append(twos_comp(self.ps_vout_mode[i],5))

    def __del__(self):
        self.data = []

    # #####BACKPLANE TPM POWER CONTROL FUNCTIONS

    # ##power_on_bkpln
    # #This method Power On the Bacplane Board providing supply to the TPMs Powercontrol devices
    # #@param[in] onoff: select the operation: 1 power on, 0 power off
    def power_on_bkpln(self):
        logger.info("power_on_bkpln")
        self.mng.write("CtrlRegs.BkplOnOff", 1)
        rdval = self.mng.read("CtrlRegs.BkplOnOff")
        if rdval != 1:
            logger.error("Error during operation: Expected %d, Read %d" % (1, rdval))

    # ##power_off_bkpln
    # This method Power Off the Bacplane Board providing supply to the TPMs Powercontrol devices
    # #@param[in] onoff: select the operation: 1 power on, 0 power off
    def power_off_bkpln(self):
        self.mng.write("CtrlRegs.BkplOnOff", 0)
        rdval = self.mng.read("CtrlRegs.BkplOnOff")
        if rdval != 0:
            logger.error("Error during operation: Expected %d, Read %d" % (0, rdval))

    # ##get_bkpln_is_onoff
    # This method return the status of the Power On/Off registers for the Backplane Board power on,off
    # return onoff: status of backplane board, 0 Pwered Off, 1 Powered On
    def get_bkpln_is_onoff(self):
        rdval = self.mng.read("CtrlRegs.BkplOnOff")
        return rdval

    # ##reset_pwr_fault_reg
    # This method reset the Bacplane TMP Power Controller fault register
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    def reset_pwr_fault_reg(self, tpm_id):
        i2c_add = 0x80+power_supply_i2c_offset[tpm_id-1]
        status = self.mng.fpgai2c_write8(i2c_add, 0x04, 0x00, FPGA_I2CBUS.i2c2)  # reset alarms

    # ##pwr_on_tpm
    # This method power on the selected TPM board
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation
    def pwr_on_tpm(self, tpm_id):
        i2c_add = 0x80+power_supply_i2c_offset[tpm_id-1]
        # print "I2C ADD "+hex(i2c_add)
        status = self.mng.fpgai2c_write8(i2c_add, 0x04, 0x00, FPGA_I2CBUS.i2c2)  # reset alarms
        if status != 0:
            logger.error("Error writing on device " + hex(i2c_add))
            return status
        status = self.mng.fpgai2c_write8(i2c_add, 0x00, 0xBB, FPGA_I2CBUS.i2c2)  # power on tpm
        # update poweron reg used only for symulation
        if self.simulation is True:
            reg = self.mng.read("Fram.TPM_SUPPLY_STATUS")
            reg = reg | (1 << tpm_id-1)
            self.mng.write("Fram.TPM_SUPPLY_STATUS", reg)
        # end of update sequence
        if status != 0:
            logger.error("Error writing on device " + hex(i2c_add))
        else:
            if self.is_tpm_on(tpm_id):
                status = 0
            else:
                status = 1
        return status

    # ##pwr_off_tpm
    # This method power off the selected TPM board
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation
    def pwr_off_tpm(self, tpm_id):
        i2c_add = 0x80 + power_supply_i2c_offset[tpm_id-1]
        # print "I2C ADD "+hex(i2c_add)
        status = self.mng.fpgai2c_write8(i2c_add, 0x00, 0xB3, FPGA_I2CBUS.i2c2)  # power off tpm
        # update poweron reg used only for symulation
        if self.simulation is True:
            reg = self.mng.read("Fram.TPM_SUPPLY_STATUS")
            reg = reg ^ (1 << (tpm_id - 1))
            self.mng.write("Fram.TPM_SUPPLY_STATUS", reg)
        # end of update sequence
        if status != 0:
            logger.error("Error writing on device " + hex(i2c_add))
        else:
            if self.is_tpm_on(tpm_id) is False:
                status = 0
            else:
                status = 1
        return status

    # ##is_tpm_on
    # This method detect if the selected TPM board power control has powewred on the TPM
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation: True board is turned on, False board is turned off
    def is_tpm_on(self, tpm_id):
        i2c_add = 0x80+power_supply_i2c_offset[tpm_id-1]
        data, status = self.mng.fpgai2c_read8(i2c_add, 0x00, FPGA_I2CBUS.i2c2)
        if print_debug:
            logger.debug("is_tpm_on " + hex(data & 0xff))
        if (data & 0xff) == 0xbb:
            if print_debug:
                logger.debug("tpm on")
            return True
        else:
            if print_debug:
                logger.debug("tpm off")
            return False

    # ##get_power_tpm
    # This method return the selected TPM board power control power value provided to TPM board
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return pwr: power value in W
    def get_power_tpm(self, tpm_id):
        if self.simulation is True:
            if self.is_tpm_on(tpm_id):
                power = self.mng.read("Fram.LTC4281_B" + str(tpm_id) + "_power")
            else:
                power = 0.0
            pwr = round(power, 3)
        else:
            power = self.mng.read("Fram.LTC4281_B"+str(tpm_id)+"_power")
            pwr = float(power*0.04*16.64*65536)/((65535*65535)*0.0025)
            pwr = round(pwr, 3)
        if print_debug:
            logger.debug("power, "+str(pwr))
        return pwr

    # ##get_voltage_tpm
    # This method return the selected TPM board power control voltage value provided to TPM board
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return vout: voltage value in V
    def get_voltage_tpm(self, tpm_id):
        if self.simulation is True:
            if self.is_tpm_on(tpm_id):
                voltage = self.mng.read("Fram.LTC4281_B" + str(tpm_id) + "_Vsource")
            else:
                voltage = 0.0
            vout = float(voltage * 16.64) / 65535
            vout = round(vout, 3)
        else:
            voltage = self.mng.read("Fram.LTC4281_B"+str(tpm_id)+"_Vsource")
            vout = float(voltage*16.64)/65535
            vout = round(vout, 3)
        if print_debug:
            logger.info("voltage, " + str(vout))
        return vout

    # ##get_pwr_fault_log
    # This method return the selected TPM board power control fault_log register value
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation
    # return data: register value
    def get_pwr_fault_log(self, tpm_id):
        i2c_add = 0x80+power_supply_i2c_offset[tpm_id-1]
        data, status = self.mng.fpgai2c_read16(i2c_add, 0x04, FPGA_I2CBUS.i2c2)
        if status == 0:
            if data == 0:
                logger.info("No fault detected ")
            else:
                if data & 0x1 == 0x1:
                    logger.error("Over Voltage Detected")
                if data & 0x2 == 0x2:
                    logger.error("Under Voltage Detected")
                if data & 0x4 == 0x4:
                    logger.error("Over Current Detected")
                if data & 0x8 == 0x8:
                    logger.error("Power Bad Detected")
                if data & 0x10 == 0x10:
                    logger.error("On Fault Detected")
                if data & 0x20 == 0x20:
                    logger.error("FET Short Detected")
                if data & 0x40 == 0x40:
                    logger.error("FET Bad Fault Detected")
                if data & 0x80 == 0x80:
                    logger.error("EEPROM Done Detected")
        return data, status

    # ##pwr_set_ilimt
    # This method set the selected TPM board power control I limit configuration register
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # @param[in] cfg: configuration value (accepted value:0 to 7, minimal to maximum power selection)
    # return status: status of operation
    def pwr_set_ilimt(self, tpm_id, cfg):
        if cfg > 7:
            logger.error("Wrong parameter, accepted value from 0 to 7")
            status = 1
            return status
        else:
            self.reset_pwr_fault_reg(tpm_id)
            i2c_add = 0x80+power_supply_i2c_offset[tpm_id-1]
            data, status = self.mng.fpgai2c_read8(i2c_add, 0x11, FPGA_I2CBUS.i2c2)
            datatowr = int(data) | (cfg << 5)
            status = self.mng.fpgai2c_write8(i2c_add, 0x11, datatowr, FPGA_I2CBUS.i2c2)
            return status

    # ##pwr_set_ilimt
    # This method get the selected TPM board power control I limit configuration register
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation
    # return cfg: actual configuration value
    def pwr_get_ilimt(self, tpm_id):
        i2c_add = 0x80+power_supply_i2c_offset[tpm_id-1]
        data, status = self.mng.fpgai2c_read8(i2c_add, 0x11, FPGA_I2CBUS.i2c2)
        cfg = (data & 0xE0) >> 5
        return cfg, status

    # ####BACKPLANE TEMPERATURE SENSORS FUNCTIONS
    # This method set a low alarm temperature value of selected temperature sensor
    # @param[in] sens_id: id of the selected sensor
    # @param[in] temp_alarm: temperature value
    # return status: status of operation
    def set_sens_temp_alarm_l(self, sens_id, temp_alarm):
        i2c_add = 0x30+(sens_id-1)*2
        status = self.mng.fpgai2c_write16(i2c_add, 0x03, temp_alarm, FPGA_I2CBUS.i2c2)  # reset alarms
        return status

    # This method set an high alarm temperature value of selected temperature sensor
    # @param[in] sens_id: id of the selected sensor
    # @param[in] temp_alarm: temperature value
    # return status: status of operation
    def set_sens_temp_alarm_h(self, sens_id, temp_alarm):
        i2c_add = 0x30+(sens_id-1)*2
        status = self.mng.fpgai2c_write16(i2c_add, 0x04, temp_alarm, FPGA_I2CBUS.i2c2)  # reset alarms
        return status

    # This method get the low alarm temperature value of selected temperature sensor
    # @param[in] sens_id: id of the selected sensor
    # return temperature: temperature value
    # return status: status of operation
    def get_sens_temp_alarm_l(self, sens_id):
        i2c_add = 0x30+(sens_id-1)*2
        temperature, status = self.mng.fpgai2c_read16(i2c_add, 0x03, FPGA_I2CBUS.i2c2)  # read temperature alarm l
        return temperature, status

    # This method get the high alarm temperature value of selected temperature sensor
    # @param[in] sens_id: id of the selected sensor
    # return temperature: temperature value
    # return status: status of operation
    def get_sens_temp_alarm_h(self, sens_id):
        i2c_add = 0x30+(sens_id-1)*2
        temperature, status = self.mng.fpgai2c_read16(i2c_add, 0x04, FPGA_I2CBUS.i2c2)  # read temperature alarm h
        return temperature, status

    # This method get the temperature value of selected temperature sensor placed on backplane board
    # @param[in] sens_id: id of the selected sensor
    # return temperature: temperature value
    # return status: status of operation
    def get_sens_temp(self, sens_id, ret_val_only = False):
        if sens_id < 1 or sens_id > 2:
            logger.error("Error Invalid ID")
            if ret_val_only:
                return None
            return 0xff, 0x1
        temperature = self.mng.read("Fram.ADT7408_B"+str(sens_id)+"_temp")
        if (temperature & 0x1000) >> 12 == 1:
            temp = float((temperature & 0xfff - 4096))/16
        else:
            temp = float((temperature & 0xfff))/16
        temp = round(temp, 2)
        if ret_val_only:
            return temp
        return temp, 0x0

        

    # ####BACKPLANE FAN FUNCTIONS
    # This method get the get_bkpln_fan_speed
    # @param[in] fan_id: id of the selected fan accepted value: 1-4
    # return fanrpm: fan rpm value
    # return fan_bank_pwm: pwm value of selected fan
    # return status: status of operation
    def get_bkpln_fan_speed(self, fan_id):
        if fan_id < 1 or fan_id > 4:
            logger.error("Error Invalid Fan ID ")
            return 0, 0, 1
        fan = self.mng.read("Fram.FAN"+str(fan_id)+"_TACH")
        fanpwmreg = self.mng.read("Fram.FAN_PWM")
        # fan_settings = (fanpwmreg >> 24) & 0xff
        if fan_id < 3:
            fan_bank = (fanpwmreg & 0xff)
        else:
            fan_bank = (fanpwmreg >> 8) & 0xff
        fan_bank_pwm = (float(fan_bank) / 255) * 100
        fan_bank_pwm_i = round(fan_bank_pwm, 0)
        if fan == 0xffff:
            fanrpm = 0
        else:
            fanrpm = (90000 * 60)//fan
        return fanrpm, fan_bank_pwm_i, 0

    # This method set the_bkpln_fan_speed
    # @param[in] fan_id: id of the selected fan accepted value: 1-4
    # @param[in] speed_pwm_perc: percentage value of fan RPM  (MIN 0=0% - MAX 100=100%)
    # return status: status of operation
    # @note settings of fan speed is possible only if fan mode is manual
    def set_bkpln_fan_speed(self, fan_id, speed_pwm_perc):
        if fan_id < 1 or fan_id > 4:
            logger.error("Error Invalid Fan ID ")
            return 1
        fanpwmreg = self.mng.read("Fram.FAN_PWM")
        if fan_id > 2:
            auto_mode = (fanpwmreg & 0x02000000) >> 25
        else:
            auto_mode = (fanpwmreg & 0x01000000) >> 24
        if auto_mode == 1:
            logger.error("Invalid command auto mode is Enable")
            return 2
        else:
            if speed_pwm_perc < 0 or speed_pwm_perc > 100:
                logger.error("Error, It should be  0 < speed_pwm_perc < 100, given %s!" % str(speed_pwm_perc))
                return 3
            regval = int(round(float(speed_pwm_perc)/100*255)) & 0xff
            if fan_id > 2:
                val = (fanpwmreg & 0x0FF00FF) | (regval << 8)
            else:
                val = (fanpwmreg & 0x00FFFF00) | regval
            self.mng.write("Fram.FAN_PWM", val)
            return 0

    # This method get the_bkpln_fan_mode
    # @param[in] fan_id: id of the selected fan accepted value: 1-4
    # return fan mode: functional fan mode: auto or manual
    # return status: status of operation
    def get_bkpln_fan_mode(self, fan_id):
        if fan_id < 1 or fan_id > 4:
            logger.error("Error Invalid Fan ID ")
            return 0, 1
        fanpwmreg = self.mng.read("Fram.FAN_PWM")
        if fan_id > 2:
            auto_mode = (fanpwmreg & 0x02000000) >> 25
        else:
            auto_mode = (fanpwmreg & 0x01000000) >> 24
        return auto_mode, 0

    # This method get the_bkpln_fan_mode
    # @param[in] fan_id: id of the selected fan accepted value: 1-4
    # return fan mode: functional fan mode: auto or manual
    # return status: status of operation
    def set_bkpln_fan_mode(self, fan_id, auto_mode):
        if fan_id < 1 or fan_id > 4:
            logger.error("Error Invalid Fan ID ")
            return 1
        fanpwmreg = self.mng.read("Fram.FAN_PWM")
        if auto_mode == 1:
            if fan_id > 2:
                self.mng.write("Fram.FAN_PWM", fanpwmreg | 0x02000000)
            else:
                self.mng.write("Fram.FAN_PWM", fanpwmreg | 0x01000000)
        else:
            if fan_id > 2:
                self.mng.write("Fram.FAN_PWM", fanpwmreg & (~0x02000000))
            else:
                self.mng.write("Fram.FAN_PWM", fanpwmreg & (~0x01000000))
        return 0

    def check_i2c_backplane_devices_access(self):
        result = []
        wr_op_passed = False
        for i in range(0, len(backplane_i2c_devices)):
            logger.info("Device: %s" %backplane_i2c_devices[i]["name"])
            if backplane_i2c_devices[i]["access"] == "CPLD":
                if backplane_i2c_devices[i]["op_check"] == "ro":
                    retval=0
                    if backplane_i2c_devices[i]["bus_size"] == 2:
                        retval,state = self.mng.fpgai2c_read16(backplane_i2c_devices[i]["ICadd"], backplane_i2c_devices[i]["ref_add"],
                                                           backplane_i2c_devices[i]["i2cbus_id"])
                    else:
                        retval,state = self.mng.fpgai2c_read8(backplane_i2c_devices[i]["ICadd"], backplane_i2c_devices[i]["ref_add"],
                                                          backplane_i2c_devices[i]["i2cbus_id"])
                    if retval != backplane_i2c_devices[i]["ref_val"]:
                        result.append({"name":backplane_i2c_devices[i]["name"],"test_result": "FAILED",
                                       "expected": backplane_i2c_devices[i]["ref_val"],
                                       "read": retval})
                        logger.info("FAILED, checking dev: %s, read value %x, expected %x" % (backplane_i2c_devices[i]["name"],
                                                                                              retval, backplane_i2c_devices[i]["ref_val"]))
                    else:
                        result.append({"name":backplane_i2c_devices[i]["name"],"test_result": "PASSED",
                                       "expected": backplane_i2c_devices[i]["ref_val"],
                                       "read": retval})
                        logger.info("PASSED, checking dev: %s, read value %x, expected %x" % (backplane_i2c_devices[i]["name"],
                                                                                              retval, backplane_i2c_devices[i]["ref_val"]))
                if backplane_i2c_devices[i]["op_check"] == "rw":
                    retval=0
                    if backplane_i2c_devices[i]["bus_size"] == 2:
                        logger.info("Writing16...")
                        self.mng.fpgai2c_write16(backplane_i2c_devices[i]["ICadd"], backplane_i2c_devices[i]["ref_add"],
                                             backplane_i2c_devices[i]["ref_val"],backplane_i2c_devices[i]["i2cbus_id"])
                        logger.info("reading16...")
                        retval,state = self.mng.fpgai2c_read16(backplane_i2c_devices[i]["ICadd"], backplane_i2c_devices[i]["ref_add"],
                                                           backplane_i2c_devices[i]["i2cbus_id"])

                    else:
                        logger.info("Writing8...")
                        self.mng.fpgai2c_write8(backplane_i2c_devices[i]["ICadd"], backplane_i2c_devices[i]["ref_add"],
                                            backplane_i2c_devices[i]["ref_val"], backplane_i2c_devices[i]["i2cbus_id"])
                        logger.info("reading8...")
                        retval,state = self.mng.fpgai2c_read8(backplane_i2c_devices[i]["ICadd"], backplane_i2c_devices[i]["ref_add"],
                                                          backplane_i2c_devices[i]["i2cbus_id"])
                    if retval != backplane_i2c_devices[i]["ref_val"]:
                        result.append({"name":backplane_i2c_devices[i]["name"],"test_result": "FAILED",
                                       "expected": backplane_i2c_devices[i]["ref_val"],
                                       "read": retval})
                        logger.info("FAILED, checking dev: %s, read value %x, expected %x" % (backplane_i2c_devices[i]["name"],
                                                                                              retval,
                                                                                              backplane_i2c_devices[i]["ref_val"]))
                    else:

                        wr_op_passed = True
                        result.append({"name":backplane_i2c_devices[i]["name"],"test_result": "PASSED",
                                       "expected": backplane_i2c_devices[i]["ref_val"],
                                       "read": retval})
                        logger.info("PASSED, checking dev: %s, read value %x, expected %x" % (backplane_i2c_devices[i]["name"],
                                                                                              retval,
                                                                                              backplane_i2c_devices[i]["ref_val"]))
                    if wr_op_passed == True:
                        logger.info("Restoring value")
                        if backplane_i2c_devices[i]["bus_size"] == 2:
                            self.mng.fpgai2c_write16(backplane_i2c_devices[i]["ICadd"], backplane_i2c_devices[i]["ref_add"],
                                                 backplane_i2c_devices[i]["res_val"],backplane_i2c_devices[i]["i2cbus_id"])
                        else:
                            self.mng.fpgai2c_write8(backplane_i2c_devices[i]["ICadd"], backplane_i2c_devices[i]["ref_add"],
                                                backplane_i2c_devices[i]["res_val"], backplane_i2c_devices[i]["i2cbus_id"])
            elif backplane_i2c_devices[i]["access"] == "CPLD":
                if backplane_i2c_devices[i]["op_check"] == "ro":
                    retval = 0
                    if backplane_i2c_devices[i]["bus_size"] == 2:
                        retval = self.mng.read_i2c(backplane_i2c_devices[i]["i2cbus_id"],backplane_i2c_devices[i]["ICadd"] >> 1,
                                               backplane_i2c_devices[i]["ref_add"],"w")
                    else:
                        retval = self.mng.read_i2c(backplane_i2c_devices[i]["i2cbus_id"],backplane_i2c_devices[i]["ICadd"] >> 1,
                                               backplane_i2c_devices[i]["ref_add"],"b")
                    if retval != backplane_i2c_devices[i]["ref_val"]:
                        result.append({"name":backplane_i2c_devices[i]["name"],"test_result": "FAILED",
                                       "expected": backplane_i2c_devices[i]["ref_val"],
                                       "read": retval})
                        logger.info("FAILED, checking dev: %s, read value %x, expected %x" % (backplane_i2c_devices[i]["name"],
                                                                                              retval,
                                                                                              backplane_i2c_devices[i]["ref_val"]))
                    else:
                        result.append({"name":backplane_i2c_devices[i]["name"],"test_result": "PASSED",
                                       "expected": backplane_i2c_devices[i]["ref_val"],
                                       "read": retval})
                        logger.info("PASSED, checking dev: %s, read value %x, expected %x" % (backplane_i2c_devices[i]["name"],
                                                                                              retval,
                                                                                              backplane_i2c_devices[i]["ref_val"]))
                if backplane_i2c_devices[i]["op_check"] == "rw":
                    retval = 0
                    if backplane_i2c_devices[i]["bus_size"] == 2:
                        logger.info("Writing16...")
                        self.write_i2c(backplane_i2c_devices[i]["i2cbus_id"],backplane_i2c_devices[i]["ICadd"] >> 1,
                                       backplane_i2c_devices[i]["ref_add"],"w",backplane_i2c_devices[i]["ref_val"])
                        logger.info("reading16...")
                        retval = self.mng.read_i2c(backplane_i2c_devices[i]["i2cbus_id"],backplane_i2c_devices[i]["ICadd"] >> 1,
                                               backplane_i2c_devices[i]["ref_add"],"w")
                    else:
                        logger.info("Writing8...")
                        self.write_i2c(backplane_i2c_devices[i]["i2cbus_id"],backplane_i2c_devices[i]["ICadd"] >> 1,
                                       backplane_i2c_devices[i]["ref_add"],"b",backplane_i2c_devices[i]["ref_val"])
                        logger.info("reading8...")
                        retval = self.mng.read_i2c(backplane_i2c_devices[i]["i2cbus_id"],backplane_i2c_devices[i]["ICadd"] >> 1,
                                               backplane_i2c_devices[i]["ref_add"],"b")
                    if retval != backplane_i2c_devices[i]["ref_val"]:
                        result.append({"name":backplane_i2c_devices[i]["name"],"test_result": "FAILED",
                                       "expected": backplane_i2c_devices[i]["ref_val"],
                                       "read": retval})
                        logger.info("FAILED, checking dev: %s, read value %x, expected %x" % (backplane_i2c_devices[i]["name"],
                                                                                              retval,
                                                                                              backplane_i2c_devices[i]["ref_val"]))
                    else:

                        wr_op_passed = True
                        result.append({"name":backplane_i2c_devices[i]["name"],"test_result": "PASSED",
                                       "expected": backplane_i2c_devices[i]["ref_val"],
                                       "read": retval})
                        logger.info("PASSED, checking dev: %s, read value %x, expected %x" % (backplane_i2c_devices[i]["name"],
                                                                                              retval,
                                                                                              backplane_i2c_devices[i]["ref_val"]))
                    if wr_op_passed == True:
                        logger.info("Restoring value")
                        if backplane_i2c_devices[i]["bus_size"] == 2:
                            self.mng.write_i2c(backplane_i2c_devices[i]["i2cbus_id"], backplane_i2c_devices[i]["ICadd"] >> 1,
                                           backplane_i2c_devices[i]["ref_add"], "w", backplane_i2c_devices[i]["res_val"])
                        else:
                            self.mng.write_i2c(backplane_i2c_devices[i]["i2cbus_id"], backplane_i2c_devices[i]["ICadd"] >> 1,
                                           backplane_i2c_devices[i]["ref_add"], "b", backplane_i2c_devices[i]["res_val"])
            else:
                pass
        return result


    # ####POWER SUPPLY FUNCTIONS
    # This method get the selected power supply status register
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return status_reg: register value
    # return status: status of operation
    def get_ps_status(self, ps_id):
        ioexp_value, status = self.mng.fpgai2c_read8(0x40, None, FPGA_I2CBUS.i2c3)
        if status != 0:
            return None
        if bool(ioexp_value & (0b1<<(ps_id-1))):
            res = {
                "present" :       False,
                "busy" :          False,
                "off" :           False,
                "vout_ov_fault" : False,
                "iout_oc_fault" : False,
                "vin_uv_fault" :  False,
                "temp_fault" :    False,
                "cml_fault" :     False,
                "vout_fault" :    False,
                "iout_fault" :    False,
                "input_fault" :   False,
                "pwr_gd" :        False,
                "fan_fault" :     False,
                "other" :         False,
                "unknown" :       False,
            }
            return res
        i2c_add = 0xb0+((ps_id-1)*2)
        #status_reg, status = self.mng.fpgai2c_read8(i2c_add, 0x78, FPGA_I2CBUS.i2c3)
        status_reg, status = self.mng.fpgai2c_read16(i2c_add, 0x79, FPGA_I2CBUS.i2c3)
        if status != 0:
            return None
        res = {
            "present" :       True,
            "busy" :          bool(status_reg & (0b1<<7)),
            "off" :           bool(status_reg & (0b1<<6)),
            "vout_ov_fault" : bool(status_reg & (0b1<<5)),
            "iout_oc_fault" : bool(status_reg & (0b1<<4)),
            "vin_uv_fault" :  bool(status_reg & (0b1<<3)),
            "temp_fault" :    bool(status_reg & (0b1<<2)),
            "cml_fault" :     bool(status_reg & (0b1<<1)),
            "vout_fault" :    bool(status_reg & (0b1<<15)),
            "iout_fault" :    bool(status_reg & (0b1<<14)),
            "input_fault" :   bool(status_reg & (0b1<<13)),
            "pwr_gd" :        not bool(status_reg & (0b1<<11)),
            "fan_fault" :     bool(status_reg & (0b1<<10)),
            "other" :         bool(status_reg & (0b1<<9)),
            "unknown" :       bool(status_reg & (0b1<<8)),
        }
        return res
        
    def get_ps_vout_mode(self, ps_id):
        i2c_add = 0xb0+((ps_id-1)*2)
        vout_mode, status = self.mng.fpgai2c_read8(i2c_add, 0x20, FPGA_I2CBUS.i2c3)
        return vout_mode, status

    # This method get the selected power supply vout value evaluated on read from vout register
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return v: vout value
    def get_ps_vout(self, ps_id):
        status = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Status_Vout")
        if status == 255:
            return 0
        vout = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Vout")
        v = float(vout*pow(2, self.ps_vout_n[ps_id-1]))
        v = round(v, 3)
        return v

    # This method get the selected power supply iout value evaluated on read from iout register
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return i: iout value
    # return status: status of operation
    def get_ps_iout(self, ps_id):
        status = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Status_Iout")
        if status == 255:
            return 0
        iout = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Iout")
        i = _decodePMBus(iout)
        i = round(i, 3)
        return i

    # This method get the selected power supply power value evaluated on read from iout and vout registers
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return pw: power value
    # return status: status of operation
    def get_ps_power(self, ps_id):
        i = self.get_ps_iout(ps_id)
        v = self.get_ps_vout(ps_id)
        pw = float(v*i)
        pw = round(pw, 3)
        return pw

    # This method set the fan_spped
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # @param[in] speed_cmd: command value (MIN 0=0% - MAX 100=100%, Fan Speed = speed_cmd*21000RPM/100,Write request is
    # executed only if the desired Fanspeed is greater than what is required by the PSU. )
    # return status: status of operation
    def set_ps_fanspeed(self, ps_id, speed_cmd):
        i2c_add = 0xb0+((ps_id-1)*2)
        if speed_cmd > 100 or speed_cmd < 0:
            status = -2
            logger.error("Error[set_ps_fanspeed]: Invalid speed parameter")
            return status
        status = self.mng.fpgai2c_write16(i2c_add, 0x3B, speed_cmd, FPGA_I2CBUS.i2c3)
        return status

    # This method get the fan_spped
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return speed_param: speed reg value (MIN 0=0% - MAX 100=100%, Fan Speed = speed_cmd*21000RPM/100,Write request is
    # executed only if the desired Fanspeed is greater than what is required by the PSU. )
    # return status: status of operation
    def get_ps_fanspeed(self, ps_id):
        i2c_add = 0xb0+((ps_id-1)*2)
        speed_param, status = self.mng.fpgai2c_read16(i2c_add, 0x3B, FPGA_I2CBUS.i2c3)
        return speed_param, status

    def close(self):
        self.__del__()
