__author__ = 'Cristian Albanese'
import string
from subprocess import Popen, PIPE
import sys
import os
import time
from subrack_mng_api import management
from subrack_mng_api.management import FPGA_I2CBUS

print_debug = False
import logging
import socket
import struct
logger=logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)

class BackplaneInvalidParameter(Exception):
    """ Define an exception which occurs when an invalid parameter is provided
    to a function or class method """
    pass






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

eep_sec = {
    "ip_address":   {"offset": 0x00, "size": 4, "name": "ip_address", "type": "ip", "protected": False},
    "netmask":      {"offset": 0x04, "size": 4, "name": "netmask", "type": "ip", "protected": False},
    "gateway":      {"offset": 0x08, "size": 4, "name": "gateway", "type": "ip", "protected": False},
    "HARDWARE_REV": {"offset": 0x0c, "size": 3, "name": "HARDWARE_REV", "type": "bytearray", "protected": True},
    "PCB_REV":      {"offset": 0x0f, "size": 1, "name": "PCB_REV", "type": "string", "protected": True},
    "SN":           {"offset": 0x10, "size": 16, "name": "SN", "type": "string", "protected": True},
}



class PCF8574_dev():
    def __init__(self,mng,id):
        self.mng = mng
        self.i2c_PCF8574_add = [0x40,0x42]
        self.i2c_bus = FPGA_I2CBUS.i2c2
        self.i2c_add = self.i2c_PCF8574_add[id]
        self.name = "FPGA_I2CBUS.i2c2.PCF8547(0x%x)"%(self.i2c_add)
        self.input_mask = 0xff
        #self.config_input_pin(self.input_mask)

    def config_input_pin(self,port_id):
       #set port in read mode 
        status = 0
        mask = self.input_mask | (1 << port_id)       
        data, status = self.mng.fpgai2c_op(self.i2c_add, 1, 0, mask, self.i2c_bus)
        if status != 0:
            logger.error(self.name + " Error reading on device " + hex(self.i2c_add))
        else:
            self.input_mask = mask
        return status

    def get_port(self,port_id):
       #set port in read mode 
        status = 0
        mask = self.input_mask | (1 << port_id)       
        data, status = self.mng.fpgai2c_op(self.i2c_add, 1, 0, mask, self.i2c_bus)
        if status != 0:
            logger.error(self.name + " Error reading on device " + hex(self.i2c_add))
            return 0xff, status
        self.input_mask = mask
        #read ports 
        data, status = self.mng.fpgai2c_op(self.i2c_add, 0, 1, 0, self.i2c_bus)
        if status != 0:
            logger.error(self.name + " Error reading on device " + hex(self.i2c_add))
            return 0xff, status
        # print(self.name, "read", reg, hex(data))
        data = (data >> port_id) & 0x1
        return data, status

    def set_port(self,port_id, port_value):
        status=0
        if port_value == 0:
            value= (( 1 << 8) - 1 - port_id) & self.input_mask
        else:
            value = self.input_mask | (1 << port_id)
        self.input_mask = value
        data, status = self.mng.fpgai2c_op(self.i2c_add, 1, 0, value, self.i2c_bus)
        if status != 0:
            logger.error(self.name + " Error reading on device " + hex(self.i2c_add))
            
        return status



    


class LTC428x_dev():

    def __init__(self,tpm_id,mng):
        self.tpm_id = tpm_id
        self.mng = mng
        self.i2c_bus = FPGA_I2CBUS.i2c2
        power_supply_i2c_offset = [0x80,0x82,0x84,0x86,0x88,0x8a,0x8c,0x8e]
        self.i2c_add = power_supply_i2c_offset[tpm_id-1]
        self.name = "FPGA_I2CBUS.i2c2.LTC428x_dev.tpm_id.%d(0x%x)"%(self.tpm_id,self.i2c_add)
        self.regs = {
            'CONTROL_B1'        : {'off' : 0x00, 'len' : 1},
            'FAULT_LOG_B1'      : {'off' : 0x04, 'len' : 1},
            'FAULT_LOG'         : {'off' : 0x04, 'len' : 2},
            'ILIM_ADJUST'       : {'off' : 0x11, 'len' : 1},
            'STATUS_B2'         : {'off' : 0x1f, 'len' : 1},
            'EE_SCRATCH_PAD_B1' : {'off' : 0x4c, 'len' : 1},
            'EE_SCRATCH_PAD_B2' : {'off' : 0x4d, 'len' : 1},
            'EE_SCRATCH_PAD_B3' : {'off' : 0x4e, 'len' : 1},
            'EE_SCRATCH_PAD_B4' : {'off' : 0x4f, 'len' : 1},
            'GPIO_CONFIG'       : {'off' : 0x07, 'len' : 1},
            'ALERT'             : {'off' : 0x02, 'len' : 2},
            'ALERT_CONTROL'     : {'off' : 0x1C, 'len' : 1},
        }
        self.gpios = {
            'GPIO3' : {'status_bit_n': 7, 'out_cfg_reg':'GPIO_CONFIG', 'output_cfg_bit': 7, 'direction': 'O', 'use': True},
            'GPIO2' : {'status_bit_n': 6, 'out_cfg_reg':'GPIO_CONFIG', 'output_cfg_bit': 6, 'direction': 'I', 'use': True},
            'GPIO1' : {'status_bit_n': 5, 'out_cfg_reg':'GPIO_CONFIG', 'output_cfg_bit': 5, 'direction': 'U', 'use': False},
            'AlertN': {'status_bit_n': 4, 'out_cfg_reg':'ALERT_CONTROL',  'output_cfg_bit': 6, 'direction': 'O', 'use': True},
        }
        
    def get_name(self):
        return self.name
    
    def read(self,reg):
        # print(self.name, "read", reg)
        if self.regs[reg]['len'] == 2:
            data, status = self.mng.fpgai2c_read16(self.i2c_add, self.regs[reg]['off'], self.i2c_bus)
        else:
            data, status = self.mng.fpgai2c_read8(self.i2c_add, self.regs[reg]['off'], self.i2c_bus)
        if status != 0:
            logger.error(self.name + " Error reading on device " + hex(self.i2c_add))
            return 0xff, status
        # print(self.name, "read", reg, hex(data))
        return data, status
    
    def write(self, reg, data):
        # print(self.name, "write", reg, hex(data))
        if self.regs[reg]['len'] == 2:
            status = self.mng.fpgai2c_write16(self.i2c_add, self.regs[reg]['off'], data, self.i2c_bus)
        else:
            status = self.mng.fpgai2c_write8(self.i2c_add, self.regs[reg]['off'], data, self.i2c_bus)
        if "EE_" in reg:
            wait_finish = True
            retry = 10
            while(wait_finish and retry > 0 ):
                # print("=")
                FAULT_LOG_B1, status = self.read('FAULT_LOG_B1')
                STATUS_B2, status  = self.read('STATUS_B2')
                # print(hex(FAULT_LOG_B1))
                # print(hex(STATUS_B2))
                wait_finish = False
                if (FAULT_LOG_B1 & 0x80) == 0:
                    wait_finish = True
                if (STATUS_B2 & 0x08) > 0:
                    wait_finish = True
                retry -= 1
            if retry == 0:
                logger.error(self.name + " Error writing EE_ on device " + hex(self.i2c_add))
                return -1
            return 0
        else:
            return status


        
    def config_gpio_alert(self):
       #set GPIO 
       self.write('ALERT', 0x0)

    def set_gpio(self,gpio,value):
        if gpio in self.gpios:
            print(gpio)
            if value == 0:
                out_conf_reg,status = self.read(self.gpios[gpio]['out_cfg_reg'])
                data_w=out_conf_reg | (1<<self.gpios[gpio]['output_cfg_bit'])
                print("val 0 data_w = %x" %data_w)
                self.write(self.gpios[gpio]['out_cfg_reg'],data_w)
            else:
                out_conf_reg,status = self.read(self.gpios[gpio]['out_cfg_reg'])
                data_w=out_conf_reg & (( 1 << 8) - 1 - (1 << self.gpios[gpio]['output_cfg_bit']))
                print("val 1 data_w = %x" %data_w)
                self.write(self.gpios[gpio]['out_cfg_reg'],data_w) 


    def get_gpio_status(self):
        result ={}  
        read_data, status = self.read('STATUS_B2')
        for gpios in self.gpios:
            if self.gpios[gpios]['direction'] == 'I' and self.gpios[gpios]['use']:
                result[gpios]=(read_data >>self.gpios[gpios]['status_bit_n'])&0x1
        return result

    def set_alertn_value(self, outval):
        if outval == 1:
            res,state = self.read('ALERT_CONTROL')
            self.write('ALERT_CONTROL',res|0x40)
        elif outval == 0:
            res,state = self.read('ALERT_CONTROL')
            self.write('ALERT_CONTROL',res&0xBF)
        else:
            logger.error("Invalid value, accepted 1 or 0")






        
# mng=MngBoard()
# ## Backplane Board Class
# This class contain methods to permit access to major functionality
# of backplane board from management CPU (iMX6) via registers mapped in filesystem
class Backplane():
    def __init__(self, Management_b, simulation=False, get_board_info = True):
        self.data = []
        self.mng = Management_b
        self.simulation = simulation
        self.eep_sec = eep_sec
        self.power_supply = [LTC428x_dev(x,self.mng) for x in range(1,9)]
        self.ioexpander =[PCF8574_dev(self.mng,x) for x in range (0,2)] 
        self.ps_vout_n = [None]*2
        try:
            data, status = self.power_supply[0].read('CONTROL_B1')
            if status == 0:
                self.bkpln_present = True
            else:
                self.bkpln_present = False
                logger.error("Error BKPLN not present!")
        except:
            self.bkpln_present = False
            logger.error("Error BKPLN not present!")
        self.board_info= None
        if get_board_info:
            self.board_info=self.get_board_info()
        

    def __del__(self):
        self.data = []

    def get_board_info(self):
        mng_info={}
        if not self.bkpln_present:
            mng_info["SN"] = "NA"
            mng_info["PN"] = "NA"    
            return mng_info
        mng_info["SN"] = self.get_field("SN")
        mng_info["PN"] = "BACKPLANE"
        pcb_rev = self.get_field("PCB_REV")
        if pcb_rev == 0xff or pcb_rev == 0x00:
            pcb_rev_string = ""
        else:
            pcb_rev_string = str(pcb_rev)
        hw_rev = self.get_field("HARDWARE_REV")
        mng_info["HARDWARE_REV"] = "v" + str(hw_rev[0]) + "." + str(hw_rev[1]) + "." + str(hw_rev[2]) + pcb_rev_string
        mng_info["CPLD_ip_address_eep"] = self.get_field("ip_address")
        mng_info["CPLD_netmask_eep"] = self.get_field("netmask")
        mng_info["CPLD_gateway_eep"] = self.get_field("gateway")

        return mng_info

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
        _id = (offset // 4)
        reg='EE_SCRATCH_PAD_B%d' % ((offset % 4) + 1)
        data, result = self.power_supply[_id].read(reg)
        return data
        
        
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
            self.eep_rd8(offset, release_lock = True)

    def rd_string(self, partition):
        return self._rd_string(partition["offset"], partition["size"])

    def _rd_string(self, offset, max_len=16):
        addr = offset
        string = ""
        for i in range(max_len):
            byte = self.eep_rd8(addr, release_lock = False)
            if byte == ord("\n") or byte == 0xff or byte == 0x0:
                break
            string += chr(byte)
            addr += 1
        self.eep_rd8(offset, release_lock = True)
        return string
    
    def eep_wr8(self, offset, data, release_lock = True):
        _id = (offset // 4)
        reg='EE_SCRATCH_PAD_B%d' % ((offset % 4) + 1)
        return self.power_supply[_id].write(reg, data)
        

    def eep_wr32(self, offset, data):
        release_lock = False
        for n in range(4):
            if n == 4-1:
                release_lock = True
            self.eep_wr8(offset+n, (data >> 8*(3-n)) & 0xFF,release_lock=release_lock)
        return
    
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
        status = self.power_supply[tpm_id-1].write('FAULT_LOG_B1',0x00)

    # ##pwr_on_tpm
    # This method power on the selected TPM board
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation
    def pwr_on_tpm(self, tpm_id):
        status = self.power_supply[tpm_id-1].write('FAULT_LOG_B1',0x00)
        if status != 0:
            logger.error("Error writing on device " + self.power_supply[tpm_id-1].get_name())
            return status
        status = self.power_supply[tpm_id-1].write('CONTROL_B1',0xBB)  # power on tpm
        # update poweron reg used only for symulation
        if self.simulation is True:
            reg = self.mng.read("Fram.TPM_SUPPLY_STATUS")
            reg = reg | (1 << tpm_id-1)
            self.mng.write("Fram.TPM_SUPPLY_STATUS", reg)
        # end of update sequence
        if status != 0:
            logger.error("Error writing on device " + self.power_supply[tpm_id-1].get_name())
        else:
            if self.is_tpm_on(tpm_id,direct=True):
                status = 0
            else:
                status = 1
        return status

    # ##pwr_off_tpm
    # This method power off the selected TPM board
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation
    def pwr_off_tpm(self, tpm_id):
        status = self.power_supply[tpm_id-1].write('CONTROL_B1',0xB3) # power off tpm
        # update poweron reg used only for symulation
        if self.simulation is True:
            reg = self.mng.read("Fram.TPM_SUPPLY_STATUS")
            reg = reg ^ (1 << (tpm_id - 1))
            self.mng.write("Fram.TPM_SUPPLY_STATUS", reg)
        # end of update sequence
        if status != 0:
            logger.error("Error writing on device " + self.power_supply[tpm_id-1].get_name())
        else:
            if self.is_tpm_on(tpm_id,direct=True) is False:
                status = 0
            else:
                status = 1
        return status

    # ##is_tpm_on
    # This method detect if the selected TPM board power control has powewred on the TPM
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation: True board is turned on, False board is turned off
    def is_tpm_on(self, tpm_id, direct = False):
        if direct:
            value, status = self.power_supply[tpm_id-1].read('CONTROL_B1') # power off tpm
        else:
            value = (self.mng.read("Fram.LTC4281_B%d_control"%tpm_id) >> 8)
        if print_debug:
            logger.debug("is_tpm_on " + hex(value & 0xff))
        if (value & 0xff) == 0xbb:
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
            pwr = round(power, 2)
        else:
            power = self.mng.read("Fram.LTC4281_B"+str(tpm_id)+"_power")
            pwr = float(power*0.04*16.64*65536)/((65535*65535)*0.0025)
            pwr = round(pwr, 2)
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
            vout = round(vout, 2)
        else:
            voltage = self.mng.read("Fram.LTC4281_B"+str(tpm_id)+"_Vsource")
            vout = float(voltage*16.64)/65535
            vout = round(vout, 2)
        if print_debug:
            logger.info("voltage, " + str(vout))
        return vout

    # ##get_pwr_fault_log
    # This method return the selected TPM board power control fault_log register value
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation
    # return data: register value
    def get_pwr_fault_log(self, tpm_id):
        data, status = self.power_supply[tpm_id-1].read('FAULT_LOG')
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
            data, status = self.power_supply[tpm_id-1].read('ILIM_ADJUST')
            
            datatowr = int(data) | (cfg << 5)
            status = self.power_supply[tpm_id-1].write('ILIM_ADJUST', datatowr)
            return status

    # ##pwr_set_ilimt
    # This method get the selected TPM board power control I limit configuration register
    # @param[in] tpm_id: id of the selected tpm (accepted value:1 to 8)
    # return status: status of operation
    # return cfg: actual configuration value
    def pwr_get_ilimt(self, tpm_id):
        data, status = self.power_supply[tpm_id-1].read('ILIM_ADJUST')
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


    def get_ps_present(self, ps_id):
        ioexp_value = self.mng.read("Fram.PSU_ioexp_pre")
        result = bool(ioexp_value & (0b1<<(ps_id-1)))
        if result:
            return False
        return True

    # ####POWER SUPPLY FUNCTIONS
    # This method get the selected power supply status register
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return status_reg: register value
    # return status: status of operation
    def get_ps_status(self, ps_id, key = None):
        if not self.get_ps_present(ps_id):
            result = {
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
            if key is None:
                return result
            return result[key]
        i2c_add = 0xb0+((ps_id-1)*2)
        #status_reg, status = self.mng.fpgai2c_read8(i2c_add, 0x78, FPGA_I2CBUS.i2c3)
        # status_reg, status = self.mng.fpgai2c_read16(i2c_add, 0x79, FPGA_I2CBUS.i2c3)
        status = 0
        status_reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_status")
        if status != 0:
            logger.error("get_ps_status access failed!")
            return None
        result = {
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
        if status_reg != 0:
            logger.error("Error:PSU%d"%ps_id)
            logger.error("status_reg: "+hex(status_reg))
            logger.error("status: "+str(status))
            logger.error(str(result))
            logger.error("Force retry")
            self.get_ps_present(ps_id)
            # status_reg, status = self.mng.fpgai2c_read16(i2c_add, 0x79, FPGA_I2CBUS.i2c3)
            status = 0
            status_reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_status")
            logger.error("status_reg: "+hex(status_reg))
            logger.error("status: "+str(status))
            result = {
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
            logger.error(str(result))
        if key is None:
            return result
        return result[key]

    def get_ps_temp(self, ps_id, temp_id = None):
        if self.get_ps_present(ps_id) != True:
            if temp_id is not None:
                return None
            else:
                return [None]*3
        if temp_id is not None:
            reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_temp"+str(temp_id))
            val = round(_decodePMBus(reg),2)
            return val
        temp_list = []
        # for _add in [ 0x8d, 0x8e, 0x8f ]:
        #     i2c_add = 0xb0+((ps_id-1)*2)
        #     temp_reg, status = self.mng.fpgai2c_read16(i2c_add, _add, FPGA_I2CBUS.i2c3)
        #     temp = float(_decodePMBus(temp_reg))
        #     temp_list.append(temp)
        for temp_id in range(1,4):
            reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_temp"+str(temp_id))
            val = round(_decodePMBus(reg),2)
            temp_list.append(val)
        return temp_list

    def get_ps_vout_mode(self, ps_id):
        if self.get_ps_present(ps_id) != True:
            return 0, 1
        i2c_add = 0xb0+((ps_id-1)*2)
        vout_mode, status = self.mng.fpgai2c_read8(i2c_add, 0x20, FPGA_I2CBUS.i2c3)
        return vout_mode, status

    # This method get the selected power supply vout value evaluated on read from vout register
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return v: vout value
    def get_ps_vout(self, ps_id):
        if self.get_ps_present(ps_id) != True:
            return float('nan')
        status = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Status_Vout")
        if status == 255:
            return 0
        vout = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Vout")
        if self.ps_vout_n[ps_id-1] is None:
            ps_vout_mode,status = self.get_ps_vout_mode(ps_id)
            self.ps_vout_n[ps_id-1] = (twos_comp(ps_vout_mode,5))
        v = float(vout*pow(2, self.ps_vout_n[ps_id-1]))
        v = round(v, 2)
        return v

    # This method get the selected power supply iout value evaluated on read from iout register
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return i: iout value
    # return status: status of operation
    def get_ps_iout(self, ps_id):
        if self.get_ps_present(ps_id) != True:
            return float('nan')
        status = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Status_Iout")
        if status == 255:
            return 0
        reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Iout")
        val = round(_decodePMBus(reg),2)
        return val

    # This method get the selected power supply power value evaluated on read from iout and vout registers
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # return pw: power value
    # return status: status of operation
    def get_ps_power(self, ps_id):
        if self.get_ps_present(ps_id) != True:
            return float('nan')
        pw = self.get_ps_pout(ps_id)
        return pw

    # This method set the fan_spped
    # @param[in] ps_id: id of the selected power supply (accepted values: 1-2)
    # @param[in] speed_cmd: command value (MIN 0=0% - MAX 100=100%, Fan Speed = speed_cmd*21000RPM/100,Write request is
    # executed only if the desired Fanspeed is greater than what is required by the PSU. )
    # return status: status of operation
    def set_ps_fanspeed(self, ps_id, speed_cmd):
        if self.get_ps_present(ps_id) != True:
            return 1
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
        if self.get_ps_present(ps_id) != True:
            return float('nan')
        reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Fan_Speed")
        val = round(_decodePMBus(reg),2)
        return val
    
    def get_ps_vin(self, ps_id):
        if self.get_ps_present(ps_id) != True:
            return 0, 1
        # i2c_add = 0xb0+((ps_id-1)*2)
        # reg, status = self.mng.fpgai2c_read16(i2c_add, 0x88, FPGA_I2CBUS.i2c3)
        reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Vin")
        val = round(_decodePMBus(reg),2)
        return val
    
    def get_ps_iin(self, ps_id):
        if self.get_ps_present(ps_id) != True:
            return 0, 1
        # i2c_add = 0xb0+((ps_id-1)*2)
        # reg, status = self.mng.fpgai2c_read16(i2c_add, 0x89, FPGA_I2CBUS.i2c3)
        reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Iin")
        val = round(_decodePMBus(reg),2)
        return val

    def get_ps_pout(self, ps_id):
        if self.get_ps_present(ps_id) != True:
            return 0, 1
        # i2c_add = 0xb0+((ps_id-1)*2)
        # reg, status = self.mng.fpgai2c_read16(i2c_add, 0x96, FPGA_I2CBUS.i2c3)
        reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Pout")
        val = round(_decodePMBus(reg),2)
        return val
    
    def get_ps_pin(self, ps_id):
        if self.get_ps_present(ps_id) != True:
            return 0, 1
        # i2c_add = 0xb0+((ps_id-1)*2)
        # reg, status = self.mng.fpgai2c_read16(i2c_add, 0x97, FPGA_I2CBUS.i2c3)
        reg = self.mng.read("Fram.PSU"+str(ps_id-1)+"_Pin")
        val = round(_decodePMBus(reg),2)
        return val

    def close(self):
        self.__del__()
