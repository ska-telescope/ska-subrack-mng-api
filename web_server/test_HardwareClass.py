from HardwareBaseClass import *
from HardwareThreadedClass import *
import time

class DummyThreadedCommand(ThreadedHardwareCommand):
    def do(self,params):
        print('Do method for command ' + self._name)
        return super().do(params)

    def thread(self,params):
        for i in range(params): 
            print('thread: i='+str(i))
            self._hardware.set_attribute(self._name, i)
            time.sleep(1)
            if self._abort:
                print('thread: aborting')
                break
        self._completed = True


def test_HardwareClass():
    device = HardwareThreadedDevice()
    device.add_attribute(HardwareAttribute(
        'start', 0,
        read_write=HardwareAttribute.HW_ATTR_RW))
    device.add_attribute(HardwareAttribute(
         'blocking', 0,
        read_write=HardwareAttribute.HW_ATTR_RW))
    device.add_command(DummyThreadedCommand('start', device))
    device.add_command(DummyThreadedCommand('blocking', device, 0, True))

    attributes = device.execute_command('list_attributes')['retvalue']
    commands = device.execute_command('list_commands')['retvalue']
    print(str(commands))
    print(str(device.execute_command('start', 4)))

    for i in range(6):
        resp = device.get_attribute('start')
        resp2 = device.execute_command('command_completed', 'start')
        print(resp2['retvalue'] + ' ' + resp['status'] + ' ' + str(resp['value']))
        time.sleep(1)

    print(str(device.execute_command('start', 4)))
    for i in range(6):
        resp = device.get_attribute('start')
        resp2 = device.execute_command('command_completed', 'start')
        print(resp2['retvalue'] + ' ' + resp['status'] + ' ' + str(resp['value']))
        if i == 2:
            print(str(device.execute_command('abort_command', 'start')))
        time.sleep(1)

    print(str(device.execute_command('blocking', 4)))
    for i in range(6):
        resp = device.get_attribute('blocking')
        resp2 = device.execute_command('command_completed', 'blocking')
        print(resp2['retvalue'] + ' ' + resp['status'] + ' ' + str(resp['value']))
        time.sleep(1)

    print(str(device.execute_command('blocking', 4)))
    for i in range(12):
        resp = device.get_attribute('blocking')
        resp2 = device.execute_command('command_completed', 'blocking')
        print(resp2['retvalue'] + ' ' + resp['status'] + ' ' + str(resp['value']))
        if i == 2:
            print(str(device.execute_command('abort_command', 'blocking')))
        time.sleep(1)

