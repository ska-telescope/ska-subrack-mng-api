__author__ = 'Cristian Albanese'
"""This Script to monitor subrack status"""
import sys
import time
from optparse import OptionParser

import terminaltables
import os
import sys
import termios, fcntl
import select
import struct
import subprocess

reverseTPM = True



tpmison = [0, 0, 0, 0, 0, 0, 0, 0]
present_i = []
present = []
present_done = False

clear = lambda: os.system('clear') #on Linux System

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

def search():
    for x in range(0, 8):
        tpm = x + 1
        if tpmison[x]:
            dev_id = []

            Mng.OneWire_SelectMux(hex(x))
            time.sleep(0.5)

            board = x + 1
            print("Search device for board " + str(board))
            dev_id = search_device()

            print("Detected " + str(len(dev_id)) + " devices")

            for i in range(0, len(dev_id)):
                # print "Device %d id:" %i
                # print [hex(d) for d in dev_id[i]]
                if i < 3:
                    dev_table[x][i] = dev_id[i]

def partial_reverse(list_, from_, to):
    (list_[4], list_[7]) = (list_[7], list_[4])
    (list_[5], list_[6]) = (list_[6], list_[5])

def tpm_present():
    global present_i
    global tpmison
    global present_done
    global present

    print("Searching...")

    present_i = Mng.read("HKeep.TPMsPresent")
    # Put present in a list
    present = [int(x) for x in '{:08b}'.format(present_i)]
    # Reverse list (bit field 0 as tpm 1)
    present.reverse()


    if present_done == False:
        for x in range(0, 8):
            tpm = x + 1
            tpmison[x] = backplane.is_tpm_on(tpm)
        present_done = True


    # Reverse
    if reverseTPM == True:
        partial_reverse(present,4, 7)
        partial_reverse(tpmison,4, 7)

    print(str(present_i))
    print(str(present))
    print(str(tpmison))

    if reverseTPM == False:
        table_index = ['Board 1', 'Board 2', 'Board 3', 'Board 4', 'Board 5', 'Board 6', 'Board 7', 'Board 8']
    else:
        table_index = ['Board 1', 'Board 2', 'Board 3', 'Board 4', 'Board 8', 'Board 7', 'Board 6', 'Board 5']

    table_present = [
        table_index,
        present,
        tpmison
    ]

    clear()
    tablepres = terminaltables.AsciiTable(table_present)
    tablepres.title = "TPM Present & ON"
    print(str(tablepres.table))

def start_conversion():
    Mng.OneWire_SelectMux(0x08) #all boards
    temp=[]
    Mng.OneWire_ResetCmd()
    Mng.OneWire_WriteByte(0xCC)
    #match_rom(dev_id_codes)

    Mng.OneWire_WriteByte(0x44)
    #time.sleep(0.5)
    # while(1):
    #     data,status=Mng.OneWire_ReadByte_d(0x0)
    #     if data!=0:
    #         break
    #     else:
    #         time.sleep(0.001)
    time.sleep(1)

def read_scratchpad():
    paddata=[]
    #print "Read scratch pad"
    Mng.OneWire_WriteByte(0xBE)
    for i in range(0,9):
        data,status=Mng.OneWire_ReadByte_d(0xff)
        paddata.append(data)
    #print paddata
    return paddata

def match_rom(dev_id_codes):
#    if(Mng.OneWire_ResetCmd()==0):
    Mng.OneWire_WriteByte(0x55)
    for i in range (0,8):
        Mng.OneWire_WriteByte(dev_id_codes[i])
    return 0
#    else:
#        return -1

#ref https://www.maximintegrated.com/en/design/technical-documents/app-notes/1/162.html
def read_temperature(dev_id_codes):
    Mng.OneWire_ResetCmd()
    match_rom(dev_id_codes)
    temp=read_scratchpad()
    #print temp
    #print "Len of sctrachpad: %d" %(len(temp))
    temp_msb=int(temp[1])    #Sign byte + lsbit
    temp_lsb=int(temp[0])    #Temp data plus lsb

    temp_tot=int((temp_msb << 8) + temp_lsb)

    temp_f = float(0.0)

    if (temp_tot >= 0x800): #Negative Temp
        if(temp_tot & 0x0001):
            temp_f += 0.06250
        if (temp_tot & 0x0002):
            temp_f += 0.12500
        if (temp_tot & 0x0004):
            temp_f += 0.25000
        if (temp_tot & 0x0008):
            temp_f += 0.50000
        temp_tot = (temp_tot >> 4) & 0x00FF
        temp_tot -= 0x0001
        temp_tot = ~temp_tot
        temp_f = temp_f - float(temp_tot & 0xFF)
    else: #Posiive Temp
        temp_f += (temp_tot >> 4) & 0x0FF
        if(temp_tot & 0x0001):
            temp_f += 0.06250
        if (temp_tot & 0x0002):
            temp_f += 0.12500
        if (temp_tot & 0x0004):
            temp_f += 0.25000
        if (temp_tot & 0x0008):
            temp_f += 0.50000


    if temp_msb <= 0x80:
        temp_lsb=temp_lsb/2
    temp_msb=temp_msb&0x80
    if temp_msb >= 0x80:
        temp_lsb = (~temp_lsb)+1   #twos complement
    if temp_msb >= 0x80:
        temp_lsb = (temp_lsb/2)     #shift to get whole degree
    if temp_msb >= 0x80:
        temp_lsb = ((-1)*temp_lsb)  #add sign bit

    #print "Temperature read in C: %f" % temp_f
    return temp_f






def search_device():
    disc_pos=[]
    prev_disc_pos=[]
    v_discrepances=[]
    idcodes=[]

    idcode=[]
    discrepances=[]
    pos=0
    iter=0
    prev_pos=0
    disc_to_use_with_unch=0
    disc_byte=[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]

    dir = 0

    while(1):
        idcode=[]
        discrepances=[]
        data=[]
        #print "Iteration %d" %iter
        Mng.write("ONEWIRE.Command1WM",0x0)
        Mng.OneWire_ResetCmd()
        Mng.OneWire_WriteByte(0xF0)
        Mng.OneWire_AccelerateModeCmd()

        for i in range (0,16):
           # print "Byte to be send %x" %disc_byte[i]
            result,status = Mng.OneWire_ReadByte_d(disc_byte[i])
            if (status)==0:
               # print "Read value " + hex(result)
               data.append(result)
           # else:
           #     print "Error while reading"

        #print "rx data "
        #print [hex(d) for d in data]

        i=0
        for q in range (0,8):
            #print "data: %x data+1 %x" %(data[i],data[i+1])
            #retrieve id
            id_l=(((data[i]&0x2)>>1)|((data[i]&0x8)>>2)|((data[i]&0x20)>>3)|((data[i]&0x80)>>4))
            id_h=(((data[i+1]&0x2)>>1)|((data[i+1]&0x8)>>2)|((data[i+1]&0x20)>>3)|((data[i+1]&0x80)>>4))
            #print "idh %x idl %x" %(id_h,id_l)
            id=id_l|(id_h<<4)
            idcode.append(id)
            #retrieve discrepances
            disc_l=(((data[i]&0x0))|((data[i]&0x4)>>1)|((data[i]&0x10)>>2)|((data[i]&0x40)>>3))
            disc_h=(((data[i+1]&0x0))|((data[i+1]&0x4)>>1)|((data[i+1]&0x10)>>2)|((data[i+1]&0x40)>>3))
            #print "disc_h %x disc_l %x" %(disc_h,disc_l)
            disc=disc_l|(disc_h<<4)
            discrepances.append(disc)
            i=i+2

       # print [hex(W) for W in idcode]
       # print [hex(W) for W in discrepances]
        #for i in range (0,len(idcode)):
        #    print "id: %x  disc: %x " %(idcode[i],discrepances[i])


        v_discrepances.append(discrepances)



        #detect_disc_bit
        prev_disc=pos
        found_disc=False
        for n in range(0, 8):
            dato=discrepances[n]
            for i in range(0, 8):
                if (dato & 0x1) == 0x1:
                    found_disc=True
                    pos = (n*8)+i
                dato=dato>>1
        if found_disc == False:
            pos = 9
            # print "No discrepances detected"
        #else:
            # print "Last discrepance detected at bit: %d" %pos


            #idcodes.append(idcode)

            #return idcodes


        #reconstruct transimt data

        if iter>0:
            if v_discrepances[iter-1]==v_discrepances[iter]:
                #print "Detected two times same discrepances"
                #print "actual pos %d" %pos
                pos = prev_pos -1
                #print "new pos %d" %pos
                """
                if dir == 0:
                    pos += 1
                    dir = 1
                else:
                    pos -= 1
                    dir = 0
                """""
        #    else:
        #        idcodes.append(idcode)
        #else:
        #    idcodes.append(idcode)

        exist=0
        if len(idcodes)>0:
            for z in range(0,len(idcodes)):
                if idcode==idcodes[z]:
                    exist=1
                    break

        if exist==0:
            idcodes.append(idcode)

        prev_pos=pos

        byte_disc_count = (pos * 2 / 8)
        bitinbytepos = ((pos * 2) - (byte_disc_count * 8)) + 1

        #print "Byte Discrepancy %x and bit in bytes %x" %(byte_disc_count,bitinbytepos)

        for i in range(0,16):
            if i<byte_disc_count:
                disc_byte[i]=0x0|(data[i]&0x2)|(data[i]&0x8)|(data[i]&0x20)|(data[i]&0x80)
            elif i==byte_disc_count:
                #print "Discrepancy byte: ", hex(disc_byte[i])
                disc_byte[i]=0
                for m in range(0,8):
                    #print "Discrepancy byte (for): ", hex(disc_byte[i])
                    if m%2!=0:
                        if m==bitinbytepos:
                            disc_byte[i]=disc_byte[i]|(1<<m)
                            break
                        else:
                            disc_byte[i]=disc_byte[i]|(data[i]&(1<<m))
                    else:
                        disc_byte[i]=disc_byte[i]|0


                mask=0
                for m in range(0,bitinbytepos+1):
                    mask=mask|(1<<m)
                #print "mask %x disc_byte %x" %(mask,disc_byte[i] )
                disc_byte[i]=disc_byte[i]&0xaa&mask
            else:
                disc_byte[i]=0x0



        #disc_byte=discrepances
        #print "discrepance byte "
        #print disc_byte
        iter=iter+1
        if iter >32:
            #print "OOOhps Somethings Wrong..."

            #print idcodes

            lens = len(idcodes)
            removes = []
            for i in range(0,lens):
                if idcodes[i][0] != 0x28:
                    removes.append(i)
                    #print "\nlist rem " + str(i)

            remlens = len(removes)
            if remlens > 0:
                for i in range (remlens, 0, -1):
                    rmm = removes[i-1]
                    #print rmm
                    #print "\nrem " + str(i) + " = " + str(rmm)
                    del idcodes[rmm]

            #print idcodes

            return idcodes



parser = OptionParser()

parser.add_option("-d", "--dump_regs",
                action="store_true", dest="dump_regs", default=False,
                help="dump all fpga registers & flags")

(options, args) = parser.parse_args()


if(options.dump_regs==True):
   # print "OneWire Regs  dump:"
    Mng.dump_onewire_regs_all()
    exit()


Mng.OneWire_Set_CLK(0x91)

w, h = 8, 3;
dev_table = [[0 for x in range(h)] for y in range(w)]

dev_table = Mng.OneWire_LoadIDs()


#print dev_table

time.sleep(1)

tpm_present()

#search()

#print dev_table
Mng.OneWire_StartConversion()

do_block = False
keyreader = KeyReader(echo=False, block=do_block)

test = 0;

while (1):
    temprow1 = [0, 0, 0, 0, 0, 0, 0, 0]
    temprow2 = [0, 0, 0, 0, 0, 0, 0, 0]
    temprow3 = [0, 0, 0, 0, 0, 0, 0, 0]

    # Reverse
    if reverseTPM == True:
        partial_reverse(present,4, 7)
        partial_reverse(tpmison,4, 7)

    for x in range(0, 8):
        if tpmison[x]:
            board = x+1
            #Mng.OneWire_SelectMux(hex(x))
           # print "Read Temperature from board %d:" %board

            for i in range(0,3):
                if i == 0:
                    temprow1[x] = str(Mng.OneWire_ReadTemperature(hex(x),str(dev_table[x][i])))
                if i == 1:
                    temprow2[x] = str(Mng.OneWire_ReadTemperature(hex(x),str(dev_table[x][i])))
                if i == 2:
                    temprow3[x] = str(Mng.OneWire_ReadTemperature(hex(x),str(dev_table[x][i])))
                #print "devid: " + str(dev_table[x][i])

                #print "x: " + str(x) + " - i: " + str(i)
                #print temprow1
                #print temprow2
                #print temprow3
                #time.sleep(0.25)
        else:
            temprow1[x] = str("-255.0")
            temprow3[x] = str("-255.0")
            temprow2[x] = str("-255.0")
            #time.sleep(0.125)

    # Reverse
    if reverseTPM == True:
        partial_reverse(temprow1, 4, 7)
        partial_reverse(temprow2, 4, 7)
        partial_reverse(temprow3, 4, 7)

    temprow3.insert(0, "FPGA0")
    temprow1.insert(0, "FPGA1")
    temprow2.insert(0, "Board")

    if reverseTPM == False:
        table_index = ['Index', 'Board 1', 'Board 2', 'Board 3', 'Board 4', 'Board 5', 'Board 6', 'Board 7', 'Board 8']
    else:
        table_index = ['Index', 'Board 1', 'Board 2', 'Board 3', 'Board 4', 'Board 8', 'Board 7', 'Board 6', 'Board 5']

    table_data = [
        table_index,
        temprow1,
        temprow2,
        temprow3
    ]

    clear()
    tpm_present()
    table = terminaltables.AsciiTable(table_data)
    table.title = "TPM Temperatures"
    print(str(table.table))

    brd_tmp = [0, 0, 0, 0, 0]
    brd_tmp[0] = Mng.read("Fram.Adt1TempValue")
    brd_tmp[1] = Mng.read("Fram.Adt2TempValue")
    brd_tmp[2] = Mng.read("Fram.ADT7408_B1_temp")
    brd_tmp[3] = Mng.read("Fram.ADT7408_B2_temp")
    p = subprocess.Popen("cat /sys/class/thermal/thermal_zone0/temp", stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    brd_tmp[4] = str(float(output)/1000)

    for x in range(0, 4):
        brd_tmp[x] = int(brd_tmp[x]) & 0x1fff
        segno = int(brd_tmp[x]) & 0x1000
        brd_tmp[x] = int(brd_tmp[x]) & 0xfff
        if segno == 0:
            brd_tmp[x] = str(int(brd_tmp[x])/16)
        else:
            brd_tmp[x] = str((int(brd_tmp[x])-4096) / 16)

    table_brdtmp = [
        ['Mng1', 'Mng2', 'Bckp1', 'Bckp2', 'CPU'],
        brd_tmp
    ]
    tablebrdtmp = terminaltables.AsciiTable(table_brdtmp)
    tablebrdtmp.title = "Board Temperatures"
    print(str(tablebrdtmp.table))


    tpm_v_reg = [0, 0, 0, 0, 0, 0, 0, 0]
    tpm_p_reg = [0, 0, 0, 0, 0, 0, 0, 0]
    tpm_a_reg = [0, 0, 0, 0, 0, 0, 0, 0]

    rsense = 0.007

    tpm_v_reg[1] = str(float("{0:.2f}".format((((Mng.read("Fram.LTC4281_B2_Vsource")*16.64)/(pow(2,16)-1))))))
    tpm_v_reg[2] = str(float("{0:.2f}".format((((Mng.read("Fram.LTC4281_B3_Vsource")*16.64)/(pow(2,16)-1))))))
    tpm_v_reg[3] = str(float("{0:.2f}".format((((Mng.read("Fram.LTC4281_B4_Vsource")*16.64)/(pow(2,16)-1))))))
    tpm_v_reg[4] = str(float("{0:.2f}".format((((Mng.read("Fram.LTC4281_B5_Vsource")*16.64)/(pow(2,16)-1))))))
    tpm_v_reg[0] = str(float("{0:.2f}".format((((Mng.read("Fram.LTC4281_B1_Vsource")*16.64)/(pow(2,16)-1))))))
    tpm_v_reg[5] = str(float("{0:.2f}".format((((Mng.read("Fram.LTC4281_B6_Vsource")*16.64)/(pow(2,16)-1))))))
    tpm_v_reg[6] = str(float("{0:.2f}".format((((Mng.read("Fram.LTC4281_B7_Vsource")*16.64)/(pow(2,16)-1))))))
    tpm_v_reg[7] = str(float("{0:.2f}".format((((Mng.read("Fram.LTC4281_B8_Vsource")*16.64)/(pow(2,16)-1))))))

    tpm_p_reg[0] = str(float("{0:.2f}".format(((Mng.read("Fram.LTC4281_B1_power")*0.040*16.64*pow(2,16))/((pow(2,16)-1))*rsense))))
    tpm_p_reg[1] = str(float("{0:.2f}".format(((Mng.read("Fram.LTC4281_B2_power")*0.040*16.64*pow(2,16))/((pow(2,16)-1))*rsense))))
    tpm_p_reg[2] = str(float("{0:.2f}".format(((Mng.read("Fram.LTC4281_B3_power")*0.040*16.64*pow(2,16))/((pow(2,16)-1))*rsense))))
    tpm_p_reg[3] = str(float("{0:.2f}".format(((Mng.read("Fram.LTC4281_B4_power")*0.040*16.64*pow(2,16))/((pow(2,16)-1))*rsense))))
    tpm_p_reg[4] = str(float("{0:.2f}".format(((Mng.read("Fram.LTC4281_B5_power")*0.040*16.64*pow(2,16))/((pow(2,16)-1))*rsense))))
    tpm_p_reg[5] = str(float("{0:.2f}".format(((Mng.read("Fram.LTC4281_B6_power")*0.040*16.64*pow(2,16))/((pow(2,16)-1))*rsense))))
    tpm_p_reg[6] = str(float("{0:.2f}".format(((Mng.read("Fram.LTC4281_B7_power")*0.040*16.64*pow(2,16))/((pow(2,16)-1))*rsense))))
    tpm_p_reg[7] = str(float("{0:.2f}".format(((Mng.read("Fram.LTC4281_B8_power")*0.040*16.64*pow(2,16))/((pow(2,16)-1))*rsense))))

    for x in range(0, 8):
        if float(tpm_p_reg[x]) == 0 or float(tpm_v_reg[x]) == 0:
            tpm_a_reg[x] = "0.0A"
        else:
            tpm_a_reg[x] = str(float("{0:.2f}".format(float(tpm_p_reg[x]) / float(tpm_v_reg[x])))) + "A"
        tpm_v_reg[x] = tpm_v_reg[x] + "V"
        tpm_p_reg[x] = tpm_p_reg[x] + "W"


    # Reverse
    if reverseTPM == True:
        partial_reverse(tpm_v_reg, 4, 7)
        partial_reverse(tpm_p_reg, 4, 7)
        partial_reverse(tpm_a_reg, 4, 7)

    if reverseTPM == False:
        table_index = ['Board 1', 'Board 2', 'Board 3', 'Board 4', 'Board 5', 'Board 6', 'Board 7', 'Board 8']
    else:
        table_index = ['Board 1', 'Board 2', 'Board 3', 'Board 4', 'Board 8', 'Board 7', 'Board 6', 'Board 5']

    table_tpmpow = [
        table_index,
        tpm_v_reg,
        tpm_a_reg,
        tpm_p_reg
    ]
    tabletpmpow = terminaltables.AsciiTable(table_tpmpow)
    tabletpmpow.title = "Board Powers"
    print(str(tabletpmpow.table))


    fan1 = Mng.read("Fram.FAN1_TACH")
    fan2 = Mng.read("Fram.FAN2_TACH")
    fan3 = Mng.read("Fram.FAN3_TACH")
    fan4 = Mng.read("Fram.FAN4_TACH")
    fanpwmreg = Mng.read("Fram.FAN_PWM")

    fan_settings = (fanpwmreg >> 24) & 0xff
    fan1_bank = (fanpwmreg & 0xff)
    fan2_bank = (fanpwmreg >> 8) & 0xff

    fan1_bank_p = (float(fan1_bank) / 255)*100
    fan2_bank_p = (float(fan2_bank) / 255) * 100

    #print hex(fanpwmreg)
    #print test

    rpmfan = ['0','0','0','0']

    rpmfan[0] = str((90000 * 60) / fan1)
    rpmfan[1] = str((90000 * 60) / fan2)
    rpmfan[2] = str((90000 * 60) / fan3)
    rpmfan[3] = str((90000 * 60) / fan4)



    fan_data = [
        ['Fan 1', 'Fan 2', 'Fan 3', "Fan 4"],
        rpmfan,
        [str(int(fan1_bank_p)) + "%", str(int(fan1_bank_p)) + "%", str(int(fan2_bank_p)) + "%", str(int(fan2_bank_p)) + "%"]
    ]

    tablefan = terminaltables.AsciiTable(fan_data)
    tablefan.title = "RPM Fan Speed & PWM"
    print(str(tablefan.table))

    if fan_settings & 0x2:
        print("Fan Control: Automatic")
    else:
        print("Fan Control: Manual")

    ps0_vout_reg = Mng.read("Fram.PSU0_Vout")
    ps0_iout_reg = Mng.read("Fram.PSU0_Iout")
    ps1_vout_reg = Mng.read("Fram.PSU1_Vout")
    ps1_iout_reg = Mng.read("Fram.PSU1_Iout")

    ps0_vout = ps0_vout_reg * pow(2,-9)
    ps1_vout = ps1_vout_reg * pow(2, -9)
    ps0_iout = (ps0_iout_reg & 0x7ff) * pow(2,-3)
    ps1_iout = (ps1_iout_reg & 0x7ff) * pow(2, -3)

    table_psu = [
        ['PSU', 'Voltage Out', 'Amperage Out', 'Power Out'],
        ['PSU 0', str(float("{0:.2f}".format(ps0_vout))) + "V", str(ps0_iout) + "A", str(float("{0:.2f}".format(ps0_iout * ps0_vout))) + "W"],
        ['PSU 1', str(float("{0:.2f}".format(ps1_vout))) + "V", str(ps1_iout) + "A", str(float("{0:.2f}".format(ps1_iout * ps1_vout))) + "W"],
        ['Total', str(float("{0:.2f}".format((ps1_vout+ps0_vout)/2))) + "V", str(ps1_iout + ps0_iout) + "A", str(float("{0:.2f}".format((ps0_iout * ps0_vout)+(ps1_iout * ps1_vout)))) + "W"]
    ]
    tablepsu = terminaltables.AsciiTable(table_psu)
    tablepsu.title = "PSU Data"
    print(str(tablepsu.table))


    #help
    print("\n\nKeyboard command help:")
    print("A-Z:\tUp & Down Fan 1 Bank (TPM 1-4)")
    print("S-X:\tUp & Down Fan 2 Bank (TPM 5-8)")
    print("C:\tEnable Automatic Fan Control")
    print("1-8:\tToggle TPM Power")
    print("0:\tToggle TPM Power Sequence (if ANY TPM is on, this start a shutdown procedure for all boards")
    print("R:\tSearch new board (OneWire sensors)")
    print("\nQ:\tQuit")

    #start_conversion()
    Mng.OneWire_StartConversion()

    fan_step = 0x11

    key = keyreader.getch()
    if key == 'q':
        keyreader = None
        exit()
    if key == 'c':
        Mng.write("Fram.FAN_PWM", 0x03FF3333)
    if key == 'a':
        fan1_bank += fan_step
        if fan1_bank > 0xff:
            fan1_bank = 0xff
        reg = (0x00FF << 16 ) + (fan2_bank << 8) + fan1_bank
        Mng.write("Fram.FAN_PWM", reg)
    if key == 'z':
        fan1_bank -= fan_step
        if fan1_bank < 0x33:
            fan1_bank = 0x33
        reg = (0x00FF << 16 ) + (fan2_bank << 8) + fan1_bank
        Mng.write("Fram.FAN_PWM", reg)
    if key == 's':
        fan2_bank += fan_step
        if fan2_bank > 0xff:
            fan2_bank = 0xff
        reg = (0x00FF << 16 ) + (fan2_bank << 8) + fan1_bank
        Mng.write("Fram.FAN_PWM", reg)
    if key == 'x':
        fan2_bank -= fan_step
        if fan2_bank < 0x33:
            fan2_bank = 0x33
        reg = (0x00FF << 16 ) + (fan2_bank << 8) + fan1_bank
        Mng.write("Fram.FAN_PWM", reg)
    if key == 'r':
        present_done = False #tpmison
        search()
    if key == '1':
        if tpmison[0]:
            backplane.pwr_off_tpm(1)
        else:
            backplane.pwr_on_tpm(1)
        present_done = False
    if key == '2':
        if tpmison[0]:
            backplane.pwr_off_tpm(2)
        else:
            backplane.pwr_on_tpm(2)
        present_done = False
    if key == '3':
        if tpmison[0]:
            backplane.pwr_off_tpm(3)
        else:
            backplane.pwr_on_tpm(3)
        present_done = False
    if key == '4':
        if tpmison[0]:
            backplane.pwr_off_tpm(4)
        else:
            backplane.pwr_on_tpm(4)
        present_done = False
    if key == '5':
        if tpmison[0]:
            backplane.pwr_off_tpm(5)
        else:
            backplane.pwr_on_tpm(5)
        present_done = False
    if key == '6':
        if tpmison[0]:
            backplane.pwr_off_tpm(6)
        else:
            backplane.pwr_on_tpm(6)
        present_done = False
    if key == '7':
        if tpmison[0]:
            backplane.pwr_off_tpm(7)
        else:
            backplane.pwr_on_tpm(7)
        present_done = False
    if key == '8':
        if tpmison[0]:
            backplane.pwr_off_tpm(8)
        else:
            backplane.pwr_on_tpm(8)
        present_done = False
    if key == '0':
        tpmisonatleast = False
        for x in range(0, 8):
            if tpmison[x]:
                tpmisonatleast = True
        if tpmisonatleast:
            os.system("python power_off_tpm.py --all")
        else:
            os.system("python power_on_tpm.py --all")
        present_done = False
    if key:
        print("-%s-" % key)
    else:
        print("None")

exit()


#print "Request Read"
#Mng.OneWire_ResetCmd()
#status = Mng.OneWire_WriteByte(0x55)
# status = Mng.OneWire_WriteByte(0x28)
# status = Mng.OneWire_WriteByte(0xff)
# status = Mng.OneWire_WriteByte(0x5c)
# status = Mng.OneWire_WriteByte(0x45)
# status = Mng.OneWire_WriteByte(0xa4)
# status = Mng.OneWire_WriteByte(0x16)
# status = Mng.OneWire_WriteByte(0x04)
#
# status = Mng.OneWire_WriteByte(0xd2)
# status = Mng.OneWire_WriteByte(0x44)
# #status = Mng.OneWire_WriteByte(0xBE)
# first=False
# if status==0:
#     print "Read Temperature"
#     while(1):
#         result,status = Mng.OneWire_ReadByte()
#         if (status)!=0:
#             print "Error while reading"
#         else:
#             print "Read value " + hex(result)
#             if(result!=0):
#                 if first==False:
#                     first=True
#                 else:
#                       break
#             else:
#                 time.sleep(0.5)
