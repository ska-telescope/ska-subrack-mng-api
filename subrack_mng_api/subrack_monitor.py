__author__ = 'Cristian Albanese'
"""This Script permit to manage OneWire read/writeoperation"""
import sys
import time
from optparse import OptionParser
from subrack_management_board import *

import terminaltables
import os
import sys
import termios, fcntl
import select
import struct
import select
import struct
import subprocess
import socket

import subprocess
import logging

reverseTPM = True

tpmison = [0, 0, 0, 0, 0, 0, 0, 0]
rpmfan = ['0', '0', '0', '0']
pwm_perc = ['0', '0', '0', '0']
tpm_v_reg = [0, 0, 0, 0, 0, 0, 0, 0,"V"]
tpm_p_reg = [0, 0, 0, 0, 0, 0, 0, 0,"W"]
tpm_a_reg = [0, 0, 0, 0, 0, 0, 0, 0,"A"]
temps = [0, 0, 0, 0, 0]
tpm_board_temp=[0,0,0,0,0,0,0,0]
tpm_mcu_temp=[0,0,0,0,0,0,0,0]
psu_volt=[0,0,"Vout (V)"]
psu_curr=[0,0,"Iout (V)"]
psu_pow=[0,0,"Pow (W)"]
psu_index=["PSU 1","PSU 2","MEAS"]



table_index = ['Board 1', 'Board 2', 'Board 3', 'Board 4', 'Board 5', 'Board 6', 'Board 7', 'Board 8']
table_index_pow = ['Board 1', 'Board 2', 'Board 3', 'Board 4', 'Board 5', 'Board 6', 'Board 7', 'Board 8',"MEAS"]
present_i = []
present = []
present_done = False

clear = lambda: os.system('clear') #on Linux System
subrack=SubrackMngBoard()




class KeyReader :
    '''
    Read keypresses one at a time, without waiting for a newline.
    echo: should characters be echoed?
    block: should we block for each character, or return immediately?
           (If !block, we'll return None if nothing is available to read.)
    '''
    def __init__(self, echo=False, block=True):
        '''Put the terminal into cbreak and noecho mode.'''
        self.fd = sys.stdin.fileno()

        self.block = block

        self.oldterm = termios.tcgetattr(self.fd)
        self.oldflags = fcntl.fcntl(self.fd, fcntl.F_GETFL)

        # Sad hack: when the destructor __del__ is called,
        # the fcntl module may already be unloaded, so we can no longer
        # call fcntl.fcntl() to set the terminal back to normal.
        # So just in case, store a reference to the fcntl module,
        # and also to termios (though I haven't yet seen a case
        # where termios was gone -- for some reason it's just fnctl).
        # The idea of keeping references to the modules comes from
        # http://bugs.python.org/issue5099
        # though I don't know if it'll solve the problem completely.
        self.fcntl = fcntl
        self.termios = termios

        newattr = termios.tcgetattr(self.fd)
        # tcgetattr returns: [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
        # where cc is a list of the tty special characters (length-1 strings)
        # except for cc[termios.VMIN] and cc[termios.VTIME] which are ints.
        self.cc_save = newattr[6]
        newattr[3] = newattr[3] & ~termios.ICANON
        if not echo:
            newattr[3] = newattr[3] & ~termios.ECHO

        if block and False:
            # VMIN and VTIME are supposed to let us do blocking reads:
            # VMIN is the minimum number of characters before it will return,
            # VTIME is how long it will wait if for characters < VMIN.
            # This is documented in man termios.
            # However, it doesn't work in python!
            # In Python, read() never returns in non-canonical mode;
            # even typing a newline doesn't help.
            cc = self.cc_save[:]   # Make a copy so we can restore VMIN, VTIME
            cc[termios.VMIN] = 1
            cc[termios.VTIME] = 0
            newattr[6] = cc
        else:
            # Put stdin into non-blocking mode.
            # We need to do this even if we're blocking, see above.
            fcntl.fcntl(self.fd, fcntl.F_SETFL, self.oldflags | os.O_NONBLOCK)

        termios.tcsetattr(self.fd, termios.TCSANOW, newattr)

    def __del__(self):
        '''Reset the terminal before exiting the program.'''
        self.termios.tcsetattr(self.fd, self.termios.TCSAFLUSH, self.oldterm)
        self.fcntl.fcntl(self.fd, self.fcntl.F_SETFL, self.oldflags)

    def getch(self):
        '''Read keyboard input, returning a string.
           Note that one key may result in a string of more than one character,
           e.g. arrow keys that send escape sequences.
           There may also be multiple keystrokes queued up since the last read.
           This function, sadly, cannot read special characters like VolumeUp.
           They don't show up in ordinary CLI reads -- you have to be in
           a window system like X to get those special keycodes.
        '''
        # Since we can't use the normal cbreak read from python,
        # use select to see if there's anything there:
        if self.block:
            inp, outp, err = select.select([sys.stdin], [], [])
        try:
            return sys.stdin.read()
        except (IOError, TypeError) as e:
            return None

def partial_reverse(list_, from_, to):
    (list_[4], list_[7]) = (list_[7], list_[4])
    (list_[5], list_[6]) = (list_[6], list_[5])


def presentdata():
    global present
    global tpmison
    present_i = subrack.GetTPMPresent()
    # Put present in a list
    present = [int(x) for x in '{:08b}'.format(present_i)]
    # Reverse list (bit field 0 as tpm 1)
    present.reverse()

    tpmison_i= subrack.GetTPMOnOffVect()
    # Put present in a list
    tpmison = [int(x) for x in '{:08b}'.format(tpmison_i)]
   #print tpmison
    # Reverse list (bit field 0 as tpm 1)
    tpmison.reverse()


def tab_present():
    table_present = [
        table_index,
        present,
        tpmison
    ]
    clear()
    tablepres = terminaltables.AsciiTable(table_present)
    tablepres.title = "TPM Present & ON"
    print(tablepres.table)


def fandata():
    for i in range (0,4):
        try:
            #subrack.SetFanMode(i+1, 0)
            rpmfan[i],pwm_perc[i]=subrack.GetFanSpeed(i+1)
        except:
            print("subrack_monitor fandata: error while reading temperature")


def tab_fandata():
    fan_data = [
        ['Fan 1', 'Fan 2', 'Fan 3', "Fan 4"],
        rpmfan,
        [str(int(pwm_perc[0])) + "%", str(int(pwm_perc[1])) + "%", str(int(pwm_perc[2])) + "%", str(int(pwm_perc[3])) + "%"]
    ]
    tablefan = terminaltables.AsciiTable(fan_data)
    tablefan.title = "RPM Fan Speed (Rpm) & PWM (%)"
    print(tablefan.table)


def voltagedata():
    presentdata()
    for i in range (1,8):
        if present[i-1]!=0:
            tpm_v_reg[i-1]=subrack.GetTPMVoltage(i)
            tpm_a_reg[i-1] = subrack.GetTPMCurrent(i)
            tpm_p_reg[i-1] = subrack.GetTPMPower(i)
        else:
            tpm_v_reg[i-1]=0
            tpm_a_reg[i-1] = 0
            tpm_p_reg[i-1] =0
def tab_voltagedata():
    table_tpmpow = [
        table_index_pow,
        tpm_v_reg,
        tpm_a_reg,
        tpm_p_reg,
    ]
    tabletpmpow = terminaltables.AsciiTable(table_tpmpow)
    tabletpmpow.title = "Board Powers (Voltage, Current, Power)"
    print(tabletpmpow.table)

def tempdata():
    temps[0],temps[1],temps[2],temps[3]=subrack.GetSubrackTemperatures()
    p = subprocess.Popen("cat /sys/class/thermal/thermal_zone0/temp", stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    temps[4]= str(float(output)/1000)

def tab_tempdata():
    table_brdtmp = [
        ['Mng1', 'Mng2', 'Bckp1', 'Bckp2', 'CPU'],
        temps
    ]
    tablebrdtmp = terminaltables.AsciiTable(table_brdtmp)
    tablebrdtmp.title = "Subrack Temperatures (Deg)"
    print(tablebrdtmp.table)

def tpmtempdata():
    presentdata()
    for i in range (0,8):
        if (present[i] and tpmison[i])==1:
            #print "i %d present[i] %d tpmison[i] %d (present[i] and tpmison[i]) %d " %(i, present[i],tpmison[i],(present[i] and tpmison[i]) )
            tpm_board_temp[i]=subrack.GetTPMTemperature(i+1,forceread=True)
            tpm_mcu_temp[i]=subrack.GetTPMMCUTemperature(i+1,forceread=True)
        else:
            tpm_board_temp[i]=0
            tpm_mcu_temp[i]=0


def tab_tpmtempdata():
    table_tpmtmp = [
        table_index,
        tpm_board_temp,
        tpm_mcu_temp
    ]
    tabletpmtmp = terminaltables.AsciiTable(table_tpmtmp)
    tabletpmtmp.title = "TPM Temperatures, board sensor & mcu sensor (Deg)"
    print(tabletpmtmp.table)

def psudata():
    for i in range (0,2):
        psu_volt[i]=subrack.GetPSVout(i+1)
        psu_curr[i]=subrack.GetPSIout(i+1)
        psu_pow[i]=subrack.GetPSPower(i+1)



def tab_psudata():
    table_psu = [
        psu_index,
        psu_volt,
        psu_curr,
        psu_pow
        #['PSU', 'Voltage Out', 'Amperage Out', 'Power Out'],
        #['PSU 0', str(float("{0:.2f}".format(ps0_vout))) + "V", str(ps0_iout) + "A", str(float("{0:.2f}".format(ps0_iout * ps0_vout))) + "W"],
        #['PSU 1', str(float("{0:.2f}".format(ps1_vout))) + "V", str(ps1_iout) + "A", str(float("{0:.2f}".format(ps1_iout * ps1_vout))) + "W"],
        #['Total', str(float("{0:.2f}".format((ps1_vout+ps0_vout)/2))) + "V", str(ps1_iout + ps0_iout) + "A", str(float("{0:.2f}".format((ps0_iout * ps0_vout)+(ps1_iout * ps1_vout)))) + "W"]
    ]
    tablepsu = terminaltables.AsciiTable(table_psu)
    tablepsu.title = "PSU Data"
    print(tablepsu.table)

parser = OptionParser()

parser.add_option("-s", "--show",
                action="store_true", dest="show_measure", default=False,
                help="dump all fpga registers & flags")
parser.add_option("-r", "--remot",
                action="store_true", dest="remote", default=False,
                help="connect and send data to client")





(options, args) = parser.parse_args()

do_block = False
keyreader = KeyReader(echo=False, block=do_block)

# Set logging
def set_logging(level):
    log = logging.getLogger('')
    if(level=="INFO"):
        log.setLevel(logging.INFO)
    if(level=="ERROR"):
        log.setLevel(logging.ERROR)
    if(level=="DEBUG"):
        log.setLevel(logging.DEBUG)
    line_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(line_format)
    log.addHandler(ch)

#set_logging("DEBUG")



subrack.PllInitialize()

if options.remote:
    HOST = '10.0.10.20'  # Standard loopback interface address (localhost)
    PORT = 1234  # Port to listen on (non-privileged ports are > 1023)
    NCLIENT = 1
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(NCLIENT)
    try:
        client, address = server.accept()
        if len(address) > 0:
            logging.info("Connected to : %s:%d" % (address[0], address[1]))
        while True:
            data = client.recv(1024)
            #log.info("RECEIVED CMD: " + data + " (%d chars)" % (len(data)))
            if not data:
                break
            cmd = data.split()
            if cmd[0] == "ACQUIRE":
                presentdata()
                fandata()
                voltagedata()
                tempdata()
                psudata()
                # Message to the client
                msg = ""
                # Mgm Temps
                b = struct.pack(">dddd", float(temps[0]), float(temps[1]), float(temps[2]), float(temps[3]))
                msg += b
                # Fans RPM
                b = struct.pack(">dddddd", float(pwm_perc[0]), float(pwm_perc[1]), float(rpmfan[0]), float(rpmfan[1]), float(rpmfan[2]), float(rpmfan[3]))
                msg += b
                # TPM Power
                for z in range(8):
                    b = struct.pack(">d", float(tpm_p_reg[z][:-1]))
                    msg += b
                # Subrack Power
                b = struct.pack(">dddd", float(psu_volt[0]), float(psu_curr[0]), float(psu_volt[1]), float(psu_curr[1]))
                msg += b
                # Message Complete
                #
                # Data Size
                #   - Mgm Temps 4
                #   - Fans RPM  4
                #   - TPM Power 8
                client.sendall(msg)
                logging.info("AQUIRE Request Answered")
                tab_present()
                tab_voltagedata()
                tab_fandata()
                tab_tempdata()
                #tab_tpmtempdata()
                tab_psudata()

    except KeyboardInterrupt:
        logging.info("\nTerminated")
elif options.show_measure:
    while (1):
        presentdata()
        fandata()
        voltagedata()
        tempdata()
        psudata()
        #tpmtempdata()
        tab_present()
        tab_voltagedata()
        tab_fandata()
        tab_tempdata()
        #tab_tpmtempdata()
        tab_psudata()
        time.sleep(2)
else:
    set_logging("INFO")




