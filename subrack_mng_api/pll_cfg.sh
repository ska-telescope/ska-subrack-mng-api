#!/bin/bash
cd /root/management_fpga_scripts/trunk/Firmware/tools/board/
python management_pll.py -l -f pll_subrack_OCXO.txt --ip 10.0.10.10 -p 10000
python management_pll.py -u --ip 10.0.10.10
python management_pll.py -c --ip 10.0.10.10
python management_pll.py --ip 10.0.10.10 0x3001
