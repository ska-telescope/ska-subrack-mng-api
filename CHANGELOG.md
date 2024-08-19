# Subrack Management API Changelog

## v2.2.0 (2023-05-31)

### Features
 - new get_health_dict and get_health_status to collect all monitoring points at once
 - new ping test on TPM (replace TPM pyfabil access, )

### Removed
 - GetTPMInfo
 - GetTPMGlobalStatusAlarm
 - Get_tpm_alarms_vector
 - GetTPMTemperatures
 - Get_TPM_temperature_vector
 - GetTPMMCUTemperature

## v2.1.0 (2023-05-25)

### Features
 - SetTPMIP manage also netmask and gateway configuration
 - BIOS update methods
 - ska-low-smm-bios python package (bios binaries and update tool)
 - get_board_info with BIOS and OS information
 - refactored initialize (only at boot, removed from web_server)
 - SFP configuration
 - PllInitialize with pll_source_internal option (default False)

### Bugfixes
 - first TPM ip address assignament fails

## v2.0.6
 - imported Pyro5 libraries to export class over eth
 - changed categories to dictionary  
 - add main to subrack_management_board to execute initialization of subrack
 - add test_eim_access method

## v2.0.5
 - add method to get PLL and CPLD_PLL status
 - add method to get TPM temperatures vectors
 - updated pyfabil submodule to manage TPM with BIOS v0.3.1
 - add UPS-Board communication methods

## v2.0.4
 - crated tools folder with utils scripts
 - add pyfabil as submodule
 - implemented automatic IP assignement of TPM boards
 - porting to python3
 - changed setup installation scripts
 - add read temperature of all TPMs
 - add read alarms of all TPMs

## v2.0.3
 - add cpld_mng_api: api to access on board CPLD via ETH
 - aligned API to manage HW Revision 1.2 board

## v2.0.2
 - moved emulation classes function in api classes
 - removed emulation classes files

## v2.0.1
 - add emulator_classes used in simaulation mode
 - add flag simulation to enable simulation mode
 - add subrack_emulator files csv to store and update states of some regs
## v2.0.0
 - version for API generation for TANGO device driver
 - add SubrackMngBoard
 - rename MngBoard class filename to management
 - use of Backplane and MngBoard
 - add some utils script: subrack_monitor.py, fpga_i2c_reg.py, fpga_reg.py, i2c_reg.py, power_on_tpm.py,power_off_tpm.py 

## v0.1.1
 - add methods to MngBoard to read and write on I2C buses to backplane board
 - add backplane board class

## v0.1.0
 - first version of class management_board and script fpga_reg.py i2c_reg.py