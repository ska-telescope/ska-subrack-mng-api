## Field update

1. Create uSD from ISO. Be carefull to change `/dev/sdb` with your system uSD device path, minimum 8GB size required.
```
gunzip -c ska-low-smm_v0.4.0_20230516.img.tgz  | sudo dd of=/dev/sdb status=progress
```

2. Insert uSD into uSD slot of SMB board.

4. Power-on the board

5. Web server start
No action required. Filesystem start with web_server service active for external control (e.g. with SKALAB).
The filesystem configure CPU ip address calculated from CPLD ip address read from EEPROM, decreasing by 6. (e.g. CPLD ip 10.0.10.19 follow to CPU ip address 10.0.10.13).

6. Connect to board via SSH
```
sshpass -p SkaUser ssh -o StrictHostKeyChecking=no mnguser@10.0.10.13
```
7. Update BIOS if needed (read below)

8. Change ip address if needed (read below)

## Update BIOS
`ska_low_smm_bios` can be used to update a SMM board, you needs to specify bios version. Ip address is not required because it operate on localhost only.

```
$ python -m ska_low_smm_bios --bios v1.0.0
==============================================================
PLEASE READ THE AGREEMENT CAREFULLY.
BY USING THIS SOFTWARE, YOU ACCEPT THE TERMS OF THE AGREEMENT.
You can read license by '--show-license' option
==============================================================

| BOARD INFO          |                                                                                                             |
|:--------------------|:------------------------------------------------------------------------------------------------------------|
| CPLD_ip_address     | 10.0.10.86                                                                                                  |
| CPLD_netmask        | 255.255.255.0                                                                                               |
| CPLD_gateway        | 10.0.10.1                                                                                                   |
| CPLD_ip_address_eep | 10.0.10.86                                                                                                  |
| CPLD_netmask_eep    | 255.255.255.0                                                                                               |
| CPLD_gateway_eep    | 10.0.10.1                                                                                                   |
| CPLD_MAC            | 04:91:62:b2:28:20                                                                                           |
| CPU_ip_address      | 10.0.10.80                                                                                                  |
| CPU_netmask         | 255.255.255.0                                                                                               |
| CPU_MAC             | 04:91:62:b2:6c:b8                                                                                           |
| SN                  |                                                                                                             |
| PN                  | SKA_SMB                                                                                                     |
| bios                | v1.0.0 (CPLD_0xbe7a1014_0x202106150954-MCU_0xdb000102_0x2021040600125020-KRN_4.14.98-0002-00003-gffba12ad9) |
| BOARD_MODE          | SUBRACK                                                                                                     |
| LOCATION            | 65535:255:255                                                                                               |
| HARDWARE_REV        | v1.2.4                                                                                                      |

| BIOS      |                                                                                                             |
|:----------|:------------------------------------------------------------------------------------------------------------|
| ACTUAL    | v1.0.0 (CPLD_0xbe7a1014_0x202106150954-MCU_0xdb000102_0x2021040600125020-KRN_4.14.98-0002-00003-gffba12ad9) |
| REQUESTED | v1.0.0 (CPLD_0xbe7a1014_0x202106150954-MCU_0xdb000102_0x2021040600125020-KRN_4.14.98-0002-00003-gffba12ad9) |
```

## Change ip address
`ska_low_smm_bios` can be also used to change network configuration stored into non-volatile memory.
The OS of SMM, at boot time, retrive information from non-volatile memory to generate `/etc/network/interfaces`. OS also assume, for convenience, that a ntp server is available and try to exec a update time at boot.

```
$ python -m ska_low_smm_bios --change-ip 10.0.10.64 --change-netmask 255.255.0.0 --change-gateway 10.0.10.254
==============================================================
PLEASE READ THE AGREEMENT CAREFULLY.
BY USING THIS SOFTWARE, YOU ACCEPT THE TERMS OF THE AGREEMENT.
You can read license by '--show-license' option
==============================================================

| BOARD INFO          |                                                                                                             |
|:--------------------|:------------------------------------------------------------------------------------------------------------|
| CPLD_ip_address     | 10.0.10.86                                                                                                  |
| CPLD_netmask        | 255.255.255.0                                                                                               |
| CPLD_gateway        | 10.0.10.1                                                                                                   |
| CPLD_ip_address_eep | 10.0.10.86                                                                                                  |
| CPLD_netmask_eep    | 255.255.255.0                                                                                               |
| CPLD_gateway_eep    | 10.0.10.1                                                                                                   |
| CPLD_MAC            | 04:91:62:b2:28:20                                                                                           |
| CPU_ip_address      | 10.0.10.80                                                                                                  |
| CPU_netmask         | 255.255.255.0                                                                                               |
| CPU_MAC             | 04:91:62:b2:6c:b8                                                                                           |
| SN                  |                                                                                                             |
| PN                  | SKA_SMB                                                                                                     |
| bios                | v1.0.0 (CPLD_0xbe7a1014_0x202106150954-MCU_0xdb000102_0x2021040600125020-KRN_4.14.98-0002-00003-gffba12ad9) |
| BOARD_MODE          | SUBRACK                                                                                                     |
| LOCATION            | 65535:255:255                                                                                               |
| HARDWARE_REV        | v1.2.4                                                                                                      |

=============== WARNING !!! ===================
Error in netwrok configuration may leads to unreachable board.

Below ip addresses MUST be reserved for board function:
| RESERVED IPs   |            |
|:---------------|:-----------|
| 10.0.10.64     | CPU        |
| 10.0.10.65     | reserved   |
| 10.0.10.66     | reserved   |
| 10.0.10.67     | reserved   |
| 10.0.10.68     | reserved   |
| 10.0.10.69     | reserved   |
| 10.0.10.70     | CPLD       |
| 10.0.10.71     | SLOT-1 TPM |
| 10.0.10.72     | SLOT-2 TPM |
| 10.0.10.73     | SLOT-3 TPM |
| 10.0.10.74     | SLOT-4 TPM |
| 10.0.10.75     | SLOT-5 TPM |
| 10.0.10.76     | SLOT-6 TPM |
| 10.0.10.77     | SLOT-7 TPM |
| 10.0.10.78     | SLOT-8 TPM |
| 10.0.10.79     | reserved   |

|                 | ACTUAL        | NEW         |
|:----------------|:--------------|:------------|
| CPU  ip address | 10.0.10.80    | 10.0.10.64  |
| CPLD ip address | 10.0.10.86    | 10.0.10.70  |
| netmask         | 255.255.255.0 | 255.255.0.0 |
| gateway         | 10.0.10.1     | 10.0.10.254 |
Do you want continue (y/N)

```

Here you can found network configuration applied

`/etc/network/interfaces`
```
# interfaces(5) file used by ifup(8) and ifdown(8)
# Include files from /etc/network/interfaces.d:
# WARNING!!! This file will be overwritten at boot by rc.local
source-directory /etc/network/interfaces.d

auto eth0
allow-hotplug eth0
iface eth0 inet static
	address 10.0.10.80
	netmask 255.255.255.0

```

`/etc/resolv.conf`
```
nameserver 8.8.8.8
nameserver 8.8.4.4
```

`route`
```
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         10.0.10.1       0.0.0.0         UG    0      0        0 eth0
10.0.10.0       0.0.0.0         255.255.255.0   U     0      0        0 eth0
```

## Misc

### Clean up filesystem before backup
 ```
 cat /dev/zero > zero.file
 sync
 rm zero.file
 history -c 
 ```

### Create ISO from uSD

```
sudo dd if=/dev/sdb bs=1M count=8192 status=progress | gzip -c > ska-low-smm_v0.4.0_20230516.img.tgz
```

### Create uSD from ISO

```
gunzip -c ska-low-smm_v0.4.0_20230516.img.tgz  | sudo dd of=/dev/sdb status=progress
```

### Create filesystem backup

```
sudo tar -cvpzf backup.tar.gz --exclude=/backup.tar.gz --one-file-system /
```

