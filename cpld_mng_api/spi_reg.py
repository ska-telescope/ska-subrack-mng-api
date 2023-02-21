import sys
sys.path.append("../")
import config.manager as config_man
from bsp.management import *
from optparse import OptionParser

config = config_man.get_config_from_file("../config/config.txt", "MANAGEMENT", False)
inst = MANAGEMENT(ip=config['FPGA_IP'], port=config['UDP_PORT'], timeout=5)


if __name__ == "__main__":
    parser = OptionParser()
    (options, args) = parser.parse_args()
    if len(args) == 1:
        print (hex(inst.read_spi(int(args[0], 16))))
    elif len(args) == 2:
        inst.write_spi(int(args[0], 16), int(args[1], 16))
    else:
        print ("Error. Wrong number of parameters")

inst.disconnect()


