import time
import binascii
from .management_spi import MANAGEMENT_SPI

eep_addr_0 = 0xA0
eep_addr_1 = 0xA2
subrack_pll_cs = 0x1
cabinet_pll_cs = 0x2
BOARD_MODE = {
"subrack": 1,
"cabinet": 2,
}
class MANAGEMENT_BSP():
    def __init__(self, board, rmp):
        self.rmp = rmp
        self.board = board
        print("creating bsp")
        self.mode=self.rmp.rd32(0x120)
        if self.mode == BOARD_MODE['subrack']:
            print("mode: SUBRACK")
            self.spi = MANAGEMENT_SPI(board,rmp,subrack_pll_cs)
        elif self.mode == BOARD_MODE['cabinet']:
            print("mode: CABINET")
            self.spi = MANAGEMENT_SPI(board,rmp,cabinet_pll_cs)
        else:
            print("mode: UNKNOWN")
            self.spi = MANAGEMENT_SPI(board,rmp,subrack_pll_cs)
        self.hw_rev=[]
        hw_rev=self.rmp.rd32(0x124)
        self.hw_rev.append((hw_rev>>16)&0xff)
        self.hw_rev.append((hw_rev>>8)&0xff)
        self.hw_rev.append((hw_rev>>0)&0xff)
        print("HW_REV: v" + str(self.hw_rev[0]) + "." + str(self.hw_rev[1]) + "." + str(self.hw_rev[2]))

    def wr32_multi(self, add, dat, ba=[0x00000000,0x10000000]):
        for b in ba:
            self.rmp.wr32(add + b, dat)

    def eep_rd8(self, offset, phy_addr = eep_addr_0):
        ba = 0x00010000
        add = phy_addr >> 1
        nof_rd_byte = 1
        nof_wr_byte = 1
        cmd = (nof_rd_byte << 12) + (nof_wr_byte << 8) + add

        self.rmp.wr32(ba + 0x4, (offset & 0xFF))
        self.rmp.wr32(ba + 0x0, cmd)
        while(self.rmp.rd32(ba + 0xC) != 0):
            pass
        return self.rmp.rd32(ba + 0x8)

    def eep_wr8(self, offset, data, phy_addr = eep_addr_0):
        ba = 0x00010000
        add = phy_addr >> 1
        nof_rd_byte = 0
        nof_wr_byte = 2
        cmd = (nof_rd_byte << 12) + (nof_wr_byte << 8) + add

        while (True):
            self.rmp.wr32(ba + 0x4, ((data & 0xFF) << 8) + (offset & 0xFF))
            self.rmp.wr32(ba + 0x0, cmd)
            while (True):
                rd = self.rmp.rd32(ba + 0xC)
                if rd == 2:
                    print("eep_wr8 error: ack_error")
                    time.sleep(0.1)
                    break
                elif rd == 0:
                    time.sleep(0.005)
                    return
                else:
                    time.sleep(0.1)
                    print(".")

    def eep_rd16(self, offset, phy_addr = eep_addr_0):
        rd = 0
        for n in range(2):
            rd = rd << 8
            rd = rd | self.eep_rd8(offset+n, phy_addr)
        return rd

    def eep_rd32(self, offset, phy_addr = eep_addr_0):
        rd = 0
        for n in range(4):
            rd = rd << 8
            rd = rd | self.eep_rd8(offset+n, phy_addr)
        return rd

    def eep_wr16(self, offset, data, phy_addr = eep_addr_0):
        for n in range(2):
            self.eep_wr8(offset+n, (data >> 8*(1-n)) & 0xFF, phy_addr)
        return

    def eep_wr32(self, offset, data, phy_addr = eep_addr_0):
        for n in range(4):
            self.eep_wr8(offset+n, (data >> 8*(3-n)) & 0xFF, phy_addr)
        return

    def cpld_efb_wr(self, dat):
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x10 == 0x10:
            pass
        self.rmp.wr32(0x90000000 + 0x71 * 4, dat)

    def cpld_flash_read(self, bitfile="cpld_dump.bit"):
        dump = []

        self.rmp.wr32(0x90000000 + 0x70*4, 0x80)    # enable wishbone connection
        self.cpld_efb_wr(0x74)  #
        self.cpld_efb_wr(0x08)  #
        self.cpld_efb_wr(0x00)  #
        self.cpld_efb_wr(0x00)  #
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass
        time.sleep(0.001)

        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0x46)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass

        for n in range(9212):
            self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
            self.cpld_efb_wr(0x73)
            self.cpld_efb_wr(0x10)
            self.cpld_efb_wr(0x00)
            self.cpld_efb_wr(0x00)
            while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
                pass

            while( self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x8 == 0x8):
                pass
            for m in range(16):
                while True:
                    rd = self.rmp.rd32(0x90000000 + 0x72 * 4)
                    if rd & 0x8 != 0:
                        pass
                    else:
                        break
                rd = self.rmp.rd32(0x90000000 + 0x73 * 4)
                #print rd
                dump.append(rd)
            while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
                pass
            self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection

            if n % 1000 == 0:
                print("Reading CPLD config frame " + str(n) + "/9212")

        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0x26)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass

        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0xFF)  #
        self.cpld_efb_wr(0xFF)  #
        self.cpld_efb_wr(0xFF)  #
        self.cpld_efb_wr(0xFF)  #
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection

        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass

        #self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection

        f = open(bitfile, "wb")
        f.write(bytearray(dump))
        f.close()
        return bytearray(dump)

    def cpld_flash_write(self, bitfile):
        print("Using CPLD bitfile " + bitfile)
        f = open(bitfile, "rb")
        dump = bytearray(f.read())
        f.close()
        start_idx = -1
        for n in range(len(dump)-8):
            if dump[n] == 0xFF and dump[n+1] == 0xFF and dump[n+2] == 0xBD and dump[n+3] == 0xB3:
                start_idx = n
                break
        if start_idx == -1:
            print("Invalid CPLD bitfile. Start word not found!")
            exit(1)
        if start_idx > 0:
            dump = dump[start_idx:]
            dump = dump[:10] + dump[10+8:]
        if len(dump) % 16 != 0:
            dump = dump + bytearray([0xFF]*(16 - len(dump) % 16))

        # enable configuration access
        print("Enable CPLD configuration access")
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0x74)  #
        self.cpld_efb_wr(0x08)  #
        self.cpld_efb_wr(0x00)  #
        self.cpld_efb_wr(0x00)  #
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass
        time.sleep(0.001)

        # erase flash
        print("Erase Flash")
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0x0E)  #
        self.cpld_efb_wr(0x04)  #
        self.cpld_efb_wr(0x00)  #
        self.cpld_efb_wr(0x00)  #
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection

        print("Flash status check")
        while True:
            # status check
            self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
            self.cpld_efb_wr(0xF0)  #
            self.cpld_efb_wr(0x00)  #
            self.cpld_efb_wr(0x00)  #
            self.cpld_efb_wr(0x00)  #
            while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
                pass
            rd = self.rmp.rd32(0x90000000 + 0x73 * 4)
            self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
            if rd == 0:
                break
            else:
                print("CPLD status register: " + hex(rd))
                time.sleep(0.2)

        # Init Address
        print("Init Address")
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0x46)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass

        nof_frame = (len(dump))/16
        idx = 0
        print("Write configuration flash")
        for n in range(nof_frame):
            self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
            self.cpld_efb_wr(0x70)
            self.cpld_efb_wr(0x00)
            self.cpld_efb_wr(0x00)
            self.cpld_efb_wr(0x00)
            for m in range(16):
                self.cpld_efb_wr(dump[idx])
                idx += 1
            self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
            if n % 1000 == 0:
                print("Writing CPLD config frame " + str(n) + "/" + str(nof_frame))

            while True:
                # status check
                self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
                self.cpld_efb_wr(0xF0)  #
                self.cpld_efb_wr(0x00)  #
                self.cpld_efb_wr(0x00)  #
                self.cpld_efb_wr(0x00)  #
                while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
                    pass
                rd = self.rmp.rd32(0x90000000 + 0x73 * 4)
                self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
                if rd == 0:
                    break
                else:
                    print("CPLD status register: " + hex(rd))
                    time.sleep(0.2)

        # program DONE
        printr( "Program Done")
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0x5E)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass
        time.sleep(0.01)

        # disable configuration access
        print("Disable CPLD configuration access")
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0x26)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass

        # Bypass
        print("Bypass")
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0xFF)  #
        self.cpld_efb_wr(0xFF)  #
        self.cpld_efb_wr(0xFF)  #
        self.cpld_efb_wr(0xFF)  #
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass

        # verify bitstream
        readback_dump = self.cpld_flash_read()
        for n in range(len(dump)):
            #print readback_dump[n]
            #print dump[n]
            #print
            if readback_dump[n] != dump[n]:
                print("CPLD Verify Flash error!")
                print("Address ", str(n))
                print("CPLD doesn't have a good bitstream, it will not boot!")
                print("Write a valid bistream into the Flash before rebooting, otherwise you will need to use then JTAG!")
                exit(1)


        #Refresh
        print("Refresh")
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x80)  # enable wishbone connection
        self.cpld_efb_wr(0x79)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.cpld_efb_wr(0x00)
        self.rmp.wr32(0x90000000 + 0x70 * 4, 0x0)  # disable wishbone connection
        while self.rmp.rd32(0x90000000 + 0x72 * 4) & 0x20 == 0:
            pass

        print("CPLD bitstream update done!")

    def mcu_reset_n(self,value):
        SAM_RESET_N = 0x900
        self.rmp.wr32(SAM_RESET_N, value)

    def i2c_set_passwd(self):
        self.mcu_reset_n(0)
        rd = self.rmp.rd32(0x00010020)
        self.rmp.wr32(0x0001003C, rd)
        rd = self.rmp.rd32(0x00010024)
        self.rmp.wr32(0x00010038, rd)

        rd = self.rmp.rd32(0x0001003C)
        if rd & 0x10000 == 0:
            print("I2C password not accepted!")
            exit(-1)
        #else:
        #    print "I2C password accepted!"

    def i2c_remove_passwd(self):
        self.rmp.wr32(0x0001003C, 0)
        self.rmp.wr32(0x00010038, 0)
        self.mcu_reset_n(1)
