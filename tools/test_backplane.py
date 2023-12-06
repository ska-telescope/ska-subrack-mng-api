__author__ = "Cristian Albanese"


import sys
import time
from management import *
from backplane import *


print("BACKPLANE FUNCTIONS CHECK")
backplane = Backplane()

print("GET POWER SUPPLY INFO")

for i in range(1, 2):
    print("Get PS " + str(i) + "Status")
    stat, status = backplane.get_ps_status(i)
    print(hex(stat))

    print("Get PS " + str(i) + "Vout")
    v, status = backplane.get_ps_vout(i)
    print(str(v) + " V")

    print("Get PS " + str(i) + "Iout")
    iout, status = backplane.get_ps_iout(i)
    print(str(iout) + " A")

    print("Get PS " + str(i) + "Power")
    pw, status = backplane.get_ps_status(i)
    print(str(pw) + " W")


time.sleep(1)


for i in range(1, 9):
    backplane.pwr_set_ilimt(i, 5)
    backplane.reset_pwr_fault_reg(i)
    print("Power On TPM " + str(i))
    backplane.pwr_on_tpm(i)

time.sleep(100)
for i in range(1, 9):
    print("Power Off TPM " + str(i))
    backplane.pwr_off_tpm(i)
    if backplane.is_tpm_on(i) == False:
        print("power off command success")
    else:
        print("power off command failed")
