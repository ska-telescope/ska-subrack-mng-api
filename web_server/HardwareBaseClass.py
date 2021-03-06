"""
Package to implement simple device drivers. 
Each hardware driver is an instance of a HardwareBaseClass
It contains a set of HardwareCommand objects, which implement
actions (with optional parameters) and 
Hardware Attribute objects, which implement physical quantities.
The HardwareBaseClass is controlled using commands, or by setting 
attributes (if they are RW). It is monitored by reading attributes. 
Hardware objects, commands and attributes can be subclassed for specific
behaviors. 
"""

class HardwareCommand:
    """
    Command for a Hardware base class. Command has a name, has access to
    its base hardware (if useful), and can check the number of parameters
    """

    def __init__(self, name, hardware=None, num_params=0):
        """
        Initialization

        :param name: Command name. Used to call it
        :type name: str
        :param hardware: HardwareBaseClass object containing the parameter
        :param num_params: Number of parameters in the command call
        """
        self._name = name
        self._hardware = hardware
        self._num_params = num_params

    def do(self, params=None):
        """
        Execution method. Subclasses must override this to do real work

        :param params: Optional list of parameters
        :type params: list
        :return: Dictionary of returned response
        :rtype: dict
        """
        return {
            "status": "OK",
            "info": self._name + " completed OK",
            "command": self._name,
            "retvalue": "",
        }

    def name(self):
        """
        Returns the command name

        :return: Command name
        :rtype: str
        """
        return self._name


class HardwareAttribute:
    """
    Attribute for a HardwareBaseClass
    Attributes can be scalar or vector of fixed dimension, of arbitrary types
    Can be read/write or read only
    """

    HW_ATTR_RO = 0
    HW_ATTR_RW = 1

    def __init__(
        self, name, init_value, hardware=None, read_write=HW_ATTR_RO, num_params=1
    ):
        """
        Initialization

        :param name: Command name. Used to call it
        :type name: str
        :param init_value: Initialization value. Scalar or list
        :param hardware: HardwareBaseClass object containing the parameter
        :param num_params: Number of parameters in the command call
        """
        self._name = name
        self._value = init_value
        self._rw_mode = read_write
        self._num_params = num_params
        self._hardware = hardware
        self._lasterr = ""

    def read(self):
        """
        Read the attribute, formatting the response dictionary

        :return: Dictionary of returned response
        :rtype: dict
        """
        value = self.read_value()
        if value is None:
            status = "ERROR"
            info = self._lasterr
        else:
            self._value = value
            status = "OK"
            info = ""
        return {
            "status": status,
            "info": info,
            "attribute": self._name,
            "value": self._value,
        }

    def write(self, params):
        """
        write value(s) in params to the attribute

        :param params: Parameters to be written

        :return: dictionary for json answer
        :rtype: dict
        """
        # default answer (everything OK)
        status = "OK"
        info = "Setting attribute " + self._name + " OK"
        # check for read write permission
        if self._rw_mode == HardwareAttribute.HW_ATTR_RO:
            status = "ERROR"
            info = "Attempt to write in read-only attribute " + self._name
        elif type(params) == list:
            num_params = len(params)
            if num_params == self._num_params:
                value = self.write_value(params)
            else:
                status = "ERROR"
                info = "Wrong number of values for attribute " + self._name
        elif self._num_params == 1:
            value = self.write_value(params)
        else:
            status = "ERROR"
            info = "Wrong number of values for attribute " + self._name

        if value is None:
            status = "ERROR"
            info = self._lasterr
        else:
            self._value = value
            status = "OK"
            info = ""
        answer = {
            "status": status,
            "info": info,
            "attribute": self._name,
            "value": self._value,
        }
        return answer

    def name(self):
        """
        Returns the command name

        :return: Command name
        :rtype: str
        """
        return self._name

    def read_value(self):
        """
        Reads the actual value
        To be overrided in the subclass

        :return: Attribute true value, from real device
        """
        return self._value

    def write_value(self, values):
        """
        Writes the actual value
        To be overrided in the subclass

        :param value: Attribute true value, to real device
        """
        self._value = values


class ListAttributeCommand(HardwareCommand):
    """
    Command to list names of the Hardware class commands
    """

    def do(self, params=None):
        """
        :param params: Optional list of parameters
        :type params: list
        :return: Dictionary of returned response
        :rtype: dict
        """
        response = super().do(params)
        response["retvalue"] = list(self._hardware.attribute_dict.keys())
        return response


class ListCommandCommand(HardwareCommand):
    """
    Command to list names of the Hardware class attributes
    """

    def do(self, params=None):
        """
        :param params: Optional list of parameters
        :type params: list
        :return: Dictionary of returned response
        :rtype: dict
        """
        response = super().do(params)
        response["retvalue"] = list(self._hardware.command_dict.keys())
        return response


class GetAllAttributesCommand(HardwareCommand):
    """
    command which returns a dictionary of all attributes and their
    current values inthe 'value' field
    """

    def do(self, params=None):
        """
        :param params: Optional list of parameters
        :type params: list
        :return: Dictionary of returned response
        :rtype: dict
        """
        response = super().do(params)
        value = {}
        for attr in self._hardware.attribute_dict.keys():
            value[attr] = self._hardware.attribute_dict[attr].read_value()
        response["retvalue"] = value
        return response


class HardwareBaseDevice:
    """
    Server side of the hardware device. 
    """

    def __init__(self):
        self.command_dict = {}
        self.attribute_dict = {}
        self.add_command(ListAttributeCommand("list_attributes", self))
        self.add_command(ListCommandCommand("list_commands", self))
        self.add_command(GetAllAttributesCommand("get_all_attributes", self))

    def execute_command(self, command, params=None):
        """
        Execute a command with optional parameters

        :param command: Command name
        :type command: str
        :param params: Optional parameter, simple list or scalar

        :return: dictionary for json answer
        """
        if command in self.command_dict.keys():
            answer = self.command_dict[command].do(params)
        else:
            answer = {
                "status": "ERROR",
                "info": command + " not implemented",
                "command": command,
                "retvalue": "",
            }
        return answer

    def set_attribute(self, attribute, values):
        """
        Set attribute values

        :param attribute: Attribute name
        :type command: str
        :param values: Attribute values, simple list or scalar

        :return: dictionary for json answer
        """
        if attribute in self.attribute_dict.keys():
            answer = self.attribute_dict[attribute].write(values)
        else:
            answer = {
                "status": "ERROR",
                "info": attribute + " not present",
                "attribute": attribute,
                "retvalue": "",
            }
        return answer

    def get_attribute(self, attribute):
        """
        Get attribute values

        :param attribute: Attribute name
        :type command: str

        :return: dictionary for json answer
        """
        E
        if attribute in self.attribute_dict.keys():
            answer = self.attribute_dict[attribute].read()
        else:
            answer = {
                "status": "ERROR",
                "info": attribute + " not present",
                "attribute": attribute,
                "retvalue": "",
            }
        return answer

    def add_command(self, command):
        """
        Add a command to the command list

        :param command: Command object
        :type attribute: :py:class:`HardwareBase.HardwareCommand`

        :return: True if command canbe added, False otherwise
        :rtype: Bool
        """
        if issubclass(type(command), HardwareCommand):
            self.command_dict[command.name()] = command
            return True
        else
            return False

    def add_attribute(self, attribute):
        """
        Add an attribute to the command list

        :param attribute: Attribute object
        :type attribute: :py:class:`HardwareBase.HardwareAttribute`

        :return: True if command canbe added, False otherwise
        :rtype: Bool
        """
        if issubclass(type(attribute), HardwareAttribute):
            self.attribute_dict[attribute.name()] = attribute
            return True
        else
            return False
