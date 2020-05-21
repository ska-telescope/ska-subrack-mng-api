# management cpu script changelog
## version 0.1.0
 - first version of class management_board and script fpga_reg.py i2c_reg.py
## version 0.1.1
 - add methods to MngBoard to read and write on I2C buses to backplane board
 - add backplane board class

## version 2.0.0
 - version for API generation for TANGO device driver
 - add SubrackMngBoard
 - rename MngBoard class filename to management
 - use of Backplane and MngBoard

## version 2.0.1
 - add emulator_classes used in simaulation mode
 - add flag simulation to enable simulation mode
 - add subrack_emulator files csv to store and update states of some regs