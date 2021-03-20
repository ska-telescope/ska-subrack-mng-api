from HardwareBaseClass import *
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


class PowerOnTpmCommand(HardwareCommand):
    def do(self, params):
        answer = super().do()
        if type(params) == list:
            for tpm_slot_id in params:
                self._hardware.PowerOnTPM(int(tpm_slot_id))
        else:
            tpm_slot_id = int(params)
            self._hardware.PowerOnTPM(tpm_slot_id)
        tpm_is_on = self._hardware.GetTPMOnOffVect()
        return answer


class PowerOffTpmCommand(HardwareCommand):
    def do(self, params):
        answer = super().do()
        if type(params) == list:
            for tpm_slot_id in params:
                self._hardware.PowerOffTPM(int(tpm_slot_id))
        else:
            tpm_slot_id = int(params)
            self._hardware.PowerOffTPM(tpm_slot_id)
        return answer


class IsTpmOnCommand(HardwareCommand):
    def do(self, params):
        answer = super().do()
        tpm_slot_id = int(params)
        tpm_on = self._hardware.GetTPMOnOffVect(tpm_slot_id)
        if tpm_on & (1 << tpm_slot_id) != 0:
            retval = 1
        else:
            retval = 0
        answer["retvalue"] = retval
        return answer


class PowerUpCommand(HardwareCommand):
    def do(self, params):
        answer = super().do()
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                self._hardware.PowerOnTPM(tpm + 1)
        return answer


class PowerDownCommand(HardwareCommand):
    def do(self, params):
        answer = super().do()
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                self._hardware.PowerOffTPM(tpm + 1)
        return answer

class AreTpmsOnCommand(HardwareCommand):
    def do(self, params):
        answer = super().do()
        tpm_on_list = byte_to_bool_array(self._hardware.GetTPMOnOffVect())
        answer.retvalue = tpm_on_list
        return answer

class SetFanMode(HardwareCommand):
    def do(self, params):
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requres 2 parameters"
        else:
            fan_id = params[0]
            fan_mode = params[1]
            self._hardware.SetFanMode(fan_id, fan_speed)
        return answer


class SetFanSpeed(HardwareCommand):
    def do(self, params):
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requres 2 parameters"
        else:
            fan_id = params[0]
            fan_speed = params[1]
            self._hardware.SetFanSpeed(fan_id, fan_speed)
        return answer


class SetPSFanSpeed(HardwareCommand):
    def do(self, params):
        answer = super().do()
        if (type(params) == list) & (len(params) < 2):
            answer["status"] = "ERROR"
            answer["info"] = "Command requres 2 parameters"
        else:
            fan_id = params[0]
            fan_speed = params[1]
            self._hardware.SetPSFanSpeed(fan_id, fan_speed)
        return answer


# Attributes


class BackplaneTemperature(HardwareAttribute):
    def read_value(self):
        temperature = self._hardware.GetSubrackTemperatures()
        answer = temperature[2:4]
        return answer


class BoardCurrent(HardwareAttribute):
    def read_value(self):
        current1 = self._hardware.GetPSIout(1)
        current2 = self._hardware.GetPSIout(2)
        return current1 + current2


class BoardTemperature(HardwareAttribute):
    def read_value(self):
        temperature = self._hardware.GetSubrackTemperatures()
        answer = temperature[0:2]
        return answer


class BoardCurrent(HardwareAttribute):
    def read_value(self):
        current1 = self._hardware.GetPsIout(1)
        current2 = self._hardware.GetPsIout(2)
        return current1 + current2


class FanSpeedPercent(HardwareAttribute):
    def read_value(self):
        answer = []
        for fan_id in range(4):
            answer = answer + [self._hardware.GetFanSpeed(fan_id + 1)[1]]
        return answer

class FanMode(HardwareAttribute):
    def read_value(self):
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
        answer = []
        for fan_id in range(4):
            answer = answer + [self._hardware.GetFanSpeed(fan_id + 1)[0]]
        return answer


class TpmTemperatures(HardwareAttribute):
    def read_value(self):
        answer = [0.0] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                answer[tpm] = self._hardware.GetTPMTemperature(tpm + 1)
        return answer


class TpmCurrents(HardwareAttribute):
    def read_value(self):
        answer = [0.0] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                answer[tpm] = self._hardware.GetTPMCurrent(tpm + 1)
        return answer


class TpmVoltages(HardwareAttribute):
    def read_value(self):
        answer = [0.0] * 8
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMPresent())
        for tpm in range(8):
            if tpm_detected[tpm]:
                answer[tpm] = self._hardware.GetTPMVoltage(tpm + 1)
        return answer


class TpmSupplyFault(HardwareAttribute):
    def read_value(self):
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMSupplyFault())
        return tpm_detected


class TpmOnOffVect(HardwareAttribute):
    def read_value(self):
        tpm_detected = byte_to_bool_array(self._hardware.GetTPMOnOffVect())
        return tpm_detected


class TpmPresent(HardwareAttribute):
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


class SubrackHardware(HardwareBaseDevice):
    def initialize(self, emulation=False):
        subrack = SubrackMngBoard(simulation=emulation)
        self.subrack = subrack
        # Actual initialization
        subrack.PllInitialize()

        # Add Commands
        self.add_command(PowerOnTpmCommand("turn_on_tpm", subrack, 1))
        self.add_command(PowerOffTpmCommand("turn_off_tpm", subrack, 1))
        self.add_command(IsTpmOnCommand("is_tpm_on", subrack, 1))
        self.add_command(AreTpmsOnCommand("are_tpms_on", subrack, 0))
        self.add_command(PowerUpCommand("turn_on_tpms", subrack, 0))
        self.add_command(PowerDownCommand("turn_off_tpms", subrack, 0))
        self.add_command(SetFanMode("set_fan_mode", subrack, 2))
        self.add_command(SetFanSpeed("set_subrack_fan_speed", subrack, 2))
        self.add_command(SetPSFanSpeed("set_power_supply_fan_speed", subrack, 2))
        # Add attributes
        self.add_attribute(BackplaneTemperature("backplane_temperatures", 
            [0]*2, subrack))
        self.add_attribute(BoardTemperature("board_temperatures", [0]*2, subrack))
        self.add_attribute(BoardCurrent("board_current", 0, subrack))
        self.add_attribute(FanSpeed("subrack_fan_speed", [0]*4, subrack))
        self.add_attribute(FanSpeedPercent("subrack_fan_speed_percent", 
            [0]*4, subrack))
        self.add_attribute(FanMode( "subrack_fan_mode", 
            [0]*4, subrack, HardwareAttribute.HW_ATTR_RW, 4))
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
                "info": message,
                "retvalue": "",
            }
        except SubrackInvalidCmd as message:
            answer = {
                "status": "ERROR",
                "command": command,
                "info": message,
                "retvalue": "",
            }
        except SubrackInvalidParameter as message:
            answer = {
                "status": "ERROR",
                "command": command,
                "info": message,
                "retvalue": "",
            }
        return answer
