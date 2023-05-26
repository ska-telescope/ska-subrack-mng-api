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
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

from subrack_monitoring_point_lookup import load_subrack_lookup

from optparse import OptionParser
import Pyro5.api

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

logger=logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.INFO)

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

PLL_CFG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),"../cpld_mng_api/pll_subrack_OCXO.txt"))
PLL_CFG_FILE_INTERNAL = os.path.abspath(os.path.join(os.path.dirname(__file__),"../cpld_mng_api/pll_subrack_OCXO_generate_internal.txt"))

def dt_to_timestamp(d):
    return calendar.timegm(d.timetuple())

def detect_ip(tpm_slot_id):
    try:
        f = open(subrack_slot_config_file, "r")
    except:
        logger.debug("Configuration File not Found")
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
@Pyro5.api.expose
class SubrackMngBoard():
    def __init__(self, **kwargs):
        logger.info("SubrackMngBoard init ...")
        self._simulation = kwargs.get("simulation")
        self.data = []
        logger.debug("Mng creating..")
        self.Mng = Management(self._simulation)
        logger.debug("Bkpln creating..")
        self.Bkpln = Backplane(self.Mng, self._simulation)
        self.CpldMng = self.Mng.CpldMng
        # logger.debug("MANAGEMENT created")
        self.mode = 0
        self.status = 0
        self.first_config = False
        self.powermon_cfgd = os.path.exists("/run/lock/subrack_management_board_powermon_cfgd")
        self.tpm_ip_list = []
        self.cpu_ip = ""
        self.__populate_tpm_ip_list()
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
        if self.Mng.read('HKeep.PPSMux') == 3:
            logger.warning("PllInitialize internal source configured")
            self.pll_lock_exp_rd = 0x03
        else:
            logger.info("PllInitialize external source configured")
            self.pll_lock_exp_rd = 0x33
        self.monitoring_point_lookup_dict = load_subrack_lookup(self)
        logger.info("SubrackMngBoard init done!")

    def __del__(self):
        self.data = []

    def Initialize(self,pll_source_internal=False):
        logger.info("SUBRACK initialize start ...")
        self.Mng.set_SFP()
        self.PllInitialize(source_internal=pll_source_internal)
        # power on the backplane
        if self.Bkpln.get_bkpln_is_onoff() == 0:
            self.Bkpln.power_on_bkpln()
        if self.powermon_cfgd == False:
            self.SubrackInitialConfiguration()
        logger.info("SUBRACK initialize done.")
    """
    def mng_eth_cpld_read(self,add):
        cmd="../cpld_mng_api/reg.py --ip " + self.ipstr + " " + hex(add)
        res=run(cmd)
        lines = res.splitlines()
        r = lines[len(lines) - 1]
        logger.debug("read val = %s" % r)
        return int(r,16)

    def mng_eth_cpld_write(self,add,val):
        cmd="../cpld_mng_api/reg.py --ip " + self.ipstr + " " + hex(add) + " " + hex(val)
        res=run(cmd)
        lines = res.splitlines()
        r = lines[len(lines) - 1]
        logger.debug("read val = %s" % r)
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
        logger.warning("__startup")
        vecton=self.GetTPMOnOffVect()
        for i in range(0, 8):
            tpm_slot_id = i + 1
            if ((vecton >> i) & 0x1) == 1:
                actual_tpm_ip_str = self.GetTPMIP(tpm_slot_id)
                tpm_ip_str = self.tpm_ip_list[i]
                if actual_tpm_ip_str != tpm_ip_str:
                    logger.warning("Found TPM in SLOT-%d with unexpected ip address"%tpm_slot_id)
                    logger.warning("expecetd %s, got %s"%(tpm_ip_str,actual_tpm_ip_str))
                    time.sleep(2)
                    self.__assign_tpm_ip(tpm_slot_id)
                    time.sleep(2)
                try:
                    self.TPM_instances_list[i] = TPM_1_6()
                    # port=10000, lmc_ip="10.0.10.1", lmc_port=4660, sampling_rate=800e6
                    self.TPM_instances_list[i].connect(ip=tpm_ip_str, port=10000, initialise=False,
                                                                simulation=False, enable_ada=False, fsample=800e6)
                    self.TPM_instances_list[i].load_plugin("Tpm_1_6_Mcu")
                except LibraryError:
                    logger.warning("Exception during TPM connection at SLOT-%d, try power cycle"%tpm_slot_id)
                    self.PowerOffTPM(tpm_slot_id)
                    self.PowerOnTPM(tpm_slot_id)
                    pass

    def __assign_tpm_ip(self, tpm_slot_id):
        cpu_ip, netmask, gateway = self.Mng.detect_cpu_ip()
        if cpu_ip is not None:
            tpm_ip_add_h = ipstr2hex(cpu_ip) & 0xFFFFFF00
            cpu_ip_l = ipstr2hex(cpu_ip) & 0xFF
            tpm_ip_add = tpm_ip_add_h | (cpu_ip_l + 6 + tpm_slot_id)
            self.SetTPMIP(tpm_slot_id,int2ip(tpm_ip_add),netmask,gateway)
        else:
            logger.debug("Error in CPU IP detection")
            raise SubrackExecFault("Error:TPM Power on Failed")

    def __populate_tpm_ip_list(self):
        cpu_ip, netmask, gateway = self.Mng.detect_cpu_ip()
        if cpu_ip is not None:
            self.cpu_ip = cpu_ip
            tpm_ip_add_h = ipstr2hex(cpu_ip) & 0xFFFFFF00
            cpu_ip_l = ipstr2hex(cpu_ip) & 0xFF
            for i in range(1, 9):
                tpm_add = tpm_ip_add_h | (cpu_ip_l + 6 + i)
                self.tpm_ip_list.append(int2ip(tpm_add))
        else:
            logger.debug("Error in CPU IP detection")
            raise SubrackExecFault("Error:TPM Power on Failed")

    def read_tpm_singlewire(self, tpm_id, address):
        self.Mng.write("HKeep.PsntMux", tpm_id - 1)  # select tpm by psnt_mux
        regval = self.CpldMng.read_register(address)
        return regval

    def write_tpm_singlewire(self, tpm_id, address, value):
        self.Mng.write("HKeep.PsntMux", tpm_id - 1)  # select tpm by psnt_mux
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
            logger.debug("TPM address will be assigned:")
            for i in range(0, 8):
                # tpm_add = (tpm_ip_add_h | (cpu_ip_l + 6 + i))
                logger.debug("slot %d -> %s" % (i+1 , self.tpm_ip_list[i]))
            return self.tpm_ip_list
        else:
            logger.debug("Error TPM IP list")
            raise SubrackExecFault("Error:TPM IP Add List Incomplete")

    def SetTPMIP(self, tpm_slot_id, ip, netmask, gateway =  None):
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
        ip_int_rb = self.read_tpm_singlewire(tpm_slot_id, 0x40000028)
        if ip_int_rb != ipstr2hex(ip):
                logger.error("SetTPMIP - expected %s, got %s"%(ip,int2ip(ip_int_rb)))
        self.write_tpm_singlewire(tpm_slot_id, 0x4000002C, ipstr2hex(netmask))
        if gateway is not None:
            self.write_tpm_singlewire(tpm_slot_id, 0x40000030, ipstr2hex(gateway))
        if len(self.tpm_ip_list) == 8:
            self.tpm_ip_list[tpm_slot_id - 1] = ip
        else:
            logger.debug("SetTPMIP ERROR: TPM IP address list incomplete")
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
        tpm_ip = self.read_tpm_singlewire(tpm_slot_id, 0x40000028)
        tpm_ip_str = int2ip(tpm_ip)
        if len(self.tpm_ip_list) == 8:
            if ipstr2hex(self.tpm_ip_list[tpm_slot_id - 1]) != tpm_ip:
                logger.warning("GetTPMIP WARNING: TPM IP mismatch with expected list")
                # raise SubrackExecFault("Error:TPM IP address mismatch with ip add list")
        else:
            logger.debug("GetTPMIP ERROR: TPM IP address list incomplete")
            raise SubrackExecFault("Error:TPM IP address list incomplete")
        logger.info("TPM IP ADD of board in slot %d: %s" % (tpm_slot_id, tpm_ip_str))
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
        # logger.info("TPM IP: %s, CPU IP: %s" %(tpm_ip,subrack_cpu_ip))
        logger.info("TPM IP: %s" % tpm_ip_str)
        # tpm = TPM_1_6()
        # tpm.connect(ip=tpm_ip_str, port=10000, initialise=False, simulation=False, enable_ada=False, fsample=800e6)
        tpm = self.TPM_instances_list[tpm_slot_id -1]
        tpm_info = tpm.get_board_info()
        if prev_onoff == 0:
            if self.Bkpln.pwr_off_tpm(tpm_slot_id)!=0:
                raise SubrackExecFault("Error:TPM Power on Failed")
        # logger.info(tpm_info)
        return tpm_info

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
                    logger.debug ("Error:TPM Power on Failed")
                    return 1
            else:
                prev_onoff = 1
        else:
            # raise SubrackInvalidCmd("TPM not present")
            logger.debug("ERROR: TPM not present")
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
        logger.debug("Global status: %s" % global_status)
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
        # logger.debug("GetTPMTemperatures %d"%tpm_slot_id)
        prev_onoff = 0
        pres_tpm = self.GetTPMPresent()
        #logger.debug("TPM Present: %x" %pres_tpm)
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
                    logger.debug ("Error:TPM Power on Failed")
                    return -1
            else:
                prev_onoff = 1
        else:
            # raise SubrackInvalidCmd("TPM not present")
            logger.debug("ERROR: TPM not present")
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
                    logger.debug("Error:TPM Power on Failed")
                    return 1
            else:
                prev_onoff = 1
        else:
            #raise SubrackInvalidCmd("TPM not present")
            logger.debug("ERROR: TPM not present")
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
        logger.info("SubrackInitialConfiguration")
        self.mode = "INIT"
        logger.debug("Config TPM's Power monitor to config 5")
        for i in range(1, 9):
            self.Bkpln.pwr_set_ilimt(i, 5)
        self.powermon_cfgd = True
        open("/run/lock/subrack_management_board_powermon_cfgd", 'a').close()

    def get_subrack_cpu_cpld_ip(self):
        """ SubrackInitialConfiguration
        @brief method Initizlize the Subrack power control configuration for TPM current limit
        :return cpu_ip, cpld_ip: Management CPU IP, Management CPLD IP
        """
        cpu_ip, netmask, gateway = self.Mng.detect_cpu_ip()
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
        logger.info("PowerOnTPM - %d"%(tpm_slot_id))
        """method to power on selected tpm
        :param  tpm_slot_id: subrack slot index for selected TPM, accepted value 1-8
        :param force: force the operation even if no TPM is present in selected slot
        """
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) == 0:
            logger.error("ERROR: TPM not present in selected slot")
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
                    logger.error("Power TPM on slot %d failed" % tpm_slot_id)
                    raise SubrackExecFault("ERROR: power on TPM command failed")
                else:
                    time.sleep(2)
                    self.__assign_tpm_ip(tpm_slot_id)
                    time.sleep(2)
                    tpm_ip_str = self.tpm_ip_list[tpm_slot_id - 1]
                    try:
                        self.TPM_instances_list[tpm_slot_id-1] = TPM_1_6()
                        # port=10000, lmc_ip="10.0.10.1", lmc_port=4660, sampling_rate=800e6
                        self.TPM_instances_list[tpm_slot_id-1].connect(ip=tpm_ip_str, port=10000, initialise=False,
                                                                    simulation=False, enable_ada=False, fsample=800e6)
                        self.TPM_instances_list[tpm_slot_id-1].load_plugin("Tpm_1_6_Mcu")
                    except LibraryError:
                        logger.warning("Exception during TPM connection at SLOT-%d"%tpm_slot_id)
        logger.info("PowerOnTPM End")



    def PowerOffTPM(self, tpm_slot_id, force = False):
        """method to power off selected tpm
        :param  tpm_slot_id: subrack slot index for selected TPM, accepted value 1-8
        :param force: force the operation even if no TPM is present in selected slot
        """
        logger.info("PowerOffTPM - %d"%(tpm_slot_id))
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) == 0:
            logger.error("ERROR: TPM not present in selected slot")
            if force is True:
                self.Bkpln.pwr_off_tpm(tpm_slot_id)
            else:
                raise SubrackExecFault("ERROR: TPM not present in selected slot")
        else:
            if self.Bkpln.is_tpm_on(tpm_slot_id) is True:
                self.TPM_instances_list[tpm_slot_id - 1].disconnect()
                self.tpm_plugin_loaded[tpm_slot_id -1] = False
                if self.Bkpln.pwr_off_tpm(tpm_slot_id):
                    logger.error("Power TPM off slot %d failed" % tpm_slot_id)
                    raise SubrackExecFault("ERROR: power off TPM command failed")
        logger.info("PowerOffTPM End")

    def SetFanSpeed(self, fan_id, speed_pwm_perc):
        """This method set the_bkpln_fan_speed
        :param fan_id: id of the selected fan accepted value: 1-4
        :param speed_pwm_perc: percentage value of fan RPM  (MIN 0=0% - MAX 100=100%)
        :note settings of fan speed is possible only if fan mode is manual
        """
        logger.info("SetFanSpeed - %d,%d"%(fan_id, speed_pwm_perc))
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
        # logger.debug ("rpm %d, pwm_perc %d" %(rpm,pwm_perc))
        if status == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        return rpm, pwm_perc

    def SetFanMode(self, fan_id_blk, auto_mode):
        """This method set the fan mode
        :param fan_id_blk: id of the fan cuople accepted value: 1-4, for fan 1,2; 3 for fan 3,4
        :param auto_mode: fan mode configuration, 1 auto(controlled by MCU), 0 manual(use SetFanSpeed method)
        :note fan are coupled, passing fan_blk_id=1 both fan 1 and 2 will be configured at same mode,
        """
        logger.info("SetFanMode - %d,%d"%(fan_id_blk, auto_mode))
        if self.Bkpln.set_bkpln_fan_mode(fan_id_blk, auto_mode) == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        
    def GetFanMode(self, fan_id):
        """This method get the_bkpln_fan_mode
        :param fan_id: id of the selected fan accepted value: 1-4
        :return auto_mode: functional fan mode: auto or manual
        :return status: status of operation
        """
        auto_mode, status = self.Bkpln.get_bkpln_fan_mode(fan_id)
        # logger.debug("auto_mode %d, status %d" % (auto_mode, status))
        if status == 1:
            raise SubrackInvalidParameter("ERROR: invalid Fan ID")
        return auto_mode

    def PllInitialize(self, source_internal = False, pll_cfg_file=None):
        """This method initialize the PLL"""
        logger.info("PllInitialize")
        if self._simulation is False:
            self.CpldMng.write_register(0x300,0)
            self.CpldMng.write_register(0x300,1)
            if pll_cfg_file is not None:
                self.CpldMng.pll_ldcfg(pll_cfg_file)
            else:
                if source_internal:
                    logger.warning("PllInitialize internal source selected")
                    self.pll_lock_exp_rd = 0x03
                    self.Mng.write('HKeep.PPSMux',3)
                    self.CpldMng.pll_ldcfg(PLL_CFG_FILE_INTERNAL)
                else:
                    logger.info("PllInitialize external source selected")
                    self.pll_lock_exp_rd = 0x33
                    self.Mng.write('HKeep.PPSMux',0)
                    self.CpldMng.pll_ldcfg(PLL_CFG_FILE)
            self.CpldMng.pll_calib()
            self.CpldMng.pll_ioupdate()
            time.sleep(0.5)
            #rd=hex(self.CpldMng.read_spi(0x3001))
            rd = self.CpldMng.pll_read_with_update(0x3001)
            logger.debug ("PLL lock reg (0x3001): 0x%x" % rd)
            if rd != self.pll_lock_exp_rd:
                logger.error("ERROR: PLL configuration failed, PLL not locked (expected 0x%x, read 0x%x)"%(self.pll_lock_exp_rd,rd))
            # raise SubrackExecFault("ERROR: PLL configuration failed, PLL not locked")
        else:
            r = "0x33"
            logger.debug("pll res = %s" % r)
            if r != "0x33":
                logger.debug ("ERROR: PLL configuration failed, PLL not locked")
        """
        if self._simulation==False:
            ipstring=self.Mng.get_cpld_actual_ip()
            cmd = "bash ./pll_cfg.sh "+ ipstring
            logger.debug (cmd)
            res=run(cmd)
            lines=res.splitlines()
            r=lines[len(lines)-1]
            logger.debug("pll res = %s" %r)
            if (r!="0x33"):
                if (str(r) != "b'0x33'"):
                    logger.debug ("ERROR: PLL configuration failed, PLL not locked")
            # raise SubrackExecFault("ERROR: PLL configuration failed, PLL not locked")
        else:
            r = "0x33"
            logger.debug("pll res = %s" % r)
            if r != "0x33":
                logger.debug ("ERROR: PLL configuration failed, PLL not locked")
        """

    def GetLockedPLL(self):
        """This method get the status of the PLL Lock
        :return locked: value of locked status, True PLL is locked, False PLL not locked
        """
        #rd = hex(self.CpldMng.read_spi(0x3001))
        rd = self.CpldMng.pll_read_with_update(0x3001)
        #logger.debug("PLL lock reg: %s" % rd)
        if rd != self.pll_lock_exp_rd:
            logger.error("PLL not locked")
            return False
        else:
            return True

    def GetCPLDLockedPLL(self):
        """This method get the status of the CPLD internal PLL Lock
        :return locked: value of locked status, True PLL is locked, False PLL not locked
        """
        rd = hex(self.CpldMng.read_register(0xC))
        #logger.debug("PLL CPLD lock reg: %s" % rd)
        if (int(rd, 16) & 0x1) != 0x1:
            #logger.debug("PLL not locked")
            return False
        else:
            #logger.debug("PLL locked")
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
                logger.debug("Received Data 0x%x" % receive_data)
                end = time.time()
                receive_data = self.ser.read(32)  # read serial port
                logger.debug("Received Data 0x%x" % receive_data)
                end = time.time()
                if end - start >= 5:
                    timeout = True
                if receive_data[0] == 73:
                    logger.debug("Update Ups Charge Regs")
                    self.ups_charge_regs = {
                        "charger_status": int.from_bytes(receive_data[1:3], byteorder='big'),  # .encode('hex'),
                        "charging_curr": int.from_bytes(receive_data[4:6], byteorder='big'),  # .encode('hex'),
                        "charging_volt": int.from_bytes(receive_data[7:9], byteorder='big'),  # .encode('hex'),
                        "alarm_warning": int.from_bytes(receive_data[10:12], byteorder='big'),  # .encode('hex'),
                        "bbu_status": int.from_bytes(receive_data[13:15], byteorder='big'),  # .encode('hex'),
                        "bbu_control": int.from_bytes(receive_data[16:18], byteorder='big')  # .encode('hex')
                    }
                    received = True
                    logger.debug(self.ups_charge_regs)
                    if receive_data[19] == 65:
                        logger.debug("Update Ups ADC Values")
                        self.ups_adc_values = {
                            "power_in": round((int.from_bytes(receive_data[20:22], byteorder='big') * 15.24 * 0.8), 2),
                            "vin_sht": round((int.from_bytes(receive_data[23:25], byteorder='big') * 15.24 * 0.8), 2),
                            "vin": round((int.from_bytes(receive_data[26:28], byteorder='big') * 15.24 * 0.8), 2),
                            "man_5v0": round((int.from_bytes(receive_data[29:31], byteorder='big') * 0.8 * 15.24), 2)
                        }
                        received = True
                        logger.debug(self.ups_adc_values)
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
                    logger.debug("TIMEOUT")
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

    def all_monitoring_points(self):
        """
        Returns a list of all monitoring points by finding all leaf nodes
        in the lookup dict that have a corresponding method field.

        The monitoring points returned are strings produced from '.' delimited 
        keys. For example:
        'voltages.5V0'
        'io.udp_interface.crc_error_count.FPGA0'

        More info at https://confluence.skatelescope.org/x/nDhED

        :return: list of monitoring points
        :rtype: list of strings
        """
        def find_leaf_dict_recursive(health_dict, key_list=[], output_list=[]):
            for name, value in health_dict.items():
                key_list.append(name)
                if not isinstance(value, dict):
                    output_list.append('.'.join(key_list))
                    key_list.pop()
                else:
                    find_leaf_dict_recursive(value, key_list, output_list)
            if key_list:
                key_list.pop()
            return output_list
            
        # Find leaves of nested dict
        dict_leaf_list = find_leaf_dict_recursive(self.monitoring_point_lookup_dict)
        # Keep only points ending in .method, then remove the .method
        monitoring_point_list = []
        for point in dict_leaf_list:
            if point.endswith('.method'):
                monitoring_point_list.append(point[:-7])
        return monitoring_point_list

    def _parse_dict_by_path(self, dictionary, path_list):
        """
        General purpose method to parse a nested dictory by a list of keys.

        Example:
        test_dict = {'parent': {'child1': 10, 'child2':12}, 'parent2': {'child3': 14}}
        self._parse_dict_by_path(test_dict, ['parent', 'child2']) would return 12
        self._parse_dict_by_path(test_dict, ['parent2', 'child3']) would return 14
        self._parse_dict_by_path(test_dict, ['parent']) would return {'child1': 10, 'child2':12}

        :param dictionary: Input nested dictionary
        :type dictionary: dict

        :param path_list: List of dictionary keys, from top to bottom
        :type path_list: list

        :return: value
        """
        return reduce(operator.getitem, path_list, dictionary)

    def _create_nested_dict(self, key_list, value, nested_dict={}):
        """
        General purpose method to append to a nested dictionary based on a provided
        list of keys and a value.
        If nested_dict is not specified a new dictionary is created. Subsequent calls
        with the same nested_dict provided will append.
        Used to recreate a nested dictionary hierarchy from scratch.

        NOTE: nested_dict is not copied so due to Python dictionaries being mutable,
        the returned nested_dict is optional, required for creation of new dictionaries.

        :param key_list: List of dictionary keys, from top to bottom
        :type key_list: list

        :param value: Value to be stored at path specified by key_list
        :type value: anything

        :param nested_dict: Input nested dictionary
        :type nested_dict: dict

        :return: nested_dict
        :rtype: dict
        """
        current_dict = nested_dict
        for key in key_list[:-1]:
            if key not in current_dict:
                current_dict[key] = {}
            current_dict = current_dict[key]
        current_dict[key_list[-1]] = value
        return nested_dict
    
    def _kwargs_handler(self, kwargs):
        """
        For use with get_health_status method.
        Filter all monitoring points to a subset based on monitoring 
        point attr match to kwargs in monitoring point lookup dict.

        NOTE: when multiple args specified, all must match

        :param kwargs: dictionary of kwargs
        :type kwargs: dict

        :return: monitoring point list
        :rtype: list
        """
        if not kwargs:
            return self.all_monitoring_points()
        # get list of monitoring points to be polled based on kwargs
        mon_point_list = []
        for monitoring_point in self.all_monitoring_points():
            lookup = monitoring_point.split('.')
            lookup_entry = self._parse_dict_by_path(self.monitoring_point_lookup_dict, lookup)
            keep = 0
            for key, val in kwargs.items():
                if val in lookup_entry.get(key, []):
                    keep +=1
            if keep == len(kwargs):
                mon_point_list.append(monitoring_point)
        return mon_point_list
    
    def get_health_status(self, **kwargs):
        """
        Returns the current value of TPM monitoring points with the 
        specified attributes as set in the method set_monitoring_point_attr.
        If no arguments given, current value of all monitoring points is returned.

        For example:
        If configured with:
        tile.set_monitoring_point_attr('io.udp_interface', my_category='yes', my_other_category=87)

        Subsequent calls to:
        tile.get_health_status(my_category='yes', my_other_category=87)

        would return only the health status for:
        io.udp_interface.arp
        io.udp_interface.status
        io.udp_interface.crc_error_count.FPGA0
        io.udp_interface.crc_error_count.FPGA1
        io.udp_interface.bip_error_count.FPGA0
        io.udp_interface.bip_error_count.FPGA1
        io.udp_interface.decode_error_count.FPGA0
        io.udp_interface.decode_error_count.FPGA1
        io.udp_interface.linkup_loss_count.FPGA0
        io.udp_interface.linkup_loss_count.FPGA1

        A group attribute is provided by default, see tpm_1_X_monitoring_point_lookup.
        This can be used like the below example:
        tile.get_health_status(group='temperatures')
        tile.get_health_status(group='udp_interface')
        tile.get_health_status(group='io')

        Full documentation on usage available at https://confluence.skatelescope.org/x/nDhED
        """
        health_status = {}
        mon_point_list = self._kwargs_handler(kwargs)
        for monitoring_point in mon_point_list:
            lookup = monitoring_point.split('.')
            lookup_entry = self._parse_dict_by_path(self.monitoring_point_lookup_dict, lookup)
            # call method stored in lookup entry
            value = lookup_entry["method"]()
            # Resolve nested values with only one value i.e
            # get_voltage("voltage_name") returns {"voltage_name": voltage}
            # get_clock_manager_status(fpga_id, name) returns {"FPGAid": {"name": status}}
            while True:
                if not isinstance(value, dict):
                    break
                if len(value) != 1:
                    break
                value = list(value.values())[0]
            # Create dictionary of monitoring points in same format as lookup
            health_status = self._create_nested_dict(lookup, value, health_status)
        return health_status

    def close(self):
        self.__del__()

    # def SetLed(self, id, status):
    #     m = {'a':0x8,'b':0x04,'c':0x2,'d':0x1}
    #     value_A=self.Mng.read('Led.Led_User_A')
    #     value_K=self.Mng.read('Led.Led_User_K')
    #     # logger.debug("m ",format(m[id],'#06b'))
    #     # logger.debug("n ",format(~(m[id])&0xf,'#06b'))
    #     # logger.debug("r ",format(value_A,'#06b'))
    #     # logger.debug("r ",format(value_K,'#06b'))
    #     value_A &= ~(m[id])&0xf
    #     value_K &= ~(m[id])&0xf
    #     if status == "green":
    #         value_A |= m[id];
    #     elif status == "red":
    #         value_K |= m[id];
    #     # logger.debug("w ",format(value_A,'#06b'))
    #     # logger.debug("w ",format(value_K,'#06b'))
    #     self.Mng.write('Led.Led_User_A',value_A)
    #     self.Mng.write('Led.Led_User_K',value_K)
    #     value_A=self.Mng.read('Led.Led_User_A')
    #     value_K=self.Mng.read('Led.Led_User_K')
    #     # logger.debug("r ",format(value_A,'#06b'))
    #     # logger.debug("r ",format(value_K,'#06b'))

if __name__ == '__main__':
    #logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S',level=logging.INFO)
    logger=logging.getLogger(os.path.basename(__file__)+"_main")

    parser = OptionParser()
    parser.add_option("-e", "--emulation", action="store_true", help="enable emulation mode")
    parser.add_option("-i", "--init", action="store_true", default=False, help="performe initialize, required after power up")
    parser.add_option("-s", "--pll_source_internal", action="store_true", default=False, help="Enable internal source for PPS and REF")
    (options, args) = parser.parse_args()
    logger.debug("SubrackMngBoard init ...")
    subrack=SubrackMngBoard(simulation=False)
    if options.init:
        logger.debug("SubrackMngBoard Initialize ...")
        subrack.Initialize(pll_source_internal=options.pll_source_internal)
