"""
LFAA SPS Subrack control board hardware driver. 
"""
from HardwareBaseClass import *
from HarwareThreadedClass import *
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
        
        :param tpm_id: index of TPM to power on (0-7) or list of indexes 
        : type tpm_id: str, list(str)

        :return: dictionary with HardwareCommand response. List of TPM On status
        :rtype: dict
        """

        if type(tpm_id) == list:
            for tpm_slot_id in tpm_id:
                self._hardware.PowerOnTPM(int(tpm_slot_id+1))
                if self._abort:
                    break
        else:
            tpm_slot_id = int(tpm_id)
            self._hardware.PowerOnTPM(tpm_slot_id+1)
        tpm_is_on = self._hardware.GetTPMOnOffVect()
        return


class PowerOffTpmCommand(ThreadedHardwareCommand):
    """
    Power Off TPM command. Switches off a single or multiple TPM
    """
    def thread(self, tpm_id):
        """
        Power off TPMs
        
        :param tpm_id: index of TPM to power on (0-7) or list of indexes 
        : type tpm_id: str, list(str)

        :return: dictionary with HardwareCommand response. List of TPM On status
        :rtype: dict
        """
        if type(tpm_id) == list:
            for tpm_slot_id in tpm_id:
                self._hardware.PowerOffTPM(int(tpm_slot_id+1))
                if self._abort:
                    break
        else:
            tpm_slot_id = int(tpm_id)
            self._hardware.PowerOffTPM(tpm_slot_id+1)
        tpm_is_on = self._hardware.GetTPMOnOffVect()
        return


class IsTpmOnCommand(HardwareCommand):
    """
    Check TPM power status
    """
    def do(self, params):
        """
        Check power status of TPMs
            
        :param tpm_id: index of TPM to check (0-7)
        : type tpm_id: str

        :return: dictionary with HardwareCommand response. Integer retvalue
        :rtype: dict
        """

        answer = super().do()
        tpm_slot_id = int(params)
        tpm_on = self._hardware.GetTPMOnOffVect()
        if tpm_on & (1 << tpm_slot_id) != 0:
            retval = 1
        else:
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
        for tpm in range(8):
            if tpm_detected[tpm]:
                self._hardware.PowerOnTPM(tpm + 1)
                if self._abort:
                    break
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
        for tpm in range(8):
            if tpm_detected[tpm]:
                self._hardware.PowerOffTPM(tpm + 1)
                if self._abort:
                    break
        return


class SetFanMode(HardwareCommand):
    """ 
    Set fan mode (manual, auto) 
    """
    def do(self, params):
        """ 
        :param params: [0]: Fan ID (in range 0-3), [1]: mode [MANUAL|AUTO]

        :return: dictionary with HardwareCommand response. 
        :rtype: dict
        """
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requres 2 parameters"
        else:
            fan_id = int(params[0])+1
            fan_mode = params[1]
            if (fan_id >= 1) & (fan_id <= 4):
                self._hardware.SetFanMode(fan_id, fan_mode)
            else:
                answer['status'] = 'ERROR'
                answer['info'] = 'Fan ID must be between 0 and 3'
        return answer


class SetFanSpeed(HardwareCommand):
    """ 
    Set cabinet fan speed (0-100) 
    """
    def do(self, params):
        """ 
        :param params: [0]: Fan ID (in range 0-3), [1]: speed (percentage)

        :return: dictionary with HardwareCommand response. Retval is actual speed 
        :rtype: dict
        """
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requres 2 parameters"
        else:
            fan_id = int(params[0])+1
            fan_speed = params[1]
            if (fan_id >= 1) & (fan_id <= 4):
                self._hardware.SetFanSpeed(fan_id, fan_speed)
            else:
                answer['status'] = 'ERROR'
                answer['info'] = 'Fan ID must be between 0 and 3'
        return answer


class SetPSFanSpeed(HardwareCommand):
    """ 
    Set Power Supply fan speed (0-100) 
    """
    def do(self, params):
        """ 
        :param params: [0]: Fan ID (in range 0-1), [1]: speed (percentage)

        :return: dictionary with HardwareCommand response. Retval is actual speed 
        :rtype: dict
        """
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requres 2 parameters"
        else:
            fan_id = int(params[0])+1
            fan_speed = int(params[1])
            if (fan_id >= 1) & (fan_id <= 2):
                self._hardware.SetPSFanSpeed(fan_id, fan_speed)
            else:
                answer['status'] = 'ERROR'
                answer['info'] = 'Fan ID must be between 0 and 1'
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


class TpmTemperatures(HardwareAttribute):
    """
    TPM bpard temperatures, in celsius. 
    Returns 8 values, 0.0 for boards not present
    """
    def read_value(self):
        """
        :return: TPM board temperature, in Celsius
        :rtype: list[float]
        """
        answer = [0.0] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                answer[tpm] = self._hardware.GetTPMTemperature(tpm + 1)
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
        :rvalue: list(float\)
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


class SubrackHardware(HardwareThreadedDevice):
    def initialize(self, emulation=False):
        subrack = SubrackMngBoard(simulation=emulation)
        self.subrack = subrack
        # Actual initialization
        subrack.PllInitialize()
        # power on the backplane
        if subrack.Bkpln.get_bkpln_is_onoff()==0:
            subrack.Bkpln.power_on_bkpln()
        if subrack.powermon_cfgd==False:
            subrack.SubrackInitialConfiguration()


        # Add Commands
        self.add_command(PowerOnTpmCommand("turn_on_tpm", subrack, 1, True))
        self.add_command(PowerOffTpmCommand("turn_off_tpm", subrack, 1, True))
        self.add_command(IsTpmOnCommand("is_tpm_on", subrack, 1))
        self.add_command(PowerUpCommand("turn_on_tpms", subrack, 0, True))
        self.add_command(PowerDownCommand("turn_off_tpms", subrack, 0, True))
        self.add_command(SetFanMode("set_fan_mode", subrack, 2))
        self.add_command(SetFanSpeed("set_subrack_fan_speed", subrack, 2))
        self.add_command(SetPSFanSpeed("set_power_supply_fan_speed", subrack, 2))
        # Add attributes
        self.add_attribute(BackplaneTemperature("backplane_temperatures", 0, subrack))
        self.add_attribute(BoardTemperature("board_temperatures", 0, subrack))
        self.add_attribute(BoardCurrent("board_current", 0, subrack))
        self.add_attribute(FanMode("fan_mode", 0, subrack))
        self.add_attribute(FanSpeed("fan_speed", 0, subrack))
        self.add_attribute(FanSpeedPercent("fan_speed_percent", 0, subrack))
        self.add_attribute(TpmTemperatures("tpm_temperatures", 0, subrack))
        self.add_attribute(TpmVoltages("tpm_voltages", 0, subrack))
        self.add_attribute(TpmCurrents("tpm_currents", 0, subrack))
        self.add_attribute(TpmPowers("tpm_powers", 0, subrack))
        self.add_attribute(TpmPresent("tpm_present", 0, subrack))
        self.add_attribute(TpmSupplyFault("tpm_supply_fault", 0, subrack))
        self.add_attribute(TpmOnOffVect("tpm_on_off", 0, subrack))
        self.add_attribute(PSFanSpeed("power_supply_fan_speeds", 0, subrack))
        self.add_attribute(PSCurrent("power_supply_currents", 0, subrack))
        self.add_attribute(PSPower("power_supply_powers", 0, subrack))
        self.add_attribute(PSVoltage("power_supply_voltages", 0, subrack))

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
