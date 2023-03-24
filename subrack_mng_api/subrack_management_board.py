__author__ = 'Cristian Albanese'
import string
from subprocess import Popen, PIPE
import sys
import os
import time
import calendar
import datetime
from subrack_mng_api.management import *
from subrack_mng_api.backplane import *
from subrack_mng_api.version import *
import logging
from pyfabil.base.definitions import *
from pyfabil.base.utils import ip2long
from pyfabil.boards.tpm_1_6 import TPM_1_6
import serial
#from pyaavs.tile_1_6 import Tile_1_6 as Tile
sys.path.append("../")
import cpld_mng_api.bsp.management as cpld_mng

from optparse import OptionParser



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

TPM_CPLD_REGFILE_BA=0x30000000

subrack_slot_config_file="/etc/SKA/subrack_slot.conf"

PLL_CFG_FILE = "../cpld_mng_api/pll_subrack_OCXO.txt"

def dt_to_timestamp(d):
    return calendar.timegm(d.timetuple())

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


def detect_cpu_ip():
    cmd = "ip address"
    ret = run(cmd)
    lines = ret.splitlines()
    print(lines)
    found = False
    state = 0
    cpu_ip = "255.255.255.255"
    for r in range(0, len(lines)):
        if str(lines[r]).find("inet") != -1:
            # print(lines[r])
            cpu_ip = str(lines[r]).split(" ")[5]
            print("CPU IP:", str(lines[r]).split(" "))
            if cpu_ip.find("10.0.10") != -1:
                cpu_ip = cpu_ip.split("/")[0]
                found = True
                break
    if found is False:
        state = -1
        cpu_ip = "255.255.255.255"
    return state, cpu_ip


def int2ip(value):
    ip = str((value >> 24) & 0xff)
    ip += "."
    ip += str((value >> 16) & 0xff)
    ip += "."
    ip += str((value >> 8) & 0xff)
    ip += "."
    ip += str((value >> 0) & 0xff)
    return ip

def ipstr2hex(ip):
    ip_part = ip.split(".")
    hexip=((int(ip_part[0]) & 0xff) << 24) |\
          ((int(ip_part[1]) & 0xff) << 16) |\
          ((int(ip_part[2]) & 0xff) << 8) | \
          (int(ip_part[3]) & 0xff)
    return hexip

# ##Subrack Management Board Class
# This class implements methods to manage and to monitor the subrack management board
class SubrackMngBoard():
    def __init__(self, **kwargs):
        self._simulation = kwargs.get("simulation")
        self.data = []
        self.Mng = Management(self._simulation)
        self.Bkpln = Backplane(self.Mng, self._simulation)
        ipstr = self.Mng.get_cpld_actual_ip()
        # print("MANAGEMENT creating..")
        self.CpldMng = cpld_mng.MANAGEMENT(ip=ipstr, port="10000", timeout=10)
        # print("MANAGEMENT created")
        self.mode = 0
        self.status = 0
        self.first_config = False
        self.powermon_cfgd = False
        self.tpm_ip_list = []
        self.cpu_ip = ""
        self.__pupolate_tpm_ip_list()
        self.TPM_instances_list = [0, 0, 0, 0, 0, 0, 0, 0]
        self.tpm_plugin_loaded = [False, False, False, False, False, False, False]
        self.__startup()
        self.ser = serial.Serial("/dev/ttymxc0", 9600, timeout=5)    #Open port with baud rate
        self.alarm_l = 12
        self.warning_l = 12
        self.ups_status = {"ups_detected":False,"alarm":False,"warning":False,"charging":False}
        self.ups_present = False
        self.__detect_ups()
        self.ups_charge_regs = []
        self.ups_adc_values = []

    def __del__(self):
        self.data = []

    """
    def mng_eth_cpld_read(self,add):
        cmd="../cpld_mng_api/reg.py --ip " + self.ipstr + " " + hex(add)
        res=run(cmd)
        lines = res.splitlines()
        r = lines[len(lines) - 1]
        print("read val = %s" % r)
        return int(r,16)

    def mng_eth_cpld_write(self,add,val):
        cmd="../cpld_mng_api/reg.py --ip " + self.ipstr + " " + hex(add) + " " + hex(val)
        res=run(cmd)
        lines = res.splitlines()
        r = lines[len(lines) - 1]
        print("read val = %s" % r)
        return int(r,16)
    """
    def __detect_ups(self):
        start = time.time()
        data = self.ser.read(32)
        if len(data) == 0 or (time.time()-start) >= 5:
            self.ups_present = False
        else:
            self.ups_present = True
        self.ups_status["ups_detected"] = self.ups_present



    def __startup(self):
        vecton=self.GetTPMOnOffVect()
        for i in range(0, 8):
            if ((vecton >> i) & 0x1) == 1:
                tpm_ip_str = self.tpm_ip_list[i]
                self.TPM_instances_list[i] = TPM_1_6()
                # port=10000, lmc_ip="10.0.10.1", lmc_port=4660, sampling_rate=800e6
                self.TPM_instances_list[i].connect(ip=tpm_ip_str, port=10000, initialise=False,
                                                               simulation=False, enable_ada=False, fsample=800e6)
                self.TPM_instances_list[i].load_plugin("Tpm_1_6_Mcu")

    def __assign_tpm_ip(self, tpm_slot_id):
        state, cpu_ip = detect_cpu_ip()
        if state != -1:
            tpm_ip_add_h = ipstr2hex(cpu_ip) & 0xFFFFFF00
            cpu_ip_l = ipstr2hex(cpu_ip) & 0xFF
            tpm_ip_add = tpm_ip_add_h | (cpu_ip_l + 6 + tpm_slot_id)
            self.write_tpm_singlewire(tpm_slot_id, 0x40000028, tpm_ip_add)
        else:
            print("Error in CPU IP detection")
            raise SubrackExecFault("Error:TPM Power on Failed")

    def __pupolate_tpm_ip_list(self):
        state, cpu_ip = detect_cpu_ip()
        if state != -1:
            self.cpu_ip = cpu_ip
            tpm_ip_add_h = ipstr2hex(cpu_ip) & 0xFFFFFF00
            cpu_ip_l = ipstr2hex(cpu_ip) & 0xFF
            for i in range(1, 9):
                tpm_add = tpm_ip_add_h | (cpu_ip_l + 6 + i)
                self.tpm_ip_list.append(int2ip(tpm_add))
        else:
            print("Error in CPU IP detection")
            raise SubrackExecFault("Error:TPM Power on Failed")

    def read_tpm_singlewire(self, tpm_id, address):
        self.CpldMng.write_register(0x500, tpm_id - 1)  # select tpm by psnt_mux
        self.CpldMng.write_register(0xA00, 0x30000000)  # set EIM add
        regval = self.CpldMng.read_register(address)
        return regval

    def write_tpm_singlewire(self, tpm_id, address, value):
        self.CpldMng.write_register(0x500, tpm_id - 1)  # select tpm by psnt_mux
        self.CpldMng.write_register(0xA00, 0x30000000)  # set EIM add
        self.CpldMng.write_register(address, value)

    #  ##TPM GET/SET INFO METHODS
    def Get_API_version(self):
        """ method to get the Version of the API
        :return string with API version
        """
        return get_version()

    def Get_Subrack_TimeTS(self):
        """ method to get the subrack Time in timestamp format
        :return time in timestamp format
        """
        tstamp = dt_to_timestamp(datetime.utcnow())
        return tstamp

    def GetTPM_Add_List(self):
        """ method to get the IP address will be assigned to each TPM board present on subrack
        :return list of IP address will be assigned assigned
        """
        if len(self.tpm_ip_list) == 8:
            print("TPM address will be assigned:")
            for i in range(0, 8):
                # tpm_add = (tpm_ip_add_h | (cpu_ip_l + 6 + i))
                print("slot %d -> %s" % (i+1 , self.tpm_ip_list[i]))
            return self.tpm_ip_list
        else:
            print("Error TPM IP list")
            raise SubrackExecFault("Error:TPM IP Add List Incomplete")

    def SetTPMIP(self, tpm_slot_id, ip, netmask):
        """ method to manually set volatile local ip address of a TPM board present on subrack
        :param tpm_slot_id: subrack slot index for selected TPM, accepted value 1-8
        :param ip: ip address will be assigned to selected TPM
        :param netmask: netmask value will be assigned to selected TPM
        :return status
        """
        prev_onoff = 0
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) != 0:
            # if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
            if self.GetTPMOnOffVect() & (1 << (tpm_slot_id-1)) == 0:
                raise SubrackExecFault("Error:TPM is Powered OFF")
        else:
            raise SubrackInvalidCmd("TPM not present")
        self.write_tpm_singlewire(tpm_slot_id, 0x40000028, ipstr2hex(ip))
        self.write_tpm_singlewire(tpm_slot_id, 0x4000002C, ipstr2hex(netmask))
        if self.tpm_ip_list == 8:
            self.tpm_ip_list[tpm_slot_id - 1] = ip
        else:
            print("SetTPMIP ERROR: TPM IP address list incomplete")
            raise SubrackExecFault("Error:TPM IP address list incomplete")

    def GetTPMIP(self,tpm_slot_id):
        """ method to manually set volatile local ip address of a TPM board present on subrack
        :param tpm_slot_id:subrack slot index for selected TPM, accepted value 1-8
        :return tpm_ip_str: tpm ip address
        """
        prev_onoff = 0
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) != 0:
            # if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
            if self.GetTPMOnOffVect() & (1 << (tpm_slot_id-1)) == 0:
                raise SubrackExecFault("Error:TPM is Powered OFF")
        else:
            raise SubrackInvalidCmd("TPM not present")
        tpm_ip = self.read_tpm_singlewire(tpm_slot_id, 0x30000308)
        tpm_ip_str = int2ip(tpm_ip)
        if len(self.tpm_ip_list) == 8:
            if ipstr2hex(self.tpm_ip_list[tpm_slot_id - 1]) != tpm_ip:
                print("GetTPMIP ERROR: TPM IP mismatch with expected list")
                raise SubrackExecFault("Error:TPM IP address mismatch with ip add list")
        else:
            print("GetTPMIP ERROR: TPM IP address list incomplete")
            raise SubrackExecFault("Error:TPM IP address list incomplete")
        logging.info("TPM IP ADD of board in slot %d: %s" % (tpm_slot_id, tpm_ip_str))
        return tpm_ip_str

    def GetTPMInfo(self, tpm_slot_id, forceread=False):
        """ method to get info about TPM board present on subrack
        :param tpm_slot_id:subrack slot index for selected TPM, accepted value 1-8
        :param forceread: force the operation even if no TPM is present in selected slot
        :return TPM_INFO
    """
        prev_onoff = 0
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) != 0:
            # if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
            if self.GetTPMOnOffVect() & (1 << (tpm_slot_id - 1)) == 0:
                if forceread is False:
                    raise SubrackInvalidCmd("TPM is powered off")
                else:
                    if self.Bkpln.get_bkpln_is_onoff() == 0:
                        self.Bkpln.power_on_bkpln()
                        if self.powermon_cfgd is False:
                            self.SubrackInitialConfiguration()
                if self.Bkpln.pwr_on_tpm(tpm_slot_id) != 0:
                    raise SubrackExecFault("Error:TPM Power on Failed")
            else:
                prev_onoff = 1
        else:
            raise SubrackInvalidCmd("TPM not present")
        # tpm_ip = self.read_tpm_singlewire(tpm_slot_id, 0x30000308)
        # tpm_ip_str = int2ip(tpm_ip)
        tpm_ip_str = self.tpm_ip_list[tpm_slot_id - 1]
        state, cpu_ip = detect_cpu_ip()
        if state != -1:
            # logging.info("TPM IP: %s, CPU IP: %s" %(tpm_ip,subrack_cpu_ip))
            logging.info("TPM IP: %s" % tpm_ip_str)
            # tpm = TPM_1_6()
            # tpm.connect(ip=tpm_ip_str, port=10000, initialise=False, simulation=False, enable_ada=False, fsample=800e6)
            tpm = self.TPM_instances_list[tpm_slot_id -1]
            tpm_info = tpm.get_board_info()
            if prev_onoff == 0:
                if self.Bkpln.pwr_off_tpm(tpm_slot_id)!=0:
                    raise SubrackExecFault("Error:TPM Power on Failed")
            # logging.info(tpm_info)
            return tpm_info
        else:
            print ("Error in CPU IP detection")
            raise SubrackExecFault("Error:TPM Power on Failed")

    def GetTPMGlobalStatusAlarm(self, tpm_slot_id, forceread=False):
        """method to get Global Status Register of  TPM selected board present on subrack
        :param tpm_slot_id subrack slot index for selected TPM, accepted value 1-8
        :param forceread: force the operation even if no TPM is present in selected slot
        :return alarms: OK, WARN, ALARM, WARN-ALARM {temperature_alarm,viltage_alarm,MCU watchdog, SEM watcdog}
        """
        prev_onoff = 0
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) != 0:
            # if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
            if self.GetTPMOnOffVect() & (1 << (tpm_slot_id - 1)) == 0:
                if forceread is False:
                    raise SubrackInvalidCmd("TPM is OFF and read isn't forced ")
                else:
                    if self.Bkpln.get_bkpln_is_onoff() == 0:
                        self.Bkpln.power_on_bkpln()
                        if self.powermon_cfgd is False:
                            self.SubrackInitialConfiguration()
                if self.Bkpln.pwr_on_tpm(tpm_slot_id) != 0:
                    # raise SubrackExecFault("Error:TPM Power on Failed")
                    print ("Error:TPM Power on Failed")
                    return 1
            else:
                prev_onoff = 1
        else:
            # raise SubrackInvalidCmd("TPM not present")
            print("ERROR: TPM not present")
            return 1
        # tpm_ip = self.read_tpm_singlewire(tpm_slot_id, 0x30000308)
        # tpm_ip_str = int2ip(tpm_ip)
        tpm_ip_str = self.tpm_ip_list[tpm_slot_id - 1]
        # tpm = TPM_1_6()
        # tpm.connect(ip=tpm_ip_str, port=10000,  initialise=False, simulation=False, enable_ada=False, fsample=800e6)
        tpm = self.TPM_instances_list[tpm_slot_id - 1]
        global_status = tpm.get_global_status_alarms()
        # tpm.disconnect()
        # global_status = self.read_tpm_singlewire(tpm_slot_id, 0x30000500)
        print("Global status: ", global_status)
        if prev_onoff == 0:
            if self.Bkpln.pwr_off_tpm(tpm_slot_id) != 0:
                raise SubrackExecFault("Error:TPM Power off Failed")
        return global_status

    def Get_tpm_alarms_vector(self):
        """method to get temperature and voltage alarm status of all TPMS presents and powered ON
        :return tpm_temp_alarm_status_vect,tpm_voltage_alarm_status_vect arrays with status of alarms temperature and
        voltages of each TPM, each field can be 0 OK, 01 Warning, 02 alarm, 03 warning then alarm, 04 board Not present or not powered
        """
        tpm_temp_alarm_status_vect = []
        tpm_voltage_alarm_status_vect = []
        for slot in range (1,9):
            if self.GetTPMPresent() & (1 << (slot - 1)) != 0:
                if self.GetTPMOnOffVect() & (1 << (slot - 1)) == 0:
                    tpm_temp_alarm_status_vect.append(0x4)
                    tpm_voltage_alarm_status_vect.append(0x4)
                else:
                    tpm_ip_str = self.tpm_ip_list[slot - 1]
                    # tpm = TPM_1_6()
                    # tpm.connect(ip=tpm_ip_str, port=10000, initialise=False, simulation=False, enable_ada=False,
                    #            fsample=800e6)
                    tpm = self.TPM_instances_list[slot - 1]
                    global_status = tpm.get_global_status_alarms()
                    # tpm.disconnect()
                    tpm_temp_alarm_status_vect.append(global_status["temperature_alm"])
                    tpm_voltage_alarm_status_vect.append(global_status["voltage_alm"])
            else:
                tpm_temp_alarm_status_vect.append(0x4)
                tpm_voltage_alarm_status_vect.append(0x4)
        return tpm_temp_alarm_status_vect, tpm_voltage_alarm_status_vect


    def GetTPMTemperatures(self, tpm_slot_id, forceread=False):
        """method to get temperature of onboard TPM selected board present on subrack
        :param tpm_slot_id subrack slot index for selected TPM, accepted value 1-8
        :param forceread: force the operation even if no TPM is present in selected slot
        :return tpm_board_temperature,tpm_fpga0_temp, tpm_fpga1_temp(if fpga is not programmed return fpga_temp =0)
        """
        # print("GetTPMTemperatures %d"%tpm_slot_id)
        prev_onoff = 0
        pres_tpm = self.GetTPMPresent()
        #print("TPM Present: %x" %pres_tpm)
        if pres_tpm & (1 << (tpm_slot_id-1)) != 0:
            # if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
            if self.GetTPMOnOffVect() & (1 << (tpm_slot_id - 1)) == 0:
                if forceread is False:
                    raise SubrackInvalidCmd("TPM is OFF and read isn't forced ")
                else:
                    if self.Bkpln.get_bkpln_is_onoff() == 0:
                        self.Bkpln.power_on_bkpln()
                        if self.powermon_cfgd is False:
                            self.SubrackInitialConfiguration()
                if self.Bkpln.pwr_on_tpm(tpm_slot_id) != 0:
                    #raise SubrackExecFault("Error:TPM Power on Failed")
                    print ("Error:TPM Power on Failed")
                    return -1
            else:
                prev_onoff = 1
        else:
            # raise SubrackInvalidCmd("TPM not present")
            print("ERROR: TPM not present")
            return -1
        # tpm_ip = self.read_tpm_singlewire(tpm_slot_id, 0x30000308)
        # tpm_ip_str = int2ip(tpm_ip)
        tpm_ip_str = self.tpm_ip_list[tpm_slot_id - 1]
        #tpm = TPM_1_6()
        #port=10000, lmc_ip="10.0.10.1", lmc_port=4660, sampling_rate=800e6
        #tpm.connect(ip=tpm_ip_str, port=10000,  initialise=False, simulation=False, enable_ada=False, fsample=800e6)
        #tpm.load_plugin("Tpm_1_6_Mcu")
        tpm = self.TPM_instances_list[tpm_slot_id-1]
        temp_mcu_f = 0
        temp_board_f = 0
        temp_fpga1_f = 0
        temp_fpga2_f = 0
        if tpm != 0:
            temp_mcu_f = tpm.tpm_monitor[0].get_mcu_temperature()
            temp_board_f = tpm.tpm_monitor[0].get_temperature()
            if tpm.is_programmed():
                if self.tpm_plugin_loaded[tpm_slot_id-1] is False:
                    tpm.load_plugin("TpmSysmon", device=Device.FPGA_1)
                    tpm.load_plugin("TpmSysmon", device=Device.FPGA_2)
                    self.tpm_plugin_loaded[tpm_slot_id - 1] = True
                else:
                    temp_fpga1_f = tpm.tpm_sysmon[0].get_fpga_temperature()
                    temp_fpga2_f = tpm.tpm_sysmon[1].get_fpga_temperature()
            temp_fpga1_f = round(temp_fpga1_f, 2)
            temp_fpga2_f = round(temp_fpga2_f, 2)
            #tpm.disconnect()
            if prev_onoff == 0:
                if self.Bkpln.pwr_off_tpm(tpm_slot_id) != 0:
                    raise SubrackExecFault("Error:TPM Power off Failed")
        return temp_mcu_f, temp_board_f, temp_fpga1_f, temp_fpga2_f


    def Get_TPM_temperature_vector(self):
        """method to get temperature of all TPMS presents and powered ON
        :return tpm_temp_board_vect, tpm_temp_fpga1_vect, tpm_temp_fpga2_vect arrays with temperature of each TPM, each
        field can be a temperature value or -256  board Not present or not powered
        """
        tpm_temp_board_vect = []
        tpm_temp_fpga1_vect = []
        tpm_temp_fpga2_vect = []
        for slot in range (1,9):
            if self.GetTPMPresent() & (1 << (slot - 1)) != 0:
                if self.GetTPMOnOffVect() & (1 << (slot - 1)) == 0:
                    tpm_temp_board_vect.append(-256)
                    tpm_temp_fpga1_vect.append(-256)
                    tpm_temp_fpga2_vect.append(-256)
                else:
                    temp_board_f, temp_fpga1_f, temp_fpga2_f = self.GetTPMTemperatures(slot)
                    tpm_temp_board_vect.append(temp_board_f)
                    tpm_temp_fpga1_vect.append(temp_fpga1_f)
                    tpm_temp_fpga2_vect.append(temp_fpga2_f)
            else:
                tpm_temp_board_vect.append(-256)
                tpm_temp_fpga1_vect.append(-256)
                tpm_temp_fpga2_vect.append(-256)
        return tpm_temp_board_vect, tpm_temp_fpga1_vect, tpm_temp_fpga2_vect


    def GetTPMMCUTemperature(self, tpm_slot_id, forceread=False):
        """method to get temperature of MCU on TPM selected board present on subrack
        :param tpm_slot_id subrack slot index for selected TPM, accepted value 1-8
        :param forceread: force the operation even if no TPM is present in selected slot
        :return temp_mcu_f tpm mcu temperature
        """
        prev_onoff = 0
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) != 0:
            # if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
            if self.GetTPMOnOffVect() & (1 << (tpm_slot_id - 1)) == 0:
                if forceread is False:
                    raise SubrackInvalidCmd("TPM is OFF and read isn't forced ")
                else:
                    if self.Bkpln.get_bkpln_is_onoff() == 0:
                        self.Bkpln.power_on_bkpln()
                        if self.powermon_cfgd == False:
                            self.SubrackInitialConfiguration()
                if self.Bkpln.pwr_on_tpm(tpm_slot_id) != 0:
                    #raise SubrackExecFault("Error:TPM Power on Failed")
                    print ("Error:TPM Power on Failed")
                    return 1
            else:
                prev_onoff = 1
        else:
            #raise SubrackInvalidCmd("TPM not present")
            print("ERROR: TPM not present")
            return 1
        # tpm_ip = self.read_tpm_singlewire(tpm_slot_id, 0x30000308)
        # tpm_ip_str = int2ip(tpm_ip)
        tpm_ip_str = self.tpm_ip_list[tpm_slot_id - 1]
        #tpm = TPM_1_6()
        #tpm.connect(ip=tpm_ip_str, port=10000, initialise=False, simulation=False, enable_ada=False, fsample=800e6)
        #tpm.load_plugin("Tpm_1_6_Mcu")
        tpm = self.TPM_instances_list[tpm_slot_id - 1]
        temp_mcu_f = tpm.tpm_monitor[0].get_mcu_temperature()
        if prev_onoff == 0:
            if self.Bkpln.pwr_off_tpm(tpm_slot_id) != 0:
                raise SubrackExecFault("Error:TPM Power off Failed")
        return temp_mcu_f


    def SubrackInitialConfiguration(self):
        """ SubrackInitialConfiguration
        @brief method Initizlize the Subrack power control configuration for TPM current limit
        """
        self.mode = "INIT"
        print("Config TPM's Power monitor to config 5")
        for i in range(1, 9):
            self.Bkpln.pwr_set_ilimt(i, 5)
        self.powermon_cfgd = True

    def get_subrack_cpu_cpld_ip(self):
        """ SubrackInitialConfiguration
        @brief method Initizlize the Subrack power control configuration for TPM current limit
        :return cpu_ip, cpld_ip: Management CPU IP, Management CPLD IP
        """
        status, cpu_ip = detect_cpu_ip()
        cpld_ip = self.Mng.get_cpld_actual_ip()
        return cpu_ip, cpld_ip

    def GetTPMPresent(self):
        """brief method to get info about TPM board present on subrack
        :return TpmDetected: vector of tpm positional,1 TPM detected,0 no TPM inserted,bit 7:0,bit 0 slot 1,bit 7 slot 8
        """
        TpmDetected = self.Mng.get_housekeeping_flag("TPMsPresent")
        TpmDetected = self.Mng.get_housekeeping_flag("TPMsPresent")
        return TpmDetected

    def GetTPMOnOffVect(self):
        """method to get Power On status of inserted tpm, 0 off or not present, 1 power on
        :return vector of poweron status for slots, bits 7:0, bit 0 slot 1, bit 7 slot 8, 1 TPM power on, 0 no TPM
        inserted or power off
        """
        reg = self.Mng.read("Fram.TPM_SUPPLY_STATUS")
        tpmison_vect = reg & 0xff
        return tpmison_vect

    def GetTPMSupplyFault(self):
        """ Method to get info about TPM supply fault status, 1 for each TPM in backplane slot
        :return tpmsupplyfault: vector of tpm supply fault status, 1 fault, 0 no fault,bit 7:0,bit 0 slot 1,bit 7 slot 8
        """
        reg = self.Mng.read("Fram.TPM_SUPPLY_STATUS")
        tpmsupplyfault = (reg & 0xff00) >> 8
        return tpmsupplyfault

    def GetTPMPower(self, tpm_slot_id, force=True):
        """ method to get power consumption of selected tpm (providing subrack index slot of tpm)
        :param tpm_slot_id: subrack slot index for selected TPM, accepted value 1-8
        :param force force the operation even if no TPM is present in selected slot
        """
        if (self.GetTPMPresent() & (1 << (tpm_slot_id-1))) != 0 or force:
            pwr = self.Bkpln.get_power_tpm(tpm_slot_id)
            return pwr
        else:
            raise SubrackInvalidCmd("Impossible to get Power Value, TPM is not present")

    def GetTPMCurrent(self, tpm_slot_id, force=True):
        """method to get current consuptin of selected tpm (providing subrack index slot of tpm)
        :param tpm_slot_id: subrack slot index for selected TPM, accepted value 1-8
        :param force: force the operation even if no TPM is present in selected slot
        """
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) != 0 or force:
            pwr = self.Bkpln.get_power_tpm(tpm_slot_id)
            volt = self.Bkpln.get_voltage_tpm(tpm_slot_id)
            if volt == 0:
                volt = self.Bkpln.get_voltage_tpm(tpm_slot_id)
                curr = 0
            else:
                curr = float(pwr/volt)
            curr = round(curr, 3)
            return curr
        else:
            raise SubrackInvalidCmd("Impossible to get Power Value, TPM is not present")

    def GetTPMVoltage(self, tpm_slot_id, force=True):
        """brief method to get power consuptin of selected tpm (providing subrack index slot of tpm)
        :param  tpm_slot_id:subrack slot index for selected TPM, accepted value 1-8
        :param force: force the operation even if no TPM is present in selected slot
        """
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) != 0 or force:
            volt = self.Bkpln.get_voltage_tpm(tpm_slot_id)
            return volt
        else:
            raise SubrackInvalidCmd("Impossible to get Voltage Value, TPM is not present")

    def GetSubrackTemperatures(self):
        """method to get temperatures from sensors placed on backplane and subrack-management boards
        :return temp_mng1: temperature value of management sensor 1
        :return temp_mng2: temperature value of management sensor 2
        :return temp_bck1: temperature value of backplane sensor 1
        :return temp_bck2: temperature value of backplane sensor 2
        """
        temp_mng1 = self.Mng.GetMngTemp(1)
        temp_mng2 = self.Mng.GetMngTemp(2)
        temp_bck1, stat1 = self.Bkpln.get_sens_temp(1)
        temp_bck2, stat2 = self.Bkpln.get_sens_temp(2)
        return temp_mng1, temp_mng2, temp_bck1, temp_bck2

    def PowerOnTPM(self, tpm_slot_id, force=False):
        """method to power on selected tpm
        :param  tpm_slot_id: subrack slot index for selected TPM, accepted value 1-8
        :param force: force the operation even if no TPM is present in selected slot
        """
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) == 0:
            logging.error("ERROR: TPM not present in selected slot")
            if force is True:
                if self.Bkpln.get_bkpln_is_onoff() == 0:
                    self.Bkpln.power_on_bkpln()
                    if self.powermon_cfgd is False:
                        self.SubrackInitialConfiguration()
                self.Bkpln.pwr_on_tpm(tpm_slot_id)
                self.__assign_tpm_ip(tpm_slot_id)
            else:
                raise SubrackExecFault("ERROR: TPM not present in selected slot")
        else:
            if self.Bkpln.get_bkpln_is_onoff() == 0:
                self.Bkpln.power_on_bkpln()
                if self.powermon_cfgd is False:
                    self.SubrackInitialConfiguration()
            if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
                if self.Bkpln.pwr_on_tpm(tpm_slot_id):
                    logging.error("Power TPM on slot %d failed" % tpm_slot_id)
                    raise SubrackExecFault("ERROR: power on TPM command failed")
                else:
                    time.sleep(2)
                    self.__assign_tpm_ip(tpm_slot_id)
                    time.sleep(2)
                    tpm_ip_str = self.tpm_ip_list[tpm_slot_id - 1]
                    self.TPM_instances_list[tpm_slot_id-1] = TPM_1_6()
                    # port=10000, lmc_ip="10.0.10.1", lmc_port=4660, sampling_rate=800e6
                    self.TPM_instances_list[tpm_slot_id-1].connect(ip=tpm_ip_str, port=10000, initialise=False,
                                                                   simulation=False, enable_ada=False, fsample=800e6)
                    self.TPM_instances_list[tpm_slot_id-1].load_plugin("Tpm_1_6_Mcu")



    def PowerOffTPM(self, tpm_slot_id, force = False):
        """method to power off selected tpm
        :param  tpm_slot_id: subrack slot index for selected TPM, accepted value 1-8
        :param force: force the operation even if no TPM is present in selected slot
        """
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) == 0:
            logging.error("ERROR: TPM not present in selected slot")
            if force is True:
                self.Bkpln.pwr_off_tpm(tpm_slot_id)
            else:
                raise SubrackExecFault("ERROR: TPM not present in selected slot")
        else:
            if self.Bkpln.is_tpm_on(tpm_slot_id) is True:
                self.TPM_instances_list[tpm_slot_id - 1].disconnect()
                self.tpm_plugin_loaded[tpm_slot_id -1] = False
                if self.Bkpln.pwr_off_tpm(tpm_slot_id):
                    logging.error("Power TPM off slot %d failed" % tpm_slot_id)
                    raise SubrackExecFault("ERROR: power off TPM command failed")

    def SetFanSpeed(self, fan_id, speed_pwm_perc):
        """This method set the_bkpln_fan_speed
        :param fan_id: id of the selected fan accepted value: 1-4
        :param speed_pwm_perc: percentage value of fan RPM  (MIN 0=0% - MAX 100=100%)
        :note settings of fan speed is possible only if fan mode is manual
        """
        status = self.Bkpln.set_bkpln_fan_speed(fan_id, speed_pwm_perc)
        if status == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        elif status == 2:
            raise SubrackExecFault("ERROR: Command Failed FanMode must be Manual!!")
        elif status > 0:
            raise SubrackExecFault("ERROR: Command Failed unexpected status")

    def GetFanSpeed(self, fan_id):
        """This method get the get_bkpln_fan_speed
        :param fan_id: id of the selected fan accepted value: 1-4
        :return fanrpm: fan rpm value
        :return fan_bank_pwm: pwm value of selected fan
        """
        rpm, pwm_perc, status = self.Bkpln.get_bkpln_fan_speed(fan_id)
        # print ("rpm %d, pwm_perc %d" %(rpm,pwm_perc))
        if status == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        return rpm, pwm_perc

    def SetFanMode(self, fan_id_blk, auto_mode):
        """This method set the fan mode
        :param fan_id_blk: id of the fan cuople accepted value: 1-4, for fan 1,2; 3 for fan 3,4
        :param auto_mode: fan mode configuration, 1 auto(controlled by MCU), 0 manual(use SetFanSpeed method)
        :note fan are coupled, passing fan_blk_id=1 both fan 1 and 2 will be configured at same mode,
        """
        if self.Bkpln.set_bkpln_fan_mode(fan_id_blk, auto_mode) == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")

    def GetFanMode(self, fan_id):
        """This method get the_bkpln_fan_mode
        :param fan_id: id of the selected fan accepted value: 1-4
        :return auto_mode: functional fan mode: auto or manual
        :return status: status of operation
        """
        auto_mode, status = self.Bkpln.get_bkpln_fan_mode(fan_id)
        # print("auto_mode %d, status %d" % (auto_mode, status))
        if status == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        return auto_mode

    def PllInitialize(self, pll_cfg_file=None):
        """This method initialize the PLL"""
        if self._simulation is False:
            if pll_cfg_file is not None:
                self.CpldMng.pll_ldcfg(pll_cfg_file)
            else:
                self.CpldMng.pll_ldcfg(PLL_CFG_FILE)
            self.CpldMng.pll_calib()
            self.CpldMng.pll_ioupdate()
            time.sleep(0.5)
            #rd=hex(self.CpldMng.read_spi(0x3001))
            rd = hex(self.CpldMng.pll_read_with_update(0x3001))
            print ("PLL lock reg: %s" % rd)
            if rd != "0x33":
                print ("ERROR: PLL configuration failed, PLL not locked")
            # raise SubrackExecFault("ERROR: PLL configuration failed, PLL not locked")
        else:
            r = "0x33"
            print("pll res = %s" % r)
            if r != "0x33":
                print ("ERROR: PLL configuration failed, PLL not locked")
        """
        if self._simulation==False:
            ipstring=self.Mng.get_cpld_actual_ip()
            cmd = "bash ./pll_cfg.sh "+ ipstring
            print (cmd)
            res=run(cmd)
            lines=res.splitlines()
            r=lines[len(lines)-1]
            print("pll res = %s" %r)
            if (r!="0x33"):
                if (str(r) != "b'0x33'"):
                    print ("ERROR: PLL configuration failed, PLL not locked")
            # raise SubrackExecFault("ERROR: PLL configuration failed, PLL not locked")
        else:
            r = "0x33"
            print("pll res = %s" % r)
            if r != "0x33":
                print ("ERROR: PLL configuration failed, PLL not locked")
        """

    def GetLockedPLL(self):
        """This method get the status of the PLL Lock
        :return locked: value of locked status, True PLL is locked, False PLL not locked
        """
        #rd = hex(self.CpldMng.read_spi(0x3001))
        rd = hex(self.CpldMng.pll_read_with_update(0x3001))
        #print("PLL lock reg: %s" % rd)
        if rd != "0x33":
            #print("PLL not locked")
            return False
        else:
            #print("PLL locked")
            return True

    def GetCPLDLockedPLL(self):
        """This method get the status of the CPLD internal PLL Lock
        :return locked: value of locked status, True PLL is locked, False PLL not locked
        """
        rd = hex(self.CpldMng.read_register(0xC))
        #print("PLL CPLD lock reg: %s" % rd)
        if (int(rd, 16) & 0x1) != 0x1:
            #print("PLL not locked")
            return False
        else:
            #print("PLL locked")
            return True

    # #UPS SECTION
    def SetUPSVoltageAlarmThresholds(self,alarm_level):
        error = 0
        if self.ups_present:
            if alarm_level < self.warning_l:
                self.alarm_l = alarm_level
            else:
                error += 1
        return error

    def SetUPSVoltageWarningThresholds(self,warning_level):
        error = 0
        if self.ups_present:
            if warning_level > self.alarm_l:
                self.warning_l = warning_level
            else:
                error += 1
        return error

    def GetUPSStatus(self):
        if self.ups_present:
            received = False

            timeout = False
            while (received is False) and (timeout is False):
                start = time.time()
                receive_data = self.ser.read(32)  # read serial port
                print("Received Data", receive_data)
                end = time.time()
                receive_data = self.ser.read(32)  # read serial port
                print("Received Data", receive_data)
                end = time.time()
                if end - start >= 5:
                    timeout = True
                if receive_data[0] == 73:
                    print("Update Ups Charge Regs")
                    self.ups_charge_regs = {
                        "charger_status": int.from_bytes(receive_data[1:3], byteorder='big'),  # .encode('hex'),
                        "charging_curr": int.from_bytes(receive_data[4:6], byteorder='big'),  # .encode('hex'),
                        "charging_volt": int.from_bytes(receive_data[7:9], byteorder='big'),  # .encode('hex'),
                        "alarm_warning": int.from_bytes(receive_data[10:12], byteorder='big'),  # .encode('hex'),
                        "bbu_status": int.from_bytes(receive_data[13:15], byteorder='big'),  # .encode('hex'),
                        "bbu_control": int.from_bytes(receive_data[16:18], byteorder='big')  # .encode('hex')
                    }
                    received = True
                    print(self.ups_charge_regs)
                    if receive_data[19] == 65:
                        print("Update Ups ADC Values")
                        self.ups_adc_values = {
                            "power_in": round((int.from_bytes(receive_data[20:22], byteorder='big') * 15.24 * 0.8), 2),
                            "vin_sht": round((int.from_bytes(receive_data[23:25], byteorder='big') * 15.24 * 0.8), 2),
                            "vin": round((int.from_bytes(receive_data[26:28], byteorder='big') * 15.24 * 0.8), 2),
                            "man_5v0": round((int.from_bytes(receive_data[29:31], byteorder='big') * 0.8 * 15.24), 2)
                        }
                        received = True
                        print(self.ups_adc_values)
                if timeout is False:
                    if self.ups_adc_values["vin"] < (self.warning_l*1000):
                        self.ups_status["warning"] = True
                    else:
                        self.ups_status["warning"] = False
                    if self.ups_adc_values["vin"] < (self.alarm_l * 1000):
                        self.ups_status["alarm"] = True
                    else:
                        self.ups_status["alarm"] = False
                        """
                        if self.ups_adc_values["vin"] <= self.alarm_l*1000:
                            self.ups_status["alarm"] = True
                            self.ups_status["warning"] = True
                        else:
                            self.ups_status["alarm"] = False
                            self.ups_status["warning"] = True
                        """
                    if self.ups_charge_regs["charger_status"] == 0xc010:
                        self.ups_status["charging"] = True
                    else:
                        self.ups_status["charging"] = False
                else:
                    print("TIMEOUT")
            return self.ups_status

    # #POWER SUPPLIES SECTION
    def GetPSVout(self, ps_id):
        """This method get the Vout voltage value of selected Power Supply of subrack
        :param ps_id: id of the selected power supply, accepted value: 1,2
        :return vout: value of Vout in Volt
        """
        if ps_id > 2 or ps_id < 0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        vout = self.Bkpln.get_ps_vout(ps_id)
        return vout

    def GetPSIout(self, ps_id):
        """This method get the Iout current value of selected Power Supply of subrack
        :param ps_id: id of the selected power supply, accepted value: 1,2
        :return vout: value of Iout in Ampere
        """
        if ps_id > 2 or ps_id < 0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        vout = self.Bkpln.get_ps_iout(ps_id)
        return vout

    def GetPSPower(self, ps_id):
        """This method get the Power consumption value of selected Power Supply of subrack
        :param ps_id: id of the selected power supply, accepted value: 1,2
        :return power: value of power in W
        """
        if ps_id > 2 or ps_id < 0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        power = self.Bkpln.get_ps_power(ps_id)
        return power

    def GetPSFanSpeed(self, ps_id):
        """This method get the fan speed of selected Power Supply of subrack
        :param ps_id: id of the selected power supply, accepted value: 1,2
        :return fanspeed: speed of the fan
        """
        if ps_id > 2 or ps_id < 0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        fanspeed, status = self.Bkpln.get_ps_fanspeed(ps_id)
        if status != 0:
            raise SubrackExecFault("ERROR: Get PS Fan speed operation failed")
        else:
            return fanspeed

    def SetPSFanSpeed(self, ps_id, speed_percent):
        """This method set the fan speed of selected Power Supply of subrack
        :param ps_id: id of the selected power supply, accepted value: 1,2
        :param speed_percent: speed in percentual value from 0 to 100
        """
        if ps_id > 2 or ps_id < 0:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        status = self.Bkpln.set_ps_fanspeed(ps_id, speed_percent)
        if status != 0:
            raise SubrackExecFault("ERROR: Set PS Fan speed operation failed")

    def GetFanAlarm(self):
        """method to get Fan Status Alarm Register of subrack
        :return alarms: OK, WARN, ALARM, WARN-ALARM, of each Fan
        """

    def GetVoltageAlarm(self):
        """method to get TPM Voltages Power supply Alarm Register of subrack
        :return alarms: status vector, OK, WARN, ALM of each TPM Voltages Alarm, for each board
        """

    def GetPowerAlarm(self):
        """method to get TPM Power consumption Alarm Register of subrack
        :return alarms: status vector, OK, WARN, ALM of each TPM Voltages Alarm, for each board
        """

    def close(self):
        self.__del__()
