__author__ = 'Cristian Albanese'
import string
from subprocess import Popen, PIPE
import sys
import os
import time
import calendar
from datetime import timezone
import datetime
from subrack_mng_api.management import *
from subrack_mng_api.backplane import *
from subrack_mng_api.version import *
import logging
# from pyfabil.base.definitions import *
# from pyfabil.base.utils import ip2long
# from pyfabil.boards.tpm_1_6 import TPM_1_6
import serial
import operator
import subprocess
from subrack_mng_api.subrack_monitoring_point_lookup import load_subrack_lookup
#from pyaavs.tile_1_6 import Tile_1_6 as Tile
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))



from optparse import OptionParser
import Pyro5.api



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


_initial_missing = object()
def reduce(function, sequence, initial=_initial_missing):
    """
    reduce(function, iterable[, initial]) -> value

    Apply a function of two arguments cumulatively to the items of a sequence
    or iterable, from left to right, so as to reduce the iterable to a single
    value.  For example, reduce(lambda x, y: x+y, [1, 2, 3, 4, 5]) calculates
    ((((1+2)+3)+4)+5).  If initial is present, it is placed before the items
    of the iterable in the calculation, and serves as a default when the
    iterable is empty.
    """

    it = iter(sequence)

    if initial is _initial_missing:
        try:
            value = next(it)
        except StopIteration:
            raise TypeError(
                "reduce() of empty iterable with no initial value") from None
    else:
        value = initial

    for element in it:
        value = function(value, element)

    return value

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

def exec_cmd(cmd,dir=None,verbose=True, exclude_line=""):
    start_time = time.time()
    try:
        if verbose:
            print("Exec command: \"" + cmd + "\"")
        if dir is None:
            child = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell = True)
        else:
            child = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell = True, cwd=dir)
        out = ""
        err = ""
        n_lines = 0
        while child.poll() is None:
            line = child.stdout.readline()
            line = line.decode("utf-8")
            n_lines += 1
            if line:
                if verbose:
                    #if exclude_line not in line or exclude_line == "":
                        print(line.strip())
                out += line
        returncode = child.returncode
        # print(n_lines, returncode)
        if verbose:
            if n_lines==0 and out!="":
                lines = out.splitlines()
                for l in lines:
                    print(l)
            print("Elapsed time was " + get_elapsed_time(start_time) + " executing command: \"" + cmd + "\"")
        #return {'out':out,'returncode':returncode}
        return out,returncode
    except KeyboardInterrupt:
        print("...CTRL+C...")
        raise NameError("exec_cmd fails: \""+cmd+"\"")


def Adu_Eth_Ping(ip, count=1, interval='0.2', size=8, wait = '1'):
    cmd='ping ' + ip + ' -c %d'%count + ' -i ' + interval
    if size is not None:
        cmd += ' -s %d'%size
    if wait is not None:
        cmd += ' -W %s'%wait
    out,returncode=exec_cmd(cmd,verbose=False)
    ping_loss=0
    if returncode > 0:
        result = 'FAILED'
        ping_loss=out.count('Unreachable')+out.count('unreachable')+out.count('time out')
        if out.count("100% packet loss"):
            ping_loss=count
    return ping_loss

# ##Subrack Management Board Class
# This class implements methods to manage and to monitor the subrack management board
@Pyro5.api.expose
@Pyro5.server.behavior(instance_mode="single")
class SubrackMngBoard():
    def __init__(self, **kwargs):
        logger.info("SubrackMngBoard init ...")
        get_board_info = kwargs.get("get_board_info",True)
        self._simulation = kwargs.get("simulation",False)
        self.data = []
        logger.debug("Mng creating..")
        self.Mng = Management(self._simulation,get_board_info=get_board_info)
        logger.debug("Bkpln creating..")
        self.Bkpln = Backplane(self.Mng, self._simulation,get_board_info=get_board_info)
        self.CpldMng = self.Mng.CpldMng
        # logger.debug("MANAGEMENT created")
        self.mode = 0
        self.status = 0
        self.first_config = False
        self.powermon_cfgd = os.path.exists("/run/lock/subrack_management_board_powermon_cfgd")
        self.tpm_ip_list = []
        self.cpu_ip = ""
        self.__populate_tpm_ip_list()
        # self.TPM_instances_list = [0, 0, 0, 0, 0, 0, 0, 0]
        # self.tpm_plugin_loaded = [False, False, False, False, False, False, False]
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
        self.board_info = {}
        self.board_info['SMM']=self.Mng.board_info
        self.board_info['BACKPLANE']=self.Bkpln.board_info
        try:
            board_info_file = open("/tmp/board_info", "w")
            for board_key,board_info in self.board_info.items():
                table=[]
                for key,value in board_info.items():
                    logger.info("%s: %s"%(key,value))
                    table.append([str(key), str(value)])
                board_info_file.write(tabulate.tabulate(table,headers=["BOARD INFO",board_key],tablefmt='pipe'))
                board_info_file.write('\n')
                board_info_file.write('\n')
            board_info_file.write("SubrackMngAPI version: %s\n" % self.Get_API_version())
            board_info_file.close()
        except PermissionError:
            logger.warning("Cannot create '/tmp/board_info' -  Permission error")

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

    def get_board_info(self):
        return self.board_info
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
                    logger.warning("expected %s, got %s"%(tpm_ip_str,actual_tpm_ip_str))
                    time.sleep(1)
                    self.__assign_tpm_ip(tpm_slot_id)
                if Adu_Eth_Ping(tpm_ip_str) > 0:
                    logger.warning("Exception during TPM connection at SLOT-%d, try power cycle"%tpm_slot_id)
                    self.PowerOffTPM(tpm_slot_id)
                    self.PowerOnTPM(tpm_slot_id)
                # try:
                #     self.TPM_instances_list[i] = TPM_1_6()
                #     # port=10000, lmc_ip="10.0.10.1", lmc_port=4660, sampling_rate=800e6
                #     self.TPM_instances_list[i].connect(ip=tpm_ip_str, port=10000, initialise=False,
                #                                                 simulation=False, enable_ada=False, fsample=800e6)
                #     self.TPM_instances_list[i].load_plugin("Tpm_1_6_Mcu")
                # except LibraryError:
                #     logger.warning("Exception during TPM connection at SLOT-%d, try power cycle"%tpm_slot_id)
                #     self.PowerOffTPM(tpm_slot_id)
                #     self.PowerOnTPM(tpm_slot_id)
                #     pass

    def __assign_tpm_ip(self, tpm_slot_id, timeout = 100):
        cpu_ip, netmask, gateway = self.Mng.detect_cpu_ip()
        if cpu_ip is not None:
            tpm_ip_add_h = ipstr2hex(cpu_ip) & 0xFFFFFF00
            cpu_ip_l = ipstr2hex(cpu_ip) & 0xFF
            tpm_ip_add = tpm_ip_add_h | (cpu_ip_l + 6 + tpm_slot_id)
            res=self.SetTPMIP(tpm_slot_id,int2ip(tpm_ip_add),netmask,gateway, bypass_check = True, timeout = timeout)
            out,returncode=exec_cmd("sudo arp -d %s"%int2ip(tpm_ip_add),verbose=False)
            return res
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
        try:
            cmd="git -C %s describe --tags --dirty --always"%os.path.dirname(__file__)
        except:
            cmd="git -C %s describe --tags --dirty --always"%"/home/mnguser/SubrackMngAPI"
        
        try:
            result = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE)
            if result.returncode == 0:
                return get_version() + " (%s)"%str(result.stdout.decode('utf-8').strip())
            return get_version()
        except:
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

    def SetTPMIP(self, tpm_slot_id, ip, netmask, gateway =  None, bypass_check = False, timeout = 100):
        """ method to manually set volatile local ip address of a TPM board present on subrack
        :param tpm_slot_id: subrack slot index for selected TPM, accepted value 1-8
        :param ip: ip address will be assigned to selected TPM
        :param netmask: netmask value will be assigned to selected TPM
        :return status
        """
        prev_onoff = 0
        if bypass_check == False:
            if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) != 0:
                # if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
                if self.GetTPMOnOffVect() & (1 << (tpm_slot_id-1)) == 0:
                    raise SubrackExecFault("Error:TPM is Powered OFF")
            else:
                raise SubrackInvalidCmd("TPM not present")
        # else:
        #     logger.info("SetTPMIP info: bypass_check disabled")
        retry = timeout
        logger.info("Wait for TPM finish local network configuration from TPM EEPROM")
        while(retry > 0):
            reg = self.read_tpm_singlewire(tpm_slot_id, 0x900000e0)
            if reg != 0xdeadbaad and reg > 0:
                break
            retry -= 1
            time.sleep(0.01)
        if retry == 0:
            logger.error("SetTPMIP : timeout on checking TPM availability")
            return False
        self.write_tpm_singlewire(tpm_slot_id, 0x40000028, ipstr2hex(ip))
        rb_val = self.read_tpm_singlewire(tpm_slot_id, 0x40000028)
        if rb_val != ipstr2hex(ip):
                logger.error("SetTPMIP - IP expected %s, got %s"%(ip,int2ip(rb_val)))
                return False
        self.write_tpm_singlewire(tpm_slot_id, 0x4000002C, ipstr2hex(netmask))
        rb_val = self.read_tpm_singlewire(tpm_slot_id, 0x4000002C)
        if rb_val != ipstr2hex(netmask):
                logger.error("SetTPMIP - NETMASK expected %s, got %s"%(netmask,int2ip(rb_val)))
                return False
        if gateway is not None:
            self.write_tpm_singlewire(tpm_slot_id, 0x40000030, ipstr2hex(gateway))
            rb_val = self.read_tpm_singlewire(tpm_slot_id, 0x40000030)
            if rb_val != ipstr2hex(gateway):
                    logger.error("SetTPMIP - GATEWAY expected %s, got %s"%(gateway,int2ip(rb_val)))
                    return False
        if len(self.tpm_ip_list) == 8:
            self.tpm_ip_list[tpm_slot_id - 1] = ip
        else:
            logger.debug("SetTPMIP ERROR: TPM IP address list incomplete")
            raise SubrackExecFault("Error:TPM IP address list incomplete")
        return True

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
        raise SubrackExecFault("Error: this method is deprecated, subrack do not access TPM anymore")

    def GetTPMGlobalStatusAlarm(self, tpm_slot_id, forceread=False):
        raise SubrackExecFault("Error: this method is deprecated, subrack do not access TPM anymore")

    def Get_tpm_alarms_vector(self):
        raise SubrackExecFault("Error: this method is deprecated, subrack do not access TPM anymore")

    def GetTPMTemperatures(self, tpm_slot_id, forceread=False):
        raise SubrackExecFault("Error: this method is deprecated, subrack do not access TPM anymore")


    def Get_TPM_temperature_vector(self):
        raise SubrackExecFault("Error: this method is deprecated, subrack do not access TPM anymore")


    def GetTPMMCUTemperature(self, tpm_slot_id, forceread=False):
        raise SubrackExecFault("Error: this method is deprecated, subrack do not access TPM anymore")


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

    def GetTPMPresent(self,tpm_slot_id = None):
        """brief method to get info about TPM board present on subrack
        :return TpmDetected: vector of tpm positional,1 TPM detected,0 no TPM inserted,bit 7:0,bit 0 slot 1,bit 7 slot 8
        """
        TpmDetected = self.Mng.get_housekeeping_flag("TPMsPresent")
        TpmDetected = self.Mng.get_housekeeping_flag("TPMsPresent")
        if tpm_slot_id is None:
            return TpmDetected
        else:
            if (TpmDetected & (1 << (tpm_slot_id-1))) != 0:
                return True
            else:
                return False


    def GetTPMOnOffVect(self):
        """method to get Power On status of inserted tpm, 0 off or not present, 1 power on
        :return vector of poweron status for slots, bits 7:0, bit 0 slot 1, bit 7 slot 8, 1 TPM power on, 0 no TPM
        inserted or power off
        """
        # reg = self.Mng.read("Fram.TPM_SUPPLY_STATUS")
        # tpmison_vect = reg & 0xff
        tpmison_vect = 0
        for i in range(1,9):
            if self.Bkpln.is_tpm_on(i):
                tpmison_vect |= 1 << (i-1)
        return tpmison_vect

    def GetTPMSupplyFault(self):
        """ Method to get info about TPM supply fault status, 1 for each TPM in backplane slot
        :return tpmsupplyfault: vector of tpm supply fault status, 1 fault, 0 no fault,bit 7:0,bit 0 slot 1,bit 7 slot 8
        """
        reg = self.Mng.read("Fram.TPM_SUPPLY_STATUS")
        tpmsupplyfault = (reg & 0xff00) >> 8
        return 0
        # return tpmsupplyfault

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
            if self.Bkpln.is_tpm_on(tpm_slot_id):
                volt = self.Bkpln.get_voltage_tpm(tpm_slot_id)
                return volt
            else:
                return None
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

    def PowerOnTPM(self, tpm_slot_id, force=False, ping_check = False):
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
            logger.info("PowerOnTPM TPM is present")
            if self.Bkpln.get_bkpln_is_onoff() == 0:
                self.Bkpln.power_on_bkpln()
                if self.powermon_cfgd is False:
                    self.SubrackInitialConfiguration()
                logger.info("PowerOnTPM BKPLN was off, switched on")
            if self.Bkpln.is_tpm_on(tpm_slot_id) is False:
                logger.info("PowerOnTPM TPM was off, switched on")
                if self.Bkpln.pwr_on_tpm(tpm_slot_id):
                    logger.error("Power TPM on slot %d failed" % tpm_slot_id)
                    raise SubrackExecFault("ERROR: power on TPM command failed")
                else:
                    #logger.info("PowerOnTPM wait 0.5s")
                    #time.sleep(0.5)
                    logger.info("PowerOnTPM __assign_tpm_ip")
                    if not self.__assign_tpm_ip(tpm_slot_id):
                        logger.warning("IP assignament of TPM on slot %d failed, retry" % tpm_slot_id)
                        logger.info("Wait 2s before power off again")
                        time.sleep(2)
                        logger.info("Power off")
                        self.Bkpln.pwr_off_tpm(tpm_slot_id)
                        logger.info("Wait 1s before power on again")
                        time.sleep(1)
                        if self.Bkpln.pwr_on_tpm(tpm_slot_id):
                            logger.error("Power TPM on slot %d failed" % tpm_slot_id)
                            raise SubrackExecFault("ERROR: power on TPM command failed")
                        else:
                            logger.info("PowerOnTPM __assign_tpm_ip")
                            if not self.__assign_tpm_ip(tpm_slot_id):
                                logger.error("IP assignament of TPM on slot %d failed" % tpm_slot_id)
                    #logger.info("PowerOnTPM wait 2s")
                    #time.sleep(2)
                    tpm_ip_str = self.tpm_ip_list[tpm_slot_id - 1]
                    if ping_check:
                        logger.info("PowerOnTPM Adu_Eth_Ping")
                        time.sleep(2)
                        if Adu_Eth_Ping(tpm_ip_str,wait=2) > 0:
                            logger.error("Adu_Eth_Ping failed at SLOT-%d"%tpm_slot_id)
                            # raise SubrackExecFault("Adu_Eth_Ping failed!")

        logger.info("PowerOnTPM End")

    def GetPingTPM(self, tpm_slot_id):
        if self.GetTPMPresent() & (1 << (tpm_slot_id-1)) > 0:
            if self.Bkpln.is_tpm_on(tpm_slot_id):
                ip = self.GetTPMIP(tpm_slot_id)
                if Adu_Eth_Ping(ip) == 0:
                    return True
                else:
                    return False
        return None
    
    def GetPingCpld(self):
        ip = self.Mng.get_cpld_actual_ip()
        if Adu_Eth_Ping(ip) == 0:
            return True
        else:
            return False
    
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
    
    def GetFanRpm(self,fan_id):
        rpm, pwm_perc = self.GetFanSpeed(fan_id)
        return rpm
    
    def GetFanPwm(self,fan_id):
        rpm, pwm_perc = self.GetFanSpeed(fan_id)
        return pwm_perc

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
            self.Mng.test_ucp_access(1000)
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
    def GetPllSource(self):
        if self.Mng.read('HKeep.PPSMux') == 3:
            return "internal"
        else:
            return "external"

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
        if ps_id > 2 or ps_id < 1:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        vout = self.Bkpln.get_ps_vout(ps_id)
        return vout

    def GetPSIout(self, ps_id):
        """This method get the Iout current value of selected Power Supply of subrack
        :param ps_id: id of the selected power supply, accepted value: 1,2
        :return vout: value of Iout in Ampere
        """
        if ps_id > 2 or ps_id < 1:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        vout = self.Bkpln.get_ps_iout(ps_id)
        return vout

    def GetPSPower(self, ps_id):
        """This method get the Power consumption value of selected Power Supply of subrack
        :param ps_id: id of the selected power supply, accepted value: 1,2
        :return power: value of power in W
        """
        if ps_id > 2 or ps_id < 1:
            raise SubrackInvalidParameter("ERROR: Invalid Power supply ID")
        power = self.Bkpln.get_ps_power(ps_id)
        return power

    def GetPSFanSpeed(self, ps_id):
        """This method get the fan speed of selected Power Supply of subrack
        :param ps_id: id of the selected power supply, accepted value: 1,2
        :return fanspeed: speed of the fan
        """
        if ps_id > 2 or ps_id < 1:
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
        if ps_id > 2 or ps_id < 1:
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
    
    def all_monitoring_categories(self):
        """
        Returns a list of all monitoring point 'categories'.
        Here categories is a super-set of monitoring points and is 
        the full list of accepted strings to set_monitoring_point_attr. 
        For example, these monitoring points:
        voltages.5V0
        io.udp_interface.crc_error_count.FPGA0

        would have these associated categories:
        'voltages'
        'voltages.5V0'
        'io'
        'io.udp_interface'
        'io.udp_interface.crc_error_count'
        'io.udp_interface.crc_error_count.FPGA0'

        :return: list of categories
        :rtype: list of strings
        """
        all_monitoring_points = self.all_monitoring_points()
        categories = set()
        for monitroing_point in all_monitoring_points:
            parts = monitroing_point.split('.')
            for i in range(len(parts)):
                categories.add('.'.join(parts[:i+1]))
        categories_list = list(categories)
        categories_list.sort()
        return categories_list
    
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
        Returns the current value of SUBRACK monitoring points
        If no group argument given, current value of all monitoring points is returned.

        For example:
        subrack.get_health_status(group='temperatures')
        would return only the health status for:
        
        A group attribute is provided by default, see subrack_monitoring_point_lookup.py.
        This can be used like the below example:
        subrack.get_health_status(group='temperatures')
        subrack.get_health_status(group='slots')
        subrack.get_health_status(group='voltages')
        

        """
        health_status = {}
        health_status['iso_datetime']= datetime.now(timezone.utc).isoformat()
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
    
    def get_health_dict(self, **kwargs):
        """
        Returns the dictionary of SUBRACK monitoring points with the 
        static key only, no value
        """
        health_dict = {}
        health_dict['iso_datetime']= datetime.now(timezone.utc).isoformat()
        mon_point_list = self._kwargs_handler(kwargs)
        for monitoring_point in mon_point_list:
            lookup = monitoring_point.split('.')
            d = self._parse_dict_by_path(self.monitoring_point_lookup_dict, lookup)
            # call method stored in lookup entry
            exclude_keys=['method']
            new_d = {k: d[k] for k in set(list(d.keys())) - set(exclude_keys)}
            
            # Create dictionary of monitoring points in same format as lookup
            health_dict = self._create_nested_dict(lookup, new_d, health_dict)
        return health_dict

    def bkpln_set_field(self,key,value, override_protected=False):
        return self.Bkpln.set_field(key,value,override_protected)
    
    def bkpln_get_field(self,key):
        return self.Bkpln.get_field(key)
    
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
    parser.add_option("-g", "--do_not_get_board_info", action="store_false", default=True, dest = "get_board_info", help="")
    parser.add_option("-s", "--pll_source_internal", action="store_true", default=False, help="Enable internal source for PPS and REF")
    (options, args) = parser.parse_args()
    logger.debug("SubrackMngBoard init ...")
    subrack=SubrackMngBoard(simulation=False,get_board_info = options.get_board_info)
    if options.init:
        logger.debug("SubrackMngBoard Initialize ...")
        subrack.Initialize(pll_source_internal=options.pll_source_internal)
