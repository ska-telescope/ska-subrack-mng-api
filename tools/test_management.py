__author__ = 'Cristian Albanese'


import sys
import time
from management import *
from backplane import *


board = Management()

board.create_regs_list("MCUR")

#get FPGA fw_vewrsion
board.get_fpga_fw_version()

print("Read Housekeeping Flags")
board.dump_housekeeping_flags_all()

print("Read MCU Registers")
board.dump_mcu_regs_all()

print ("Read Fram Registers")
board.dump_fram_regs_all()

print ("Read I2C regs")
board.read_i2c(0, I2CDevAdd.EEPROM_MAC_1, 0xfa, "b")


print("Read I2C Backplane regs")
backplane=Backplane()

#temp,status=backplane.get_sens_temp_alarm(1)
#print "Backplane Temp 1: " + str(temp)

#temp,status=backplane.get_sens_temp_alarm(2)
#print "Backplane Temp 2: " + str(temp)


id,status=backplane.get_sens_temp_manuf_id(1)
print( "Backplane ID1: " + hex(id) + ", status:" + str(status))

#clk,status=backplane.get_pwr_clk(1)
#print "PWRON CLK REG ID1: " + hex(clk) + ", status:" + str(status)
#id,status=backplane.get_sens_temp_manuf_id(1)
#print "Backplane ID2 : " + hex(id)