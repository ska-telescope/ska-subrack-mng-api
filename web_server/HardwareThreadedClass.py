from HardwareBaseClass import *
import threading

"""
Package to implement simple device drivers with the possibility to 
start a thread for long time to complete. Multiple threads can be started, 
aborted and checked for completion, or the whole driver can be locked until
the thread has completed. 
Each hardware driver is an instance of a HardwareBaseClass
It contains a set of HardwareCommand objects, which implement
actions (with optional parameters) and 
Hardware Attribute objects, which implement physical quantities.
The HardwareBaseClass is controlled using commands, or by setting 
attributes (if they are RW). It is monitored by reading attributes. 
Hardware objects, commands and attributes can be subclassed for specific
behaviors. 
"""


class ThreadedHardwareCommand(HardwareCommand):
    """
    An hardware command which requires long time to complete.
    A thread is started to execute the command. The thread must contain
    frequent checkpoints, where the _abort flag is checked and the
    action stopped if this is set.
    The completed() method checks for completion of the thread.
    """

    def __init__(self, name, hardware=None, num_params=0, blocking=False):
        """
        Initialization

        :param name: Command name. Used to call it
        :type name: str
        :param hardware: HardwareBaseClass object containing the parameter
        :param num_params: Number of parameters in the command call
        :param blocking: Whether the thread must block other command execution
        """
        super().__init__(name, hardware, num_params)
        self._thread = None
        self._abort = False
        self._completed = True
        self._blocking = blocking

    def do(self, params):
        """
        Command execution.
        Starts a thread and sets internal atributes to
        :param params: Command parameters
        :return: Dictionary of returned response
        :rtype: dict
        """

        answer = super().do(params)
        if self._completed == True:
            self._abort = False
            self._completed = False
            self._thread = threading.Thread(target=self.thread, args=(params,))
            self._thread.start()
            answer["status"] = "STARTED"
        else:
            answer["status"] = "ERROR"
            answer["info"] = "Command " + self._name + " still running"
        return answer

    def thread(self, params):
        """
        Execution thread. Must periodically check self._abort
        with maximum execution time of approx 1 second between checkpoints
        Terminates setting self._completed True.
        """
        self._completed = True

    def abort(self):
        """
        abort the current thread.
        Just sets the abort flag, and waits for the thread to complete
        """
        self._abort = True
        if self._thread is not None:
            self._thread.join()
        self._thread = None
        self._completed = True

    def completed(self):
        """
        checks whether the current thread has completed
        If it has, joins the thread (to free resources)
        :return: Whether the thread has completed
        :rtype: Bool
        """
        if self._completed:
            if not (self._thread is None):
                self._thread.join()
                self._thread = None
        return self._completed

    def is_blocking(self):
        """
        :return: Whether the command requires blocking of the device
        :rtype: Bool
        """
        return self._blocking


class AbortCommand(HardwareCommand):
    """
    Abort a thread (if specfied in the parameter) or the blocking thread
    """

    def do(self, param=None):
        """
        :param: Command to abort or None
        :type: class.ThreadedHardwareCommand
        """
        answer = super().do()
        device = self._hardware
        if device._blocked:
            if device._runningCommand is None:
                pass
            else:
                device._runningCommand.abort()
                device._runningCommand = None
                device._blocked = False
        elif param in device.command_dict.keys():
            command = device.command_dict[param]
            if issubclass(type(command), ThreadedHardwareCommand):
                command.abort()
        else:
            answer["status"] = "ERROR"
            answer["info"] = command + " not implemented"

        return answer


class IsCompletedCommand(HardwareCommand):
    """
    check if a specific command thread (if specified in the parameter)
    or the blocking thread is currently running
    """

    def do(self, param=None):
        """
        :param: Command to check or None
        :type: class.ThreadedHardwareCommand
        """
        answer = super().do()
        device = self._hardware
        completed = False
        if param is None:
            if device._blocked:
                if device._runningCommand is None:
                    pass
                else:
                    completed = device._runningCommand.completed()
            if not running:
                device._runningCommand = None
                device._blocked = False

        elif param in device.command_dict.keys():
            command = device.command_dict[param]
            if issubclass(type(command), ThreadedHardwareCommand):
                completed = command.completed()

        answer["retvalue"] = str(completed)
        return answer


class HardwareThreadedDevice(HardwareBaseDevice):
    """"""

    def __init__(self):
        super().__init__()
        self._blocked = False
        self._runningCommand = None
        self.add_command(AbortCommand("abort_command", self))
        self.add_command(IsCompletedCommand("command_completed", self))

    def execute_command(self, command, params=None):
        """
        Execute a command with optional parameters
        Checks if the device is blocked before allowing it.
        Otherwise, checks if the thread is completed.
        If this is blocked, only abort or command is running are allowed.
        If the command is a Threaded command, and is blocking,
        set blocking atributes for the device.

        :param command: Command name
        :type command: str
        :param params: Optional parameter, simple list or scalar

        :return: dictionary for json answer
        """
        if command in self.command_dict.keys():
            cmdObj = self.command_dict[command]
            blocked = False
            if not (self._runningCommand is None):
                if not self._runningCommand.completed():
                    blocked = True
            if blocked:
                if (command == "abort_command") | (command == "command_completed"):
                    pass
                else:
                    return {
                        "status": "ERROR",
                        "info": self._runningCommand.name() + " still running",
                        "command": command,
                        "retvalue": "",
                    }
            if issubclass(type(cmdObj), ThreadedHardwareCommand):
                if cmdObj.is_blocking():
                    self._blocked = True
                    self._runningCommand = cmdObj
            answer = cmdObj.do(params)
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

        :return: dictionary for json answer
        """
        blocked = False
        if not (self._runningCommand is None):
            if not self._runningCommand.completed():
                blocked = True
        if blocked:
            answer = {
                "status": "ERROR",
                "info": self._runningCommand.name() + " still running",
                "attribute": attribute,
                "value": "",
            }
        else:
            answer = super().set_attribute(attribute, values)
        return answer

    def get_attribute(self, attribute):
        """
        Get attribute values

        :param attribute: Attribute name
        :type command: str

        :return: dictionary for json answer
        """

        blocked = False
        if not (self._runningCommand is None):
            if not self._runningCommand.completed():
                blocked = True
        if blocked:
            answer = {
                "status": "ERROR",
                "info": self._runningCommand.name() + " still running",
                "attribute": attribute,
                "value": "",
            }
        else:
            answer = super().get_attribute(attribute)
        return answer
