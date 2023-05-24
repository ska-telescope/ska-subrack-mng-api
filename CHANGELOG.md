# Subrack Management API Changelog

## version 2.1.0
- add netmask and gateway management to SetTPMIP
- add BIOS update methods
- add ska-low-smm-bios python package (bios binaries and update tool)
- new get_board_info with BIOS and OS information
- refactored initialize (only at boot, removed from web_server)
- add SFP configuration
- add pll_source_internal option (default False)
- bugfix - first TPM ip address assignament fails

## version 2.0.6
- imported Pyro5 libraries to export class over eth
- changed categories to dictionary  
- add main to subrack_management_board to execute initialization of subrack
- add test_eim_access method

## version 2.0.5
- add method to get PLL and CPLD_PLL status
- add method to get TPM temperatures vectors
- updated pyfabil submodule to manage TPM with BIOS v0.3.1
- add UPS-Board communication methods

## version 2.0.4
- crated tools folder with utils scripts
- add pyfabil as submodule
- implemented automatic IP assignement of TPM boards
- porting to python3
- changed setup installation scripts
- add read temperature of all TPMs
- add read alarms of all TPMs

## version 2.0.3
- add cpld_mng_api: api to access on board CPLD via ETH
- aligned API to manage HW Revision 1.2 board

## version 2.0.2
 - moved emulation classes function in api classes
 - removed emulation classes files

## version 2.0.1
 - add emulator_classes used in simaulation mode
 - add flag simulation to enable simulation mode
 - add subrack_emulator files csv to store and update states of some regs
## version 2.0.0
 - version for API generation for TANGO device driver
 - add SubrackMngBoard
 - rename MngBoard class filename to management
 - use of Backplane and MngBoard
 - add some utils script: subrack_monitor.py, fpga_i2c_reg.py, fpga_reg.py, i2c_reg.py, power_on_tpm.py,power_off_tpm.py 

## version 0.1.1
 - add methods to MngBoard to read and write on I2C buses to backplane board
 - add backplane board class

## version 0.1.0
 - first version of class management_board and script fpga_reg.py i2c_reg.py


