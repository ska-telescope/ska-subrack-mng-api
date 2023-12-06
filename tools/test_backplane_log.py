__author__ = "Cristian Albanese"


import sys
import time
import datetime
from management import *
from backplane import *


fps = open("backplane_ps_log.csv", "w+")
fps.write(
    "TIMESTAMP,PS1 VOUT(V), PS1 IOUT(A),PS1 STATUS,PS2 VOUT(V), PS2 IOUT(A),PS2 STATUS\n"
)

fmng = open("backplane_tpm_log.csv", "w+")
fmng.write(
    "TIMESTAMP,TPM ON OFF,TPM1 VOLTAGE(V), TPM1 POWER(W),BACKPLANE_TEMP1,BACKPLANE_TEMP2,FAULTREG\n"
)

print("BACKPLANE FUNCTIONS CHECK")
backplane = Backplane()

tpm_on_list = [0, 0, 0, 0, 0, 0, 0, 0]
tpm_present_list = [0, 0, 0, 0, 0, 0, 0, 0]


def update_tpm_on_list():
    for i in range(1, 9):
        if (
            backplane.mng.read("HKeep.TPMsPresent") & TPM_PRESENT_MASK[i - 1]
        ) == TPM_PRESENT_MASK[i - 1]:
            tpm_present_list[i - 1] = 1
            if backplane.is_tpm_on(i) == True:
                # print "TPM %d is ON " %i
                tpm_on_list[i - 1] = 1
            else:
                # print "TPM %d is OFF " %i
                tpm_on_list[i - 1] = 0
        else:
            tpm_present_list[i - 1] = 0
            tpm_on_list[i - 1] = 0


k = 0
faultreg = 0
while 1:
    print("GET POWER SUPPLY INFO")
    stat1, status = backplane.get_ps_status(1)
    print("PS 1 Status " + hex(stat1))
    v1, status = backplane.get_ps_vout(1)
    print("PS 1 Vout " + str(v1) + " V")
    iout1, status = backplane.get_ps_iout(1)
    print("PS 1 Iout " + str(iout1) + " A")
    # pw1,status=backplane.get_ps_status(1)
    # print "PS 1 Power " + str(pw1) + " W"

    stat2, status = backplane.get_ps_status(2)
    print("PS 2 Status " + hex(stat2))
    v2, status = backplane.get_ps_vout(2)
    print("PS 2 Vout " + str(v2) + " V")
    iout2, status = backplane.get_ps_iout(2)
    print("PS 2 Iout " + str(iout2) + " A")
    # pw2,status=backplane.get_ps_status(2)
    # print "PS 2 Power " + str(pw2) + " W"

    ts = datetime.datetime.now()
    date_time = date_time = ts.strftime("%m/%d/%Y %H:%M:%S")

    print("Get TPM INFO")
    errcount = 0
    update_tpm_on_list()
    print("TPM_PRESENT " + str(tpm_present_list))
    print("TPM ON-OFF" + str(tpm_on_list))

    temp1, status = backplane.get_sens_temp(1)
    if status != 0:
        print("Error in temperature value detection")
    else:
        print("Actual Backplane Temperature 1 " + str(temp1))

    temp2, status = backplane.get_sens_temp(2)
    if status != 0:
        print("Error in temperature value detection")
    else:
        print("Actual Backplane Temperature 2 " + str(temp2))

    for i in range(1, 9):
        voltage, status = backplane.get_voltage_tpm(i)
        if status != 0:
            print("Error in voltage value detection")
        else:
            print("Actual TPM " + str(i) + " voltage: " + str(voltage) + " V")

        power, status = backplane.get_power_tpm(i)
        if status != 0:
            print("Error in power value detection")
        else:
            print("Actual TPM " + str(i) + " power: " + str(power) + " W")
        if i == 1:
            fps.write(
                date_time
                + ","
                + str(v1)
                + ","
                + str(iout1)
                + ","
                + hex(stat1)
                + ","
                + str(v2)
                + ","
                + str(iout2)
                + ","
                + hex(stat2)
                + "\n"
            )
            fmng.write(
                date_time
                + ","
                + str(tpm_on_list[i - 1])
                + ","
                + str(voltage)
                + ","
                + str(power)
                + ","
                + str(temp1)
                + ","
                + str(temp2)
                + ","
                + hex(faultreg)
                + "\n"
            )

        if (tpm_present_list[i - 1] == 1 and tpm_on_list[i - 1] == 1) and (
            (power == 0) or (voltage == 0)
        ):
            print("power or voltage not valid")
            faultreg, status = backplane.get_pwr_fault_log(i)
            print("Fault reg")
            errcount = errcount + 1
            if (int(faultreg) & (0xFE)) != 0:
                if errcount > 5:
                    print("Max configuration changing retry reached")
                    break

                actcfg, stat = backplane.pwr_get_ilimt(i)
                print("actual configuration: " + str(actcfg))
                if actcfg < 7:
                    cfg = actcfg + 1
                    print("change configuration to next power cfg")
                    backplane.pwr_set_ilimt(i, cfg)
                    backplane.reset_pwr_fault_reg(i)
                    backplane.pwr_off_tpm(i)
                    # backplane.pwr_on_tpm(i)

    time.sleep(2)
    k = k + 1
    if k == 100:
        break

fps.close()
fmng.close()
