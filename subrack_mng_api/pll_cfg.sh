#!/bin/bash

echo "number of param $#"
if [ $# -ge 2 ]; then
  echo "IP Address of CPLD Required"
  exit
else
  echo "ip addrss $1"
  mng_ip=$1
fi
cd ../cpld_mng_api/
python management_pll.py -l -f pll_subrack_OCXO.txt --ip $mng_ip -p 10000
python management_pll.py -u --ip $mng_ip
python management_pll.py -c --ip $mng_ip
python management_pll.py --ip $mng_ip 0x3001

