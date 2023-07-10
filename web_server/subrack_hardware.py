"""
LFAA SPS Subrack control board hardware driver.
"""
from HardwareBaseClass import *
from HardwareThreadedClass import *
from subrack_mng_api.subrack_management_board import *
import time
import json
import logging

# helper function
# byte to list of 8 bool
def byte_to_bool_array(byte_in):
    """
    Convert a byte to a list of 8 bool. Bit 0 corresponds to list[0]

    :param byte_in: Byte with 8 LS bits representing 8 logical values
    :type byte_in: int
    :return: list of 8 bool values
    """
    retvalue = [False] * 8
    mask = 1
    for i in range(8):
        if (byte_in & mask) != 0:
            retvalue[i] = True
        mask = mask << 1
    return retvalue


# Commands for subrack


class PowerOnTpmCommand(ThreadedHardwareCommand):
    """
    Power On TPM command. Switches on a single or multiple TPM
    """

    def thread(self, tpm_id):
        """
        Power on TPMs

        :param tpm_id: index of TPM to power on (1-8) or list of indexes
        : type tpm_id: str, list(str)

        :return: dictionary with HardwareCommand response. List of TPM On status
        :rtype: dict
        """

        try:
            if type(tpm_id) == list:
                for tpm_slot_id in tpm_id:
                    self._hardware.PowerOnTPM(int(tpm_slot_id))
                    if self._abort:
                        break
            else:
                tpm_slot_id = int(tpm_id)
                self._hardware.PowerOnTPM(tpm_slot_id)
        except SubrackExecFault:
            pass
        tpm_is_on = self._hardware.GetTPMOnOffVect()
        self._completed = True
        return


class PowerOffTpmCommand(ThreadedHardwareCommand):
    """
    Power Off TPM command. Switches off a single or multiple TPM
    """

    def thread(self, tpm_id):
        """
        Power off TPMs

        :param tpm_id: index of TPM to power on (1-8) or list of indexes
        : type tpm_id: str, list(str)

        :return: dictionary with HardwareCommand response. List of TPM On status
        :rtype: dict
        """
        try:
            if type(tpm_id) == list:
                for tpm_slot_id in tpm_id:
                    self._hardware.PowerOffTPM(int(tpm_slot_id))
                    if self._abort:
                        break
            else:
                tpm_slot_id = int(tpm_id)
                self._hardware.PowerOffTPM(tpm_slot_id)
        except SubrackExecFault:
            pass
        tpm_is_on = self._hardware.GetTPMOnOffVect()
        self._completed = True
        return


class IsTpmOnCommand(HardwareCommand):
    """
    Check TPM power status
    """

    def do(self, params):
        """
        Check power status of TPMs

        :param params: index of TPM to check (1-8)
        : type params: str

        :return: dictionary with HardwareCommand response. Integer retvalue
        :rtype: dict
        """

        answer = super().do()
        tpm_slot_id = int(params)
        if tpm_slot_id > 0 & tpm_slot_id <= 8:
            tpm_on = self._hardware.GetTPMOnOffVect()
            if tpm_on & (1 << (tpm_slot_id - 1)) != 0:
                retval = 1
            else:
                retval = 0
        else:
            answer["status"] = "ERROR"
            answer["info"] = "TPM ID must be between 1 and 8"
            retval = 0
        answer["retvalue"] = retval
        return answer


class PowerUpCommand(ThreadedHardwareCommand):
    """
    Power on all TPMs
    """

    def thread(self, params):
        """
        Power on all TPMs

        :param params: unused
        """

        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        try:
            for tpm in range(8):
                if tpm_detected[tpm]:
                    self._hardware.PowerOnTPM(tpm + 1)
                    if self._abort:
                        break
        except SubrackExecFault:
            pass
        self._completed = True
        return


class PowerDownCommand(ThreadedHardwareCommand):
    """
    Power off all TPMs
    """

    def thread(self, params):
        """
        Power off all TPMs

        :param params: unused
        """

        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        try:
            for tpm in range(8):
                if tpm_detected[tpm]:
                    self._hardware.PowerOffTPM(tpm + 1)
                    if self._abort:
                        break
        except SubrackExecFault:
            pass
        self._completed = True
        return


class AreTpmsOnCommand(HardwareCommand):
    def do(self, params):
        answer = super().do()
        tpm_on_list = byte_to_bool_array(self._hardware.GetTPMOnOffVect())
        answer["retvalue"] = tpm_on_list
        return answer


class SetFanMode(HardwareCommand):
    """
    Set fan mode (manual, auto)
    """

    def do(self, params):
        """
        :param params: [0]: Fan ID (in range 1-4), [1]: mode [MANUAL|AUTO]

        :return: dictionary with HardwareCommand response.
        :rtype: dict
        """
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requires 2 parameters"
        else:
            fan_id = int(params[0])
            fan_mode = params[1]
            if (fan_id >= 1) & (fan_id <= 4):
                self._hardware.SetFanMode(fan_id, fan_mode)
            else:
                answer["status"] = "ERROR"
                answer["info"] = "Fan ID must be between 1 and 4"
        return answer


class SetFanSpeed(HardwareCommand):
    """
    Set cabinet fan speed (0-100)
    """

    def do(self, params):
        """
        :param params: [0]: Fan ID (in range 1-4), [1]: speed (percentage)

        :return: dictionary with HardwareCommand response. Retval is actual speed
        :rtype: dict
        """
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requires 2 parameters"
        else:
            fan_id = int(params[0])
            fan_speed = params[1]
            if (fan_id >= 1) & (fan_id <= 4):
                self._hardware.SetFanSpeed(fan_id, fan_speed)
            else:
                answer["status"] = "ERROR"
                answer["info"] = "Fan ID must be between 1 and 4"
        return answer


class SetPSFanSpeed(HardwareCommand):
    """
    Set Power Supply fan speed (0-100)
    """

    def do(self, params):
        """
        :param params: [0]: Fan ID (in range 1-2), [1]: speed (percentage)

        :return: dictionary with HardwareCommand response. Retval is actual speed
        :rtype: dict
        """
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requires 2 parameters"
        else:
            fan_id = int(params[0])
            fan_speed = int(params[1])
            if (fan_id >= 1) & (fan_id <= 2):
                self._hardware.SetPSFanSpeed(fan_id, fan_speed)
            else:
                answer["status"] = "ERROR"
                answer["info"] = "Fan ID must be between 1 and 2"
        return answer


class TpmInfo(HardwareCommand):
    """
    Return info about TPM board present on subrack.
    """

    def do(self, params):
        """
        Info about TPM.

        :param params: index of TPM to check (1-8)
        : type params: str

        :return: TPM info
        :rtype: dict
        """
        answer = super().do()
        tpm_slot_id = int(params)
        tpm_info = self._hardware.GetTPMInfo(tpm_slot_id)
        answer["retvalue"] = tpm_info
        return answer

class GetHealthDict(HardwareCommand):
    """
    Return subrack health status dictionary.
    """

    def do(self, params):
        """
        Info about subrack health status 
        :param params: group of monitor points to report
        :type params: str 

        :return:dictionary  of monitor points
        :rtype: dict
        """
        answer = super().do()
        if (params == "") or (params is None) or (len(params) == 0):
            answer["retvalue"] = self._hardware.get_health_dict()
        else:
            answer["retvalue"] = self._hardware.get_health_dict(group=params)
        return answer

class GetHealthStatus(HardwareCommand):
    """
    Return info about subrack health status.
    """

    def do(self, params):
        """
        Info about subrack health status 
        :param params: group of monitor points to report
        :type params: str 

        :return: dictionary of monitor point values
        :rtype: dict
        """
        answer = super().do()
        if (params == "") or (params is None) or (len(params) == 0):
            answer["retvalue"] = self._hardware.get_health_status()
        else:
            answer["retvalue"] = self._hardware.get_health_status(group=params)
        return answer


# Attributes


class BackplaneTemperature(HardwareAttribute):
    """
    Backplane temperature, in celsius
    """

    def read_value(self):
        """
        :return: backplane temperature, in celsius, for the two backplane halves
        :rtype: list[float]
        """
        temperature = self._hardware.GetSubrackTemperatures()
        answer = temperature[2:4]
        return answer


class BoardCurrent(HardwareAttribute):
    def read_value(self):
        """
        :return: Total subrack current (A)
        :rtype: float
        """
        current1 = self._hardware.GetPSIout(1)
        current2 = self._hardware.GetPSIout(2)
        return current1 + current2


class BoardTemperature(HardwareAttribute):
    def read_value(self):
        """
        :return: Subrack control board temperature, in celsius, 2 values
        :rtype: list[float]
        """
        temperature = self._hardware.GetSubrackTemperatures()
        answer = temperature[0:2]
        return answer


class FanSpeedPercent(HardwareAttribute):
    def read_value(self):
        """
        :return: Subrack fan speed, in percent of the maximum values, for the 4 fans
        :rtype: list[float]
        """
        answer = []
        for fan_id in range(4):
            answer = answer + [self._hardware.GetFanSpeed(fan_id + 1)[1]]
        return answer


class FanMode(HardwareAttribute):
    def read_value(self):
        """
        :return: Subrack fan mode
        :rtype: list[float]
        """
        answer = []
        for fan_id in range(4):
            answer = answer + [self._hardware.GetFanMode(fan_id + 1)]
        return answer

    def write_value(self, mode):
        for fan_id in range(4):
            if mode[fan_id] == 0:
                mode_i = 0
            else:
                mode_i = 1
            self._hardware.SetFanMode(fan_id + 1, mode_i)
        return self.read_value()


class FanSpeed(HardwareAttribute):
    def read_value(self):
        """
        :return: Subrack fan speed, in RPM, for the 4 fans
        :rtype: list[float]
        """
        answer = []
        for fan_id in range(4):
            answer = answer + [self._hardware.GetFanSpeed(fan_id + 1)[0]]
        return answer


class TpmMCUTemperatures(HardwareAttribute):
    """
    TPM MCU temperatures, in celsius.
    Returns 8 values, 0.0 for boards not present or powered off
    """

    def read_value(self):
        """
        :return: TPM MCU temperature, in Celsius
        :rtype: list[float]
        """
        answer = [0.0] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                answer[tpm] = self._hardware.GetTPMMCUTemperature(tpm + 1)
        return answer


class TpmIPs(HardwareAttribute):
    """
    IP address of TPMs present on subrack.
    Returns 8 IP address, "0" for TPMs not powered off and "-1" for TPMs not present
    """

    def read_value(self):
        """
        :return: TPM IP
        :rtype: list[str]
        """
        answer = ["0"] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        tpm_status = byte_to_bool_array(self._hardware.GetTPMOnOffVect())
        for tpm in range(8):
            if tpm_detected[tpm] & tpm_status[tpm]:
                answer[tpm] = self._hardware.GetTPMIP(tpm + 1)
            elif tpm_status[tpm]:
                answer[tpm] = "-1"
        return answer


class TpmCurrents(HardwareAttribute):
    """
    TPM board current, in A.
    Returns 8 values, 0.0 for boards not present
    """

    def read_value(self):
        """
        :return: 8 values, 0.0 for boards not present
        :rvalue: list(float)
        """
        answer = [0.0] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                answer[tpm] = self._hardware.GetTPMCurrent(tpm + 1)
        return answer


class TpmVoltages(HardwareAttribute):
    """
    TPM board power supply voltages (V)
    """

    def read_value(self):
        """
        :return: 8 values, 0.0 for boards not present
        :rvalue: list(float)
        """
        answer = [0.0] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                answer[tpm] = self._hardware.GetTPMVoltage(tpm + 1)
        return answer


class TpmPowers(HardwareAttribute):
    """
    TPM board power usage (W)
    """

    def read_value(self):
        """
        :return: 8 values, 0.0 for boards not present
        :rvalue: list(float)
        """
        answer = [0.0] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                answer[tpm] = self._hardware.GetTPMPower(tpm + 1)
        return answer


class TpmSupplyFault(HardwareAttribute):
    """
    TPM supply fault status
    Returns 8 bool values, True if board supply fault has been triggered
    """

    answer = [0.0] * False

    def read_value(self):
        tpm_supply_fault = byte_to_bool_array(self._hardware.GetTPMSupplyFault())
        return tpm_supply_fault


class TpmOnOffVect(HardwareAttribute):
    """
    TPM board power status
    """

    def read_value(self):
        tpm_is_on = byte_to_bool_array(self._hardware.GetTPMOnOffVect())
        return tpm_is_on


class TpmPresent(HardwareAttribute):
    """
    TPM board presence
    Returns 8 values, True if board present and powered on
    """

    def read_value(self):
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        return tpm_detected


class PSFanSpeed(HardwareAttribute):
    def read_value(self):
        fan_speed = [
            self._hardware.GetPSFanSpeed(1),
            self._hardware.GetPSFanSpeed(2),
        ]
        return fan_speed


class PSCurrent(HardwareAttribute):
    def read_value(self):
        fan_speed = [
            self._hardware.GetPSIout(1),
            self._hardware.GetPSIout(2),
        ]
        return fan_speed


class PSPower(HardwareAttribute):
    def read_value(self):
        fan_speed = [
            self._hardware.GetPSPower(1),
            self._hardware.GetPSPower(2),
        ]
        return fan_speed


class PSVoltage(HardwareAttribute):
    def read_value(self):
        fan_speed = [
            self._hardware.GetPSVout(1),
            self._hardware.GetPSVout(2),
        ]
        return fan_speed

class TPM_Add_List(HardwareAttribute):
    """
    TPM IP Address Will Be Assigned.
    Returns 8 IP address, address will be assigned to each TPM in subrack slots
    """
    def read_value(self):
        ip_add_list = self._hardware.GetTPM_Add_List()
        return ip_add_list

class TPM_Temperature_Alarms(HardwareAttribute):
    """
    TPMs Temperature alarm status
    Returns 8 temeprature alarms
    """
    def read_value(self):
        temp_alms = self._hardware.Get_tpm_alarms_vector()[0]
        return temp_alms

class TPM_Voltage_Alarms(HardwareAttribute):
    """
    TPMs Voltage alarm status
    Returns 8 voltage alarms
    """
    def read_value(self):
        voltage_alms = self._hardware.Get_tpm_alarms_vector()[1]
        return voltage_alms

class CPLD_PLL_Locked(HardwareAttribute):
    """
    Subrack CPLD PLL Lock status
    Returns status of CPLD internal PLL lock
    """
    def read_value(self):
        cpld_pll_lock = self._hardware.GetCPLDLockedPLL()
        return cpld_pll_lock

class Subrack_PLL_Locked(HardwareAttribute):
    """
    Subrack PLL Lock status
    Returns status of Subrack PLL lock
    """
    def read_value(self):
        cpld_pll_lock = self._hardware.GetLockedPLL()
        return cpld_pll_lock

class Subrack_Timestamp(HardwareAttribute):
    """
    Subrack Time in timestamp
    Returns Time of Subrack in timrstamp format
    """
    def read_value(self):
        tstamp = self._hardware.Get_Subrack_TimeTS()
        return tstamp

class API_Version(HardwareAttribute):
    """
    API version
    Returns version of API
    """
    def read_value(self):
        version = self._hardware.Get_API_version()
        return version

class TPM_Temperatures(HardwareAttribute):
    """
    TPMs Temperature vectors
    Returns 8 TPMBoard temepratures , 8 TPM FPGA1 temperatures, 8 TPM FPGA2 temperatures
    """
    def read_value(self):
        board_temps, fpga1_temps,fpga2_temps = self._hardware.Get_TPM_temperature_vector()
        return board_temps, fpga1_temps,fpga2_temps

class ups_status(HardwareAttribute) :
    """
    UPS board status
    Returns UPS Board Status: ups_status = {"alarm":False,"warning":False,"charging":False}
    """
    def read_value(self):
        ups_status = self._hardware.GetUPSStatus()
        return ups_status

class SubrackHardware(HardwareThreadedDevice):
    def initialize(self, emulation=False):
        subrack = SubrackMngBoard(simulation=emulation)
        self.subrack = subrack
        
        # Add Commands
        self.add_command(PowerOnTpmCommand("turn_on_tpm", subrack, 1, blocking=True))
        self.add_command(PowerOffTpmCommand("turn_off_tpm", subrack, 1, blocking=True))
        self.add_command(IsTpmOnCommand("is_tpm_on", subrack, 1))
        self.add_command(AreTpmsOnCommand("are_tpms_on", subrack, 0))
        self.add_command(PowerUpCommand("turn_on_tpms", subrack, 0, blocking=True))
        self.add_command(PowerDownCommand("turn_off_tpms", subrack, 0, blocking=True))
        self.add_command(SetFanMode("set_fan_mode", subrack, 2))
        self.add_command(SetFanSpeed("set_subrack_fan_speed", subrack, 2))
        self.add_command(SetPSFanSpeed("set_power_supply_fan_speed", subrack, 2))
        self.add_command(TpmInfo("tpm_info", subrack, 1))
        self.add_command(GetHealthDict("get_health_dictionary", subrack, 1))
        self.add_command(GetHealthStatus("get_health_status", subrack, 1))

        # Add attributes
        self.add_attribute(
            BackplaneTemperature("backplane_temperatures", [0] * 2, subrack)
        )
        self.add_attribute(BoardTemperature("board_temperatures", [0] * 2, subrack))
        self.add_attribute(BoardCurrent("board_current", 0, subrack))
        self.add_attribute(FanSpeed("subrack_fan_speeds", [0] * 4, subrack))
        self.add_attribute(
            FanSpeedPercent("subrack_fan_speeds_percent", [0] * 4, subrack)
        )
        self.add_attribute(
            FanMode("subrack_fan_mode", [0] * 4, subrack)
        )  # , HardwareAttribute.HW_ATTR_RW, 4)) TODO
        self.add_attribute(TpmMCUTemperatures("tpm_mcu_temperatures", 0, subrack))
        self.add_attribute(TpmVoltages("tpm_voltages", 0, subrack))
        self.add_attribute(TpmCurrents("tpm_currents", 0, subrack))
        self.add_attribute(TpmIPs("tpm_ips", 0, subrack))
        self.add_attribute(TpmPowers("tpm_powers", 0, subrack))
        self.add_attribute(TpmPresent("tpm_present", 0, subrack))
        self.add_attribute(TpmSupplyFault("tpm_supply_fault", 0, subrack))
        self.add_attribute(TpmOnOffVect("tpm_on_off", 0, subrack))
        self.add_attribute(PSFanSpeed("power_supply_fan_speeds", 0, subrack))
        self.add_attribute(PSCurrent("power_supply_currents", 0, subrack))
        self.add_attribute(PSPower("power_supply_powers", 0, subrack))
        self.add_attribute(PSVoltage("power_supply_voltages", 0, subrack))
        self.add_attribute(TPM_Add_List("assigned_tpm_ip_adds", 0, subrack))
        self.add_attribute(TPM_Temperature_Alarms("tpms_temp_alarms", 0, subrack))
        self.add_attribute(TPM_Voltage_Alarms("tpms_voltage_alarms", 0, subrack))
        self.add_attribute(CPLD_PLL_Locked("cpld_pll_locked", 0, subrack))
        self.add_attribute(Subrack_PLL_Locked("subrack_pll_locked", 0, subrack))
        self.add_attribute(TPM_Temperatures("tpms_temperatures", 0, subrack))
        self.add_attribute(API_Version("api_version", 0, subrack))
        self.add_attribute(Subrack_Timestamp("subrack_timestamp", 0, subrack))

        self.subrack.Mng.write("Led.Led_3", 1) 

    def execute_command(self, command, params=None):
        try:
            answer = super().execute_command(command, params)
        except SubrackExecFault as message:
            answer = {
                "status": "ERROR",
                "command": command,
                "info": str(message),
                "retvalue": "",
            }
        except SubrackInvalidCmd as message:
            answer = {
                "status": "ERROR",
                "command": command,
                "info": str(message),
                "retvalue": "",
            }
        except SubrackInvalidParameter as message:
            answer = {
                "status": "ERROR",
                "command": command,
                "info": str(message),
                "retvalue": "",
            }
        return answer
