# Subrack Management API changelog
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

## version 2.0.2
 - moved emulation classes function in api classes
 - removed emulation classes files
 
## version 2.0.3
- add cpld_mng_api: api to access on board CPLD via ETH
- aligned API to manage HW Revision 1.2 board

## version 2.0.4
- crated tools folder with utils scripts
- add pyfabil as submodule
- implemented automatic IP assignement of TPM boards
- porting to python3
- changed setup installation scripts

## version 2.0.5
- add method to get PLL and CPLD_PLL status
- add method to get TPM temperatures vectors
- updated pyfabil submodule to manage TPM with BIOS v0.3.1
- add UPS-Board communication methods

## version 2.0.6
- imported Pyro5 libraries to export class over eth
- changed categories to dictionary  
- add main to sbrack_management_board to execute initialization of subrack
- add test_eim_access mtehod
