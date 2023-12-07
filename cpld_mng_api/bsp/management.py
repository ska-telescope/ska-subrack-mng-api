import os
import re
import sys

# import netproto.rmp as rmp
import lxml.etree as ET
from .management_bsp import MANAGEMENT_BSP
from .management_flash import MngProgFlash
from .management_mcu_uart import MngMcuUart
from .management_spi import MANAGEMENT_SPI
import zlib
import binascii


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import netproto.rmp as rmp

MAX_PLL_REG_ADD = 0x3A3C


def hexstring2ascii(hexstring, xor=0):
    """Convert a hexstring to an ASCII-String.

    Args:
        hexstring (str): The input hex string.
        xor (int): XOR value as an integer (default is 0).

    Returns:
        str: The converted ASCII string.
    """
    ascii_str = ""
    for i in range(0, len(hexstring) / 2):
        ascii_str = ascii_str + chr(int(hexstring[2 * i : 2 * i + 2], 16) ^ xor)
    return ascii_str


def format_num(num):
    """Convert a number to a string."""
    return str(num)


def get_max_width(table1, index1):
    """Get the maximum width of the given column index"""
    return max([len(format(row1[index1])) for row1 in table1])


def pprint_table(table):
    """Prints out a table of data, padded for alignment.

    Args:
        table (list): The table to print. A list of lists.
                     Each row must have the same number of columns.
    """
    col_paddings = []
    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # print row
        # left col
        print(
            row[0].ljust(col_paddings[0] + 1)(),
        )
        # rest of the cols
        for i in range(1, len(row)):
            col = format_num(row[i]).rjust(col_paddings[i] + 2)
            print(
                col,
            )
        print("")


def filter_list_by_level(reg_name_list, reg_name):
    """Filter a list of register names by level."""
    filter_list = []
    level_num = len(reg_name.split("."))
    for reg in reg_name_list:
        if len(reg.split(".")) == level_num and reg != reg_name:
            filter_list.append(reg)
    return filter_list


def get_shift_from_mask(mask):
    """Get the shift value from a mask."""
    mask = int(mask, 16)
    shift = 0
    while (mask & 0x1) != 1:
        shift += 1
        mask = mask >> 1
    return shift


class MANAGEMENT:
    """Class representing a MANAGEMENT instance."""

    def __init__(self, **kwargs):
        """Initialize the MANAGEMENT instance.

        Args:
            **kwargs: Variable keyword arguments for configuration.
        """
        self.reg_list = []
        self.reg_dict = {}
        self.reg_sel_list = []
        self.reg_sel_dict = {}
        self.board = ""
        self.state = "Created"
        self.extended_info = ""

        if not "ip" in kwargs.keys():
            print("Error! An IP address must be specified!")
            sys.exit()
        else:
            ip = kwargs["ip"]
            # print("provided ip %s" %(ip) )
        if not "port" in kwargs.keys():
            print("Assuming UDP port 10000")
            port = 10000
        else:
            port = int(kwargs["port"])
        if not "timeout" in kwargs.keys():
            print("Assuming UDP socket timeout 1 second")
            timeout = 1
        else:
            timeout = int(kwargs["timeout"])
        if "host_ip" in kwargs.keys():
            self.rmp = rmp.rmpNetwork(kwargs["host_ip"], ip, port, timeout)
        else:
            self.rmp = rmp.rmpNetwork("", ip, port, timeout)
        # print "IP init: " + ip
        self.state = "Connected"
        if "board_reg" in kwargs.keys():
            raise NameError(
                "board_reg is not supported, board name must be retrieved from the extended info string!"
            )
        elif "board" in kwargs.keys():
            self.board = kwargs["board"]
        else:
            # self.board = self.get_board(0x10)
            self.board = "MNG"
            # self.board = "KCU105"

        # self.spi = TPM_SPI(self.board, self.rmp)
        self.bsp = MANAGEMENT_BSP(self.board, self.rmp)
        self.spiflash = MngProgFlash(self, self.rmp)
        self.mcuuart = MngMcuUart(self, self.rmp)

    def __getitem__(self, key):
        """Override __getitem__, return value from the board.

        Args:
            key (Union[str, Tuple]): The key or tuple representing the key.

        Returns:
            Union[int, str]: The value associated with the key.
        """
        if type(key).__name__ == "tuple":
            k = key[0]
            h = 1
        else:
            k = key
            h = 0
        rd = self.read_register(k)
        if h == 1:
            return hex(rd)
        else:
            return rd

    def __setitem__(self, key, value):
        """Override __setitem__, set value on the board.

        Args:
            key (Union[str, Tuple]): The key or tuple representing the key.
            value: The value to set.
        """
        self.write_register(key, value)
        return

    def __len__(self):
        """Override __len__, return the number of registers.

        Returns:
            int: The number of registers.
        """
        self.checkLoad()
        return len(self.reg_dict.keys())

    def __repr__(self):
        """Override __repr__, list register names.

        Returns:
            str: An empty string.
        """
        self.list_register_names()
        return ""

    def get_xml_from_board(self, xml_map_offset):
        """Get XML data from the board."""
        # read the offset where the zipped XML is stored
        xml_off = self.read_register(xml_map_offset)
        # first 4 bytes are the zipped XML file length in byte
        xml_len = self.read_register(xml_off)
        # read the zipped XML, this should be optimized using larger accesses
        xml_hex_str = ""
        byte_to_read = xml_len
        byte_offset = xml_off + 4
        req_len = 256
        while True:
            if byte_to_read < req_len * 4:
                rd = self.read_register(byte_offset, n=byte_to_read / 4 + 1)
                byte_to_read = 0
            else:
                rd = self.read_register(byte_offset, n=req_len)
                byte_to_read -= req_len * 4
                byte_offset += req_len * 4
            if type(rd) == list:
                for n in rd:
                    xml_hex_str += format(n, "08x")
            else:
                print(str(rd))
                xml_hex_str += format(rd, "08x")
            if byte_to_read == 0:
                break
        # for n in range(xml_len/(8)+1):
        #   xml_hex_str += format(self.read_register(xml_off+4*(n+1)),'08x')
        # decompress zipped XML
        xml = zlib.decompress(binascii.unhexlify(xml_hex_str[: 2 * xml_len]))
        # this string contains the decompressed XML
        return xml

    def get_extended_info(self, ext_info_offset=0x10):
        """Get the extended info string from the board."""
        # read the offset where the extended info string is stored
        ext_off = self.read_register(ext_info_offset)
        # first 4 bytes are the zipped XML file length in byte
        ext_len = self.read_register(ext_off)
        # read the zipped XML, this should be optimized using larger accesses
        hex_str = ""
        byte_to_read = ext_len
        byte_offset = ext_off + 4
        req_len = 256
        while True:
            if byte_to_read < req_len * 4:
                rd = self.read_register(byte_offset, n=byte_to_read / 4 + 1)
                byte_to_read = 0
            else:
                rd = self.read_register(byte_offset, n=req_len)
                byte_to_read -= req_len * 4
                byte_offset += req_len * 4
            if type(rd) == list:
                for n in rd:
                    hex_str += format(n, "08x")
            else:
                print(str(rd))
                hex_str += format(rd, "08x")
            if byte_to_read == 0:
                break
        info = zlib.decompress(binascii.unhexlify(hex_str[: 2 * ext_len]))
        # print info
        return info

    def get_board(self, ext_info_offset=0x10):
        """Get the board name from the extended info string.

        Args:
            ext_info_offset (int, optional): Offset for extended info. Defaults to 0x10.

        Returns:
            str: The extracted board name.

        Raises:
            NameError: If the field BOARD doesn't exist in the extended info.
        """
        self.extended_info = self.get_extended_info(ext_info_offset=0x10)
        my_regex = r"" + re.escape("BOARD: ") + r"\s*(\w+)"
        m = re.search(my_regex, self.extended_info)
        if m is not None:
            return m.group(1)
        else:
            print("Field BOARD" + " doesn't exist in extended info!")
            sys.exit(1)

    def load_firmware_blocking(self, Device, path_to_xml_file="", xml_map_offset=0x8):
        """Load firmware blocking."""
        if path_to_xml_file == "":
            xml_str = self.get_xml_from_board(xml_map_offset)
            root = ET.fromstring(xml_str)
        else:
            tree = ET.parse(path_to_xml_file)
            root = tree.getroot()

        for node in root.iter("node"):
            if node.get("absolute_id") is not None:
                # reg = {
                # 'name'        : '%s.%s' % (names[dev], registers[i].name),
                # 'address'     : registers[i].address,
                # 'type'        : RegisterType(registers[i].type),
                # 'device'      : dev,
                # 'permission'  : Permission(registers[i].permission),
                # 'size'        : registers[i].size,
                # 'bitmask'     : registers[i].bitmask,
                # 'bits'        : registers[i].bits,
                # 'value'       : registers[i].value,
                # 'description' : registers[i].description
                # }

                local_dict = {}
                local_dict["name"] = None
                local_dict["address"] = "None"
                local_dict["bitmask"] = "None"
                local_dict["size"] = "None"
                local_dict["permission"] = "None"
                local_dict["description"] = "None"

                if node.get("absolute_id") != None:
                    local_dict["name"] = node.get("absolute_id")
                if node.get("absolute_offset") != None:
                    local_dict["address"] = node.get("absolute_offset")
                if node.get("mask") != None:
                    local_dict["bitmask"] = node.get("mask")
                if node.get("size") != None:
                    local_dict["size"] = node.get("size")
                if node.get("permission") != None:
                    local_dict["permission"] = node.get("permission")
                if node.get("description") != None:
                    local_dict["description"] = node.get("description")

                self.reg_list.append(local_dict)
                self.reg_dict[node.get("absolute_id")] = local_dict

        for reg in self.reg_list:
            if (
                reg["name"] != None
                and reg["bitmask"] != "None"
                and reg["size"] != "None"
            ):
                self.reg_sel_list.append(reg)
                self.reg_sel_dict[reg["name"]] = reg
        for register in self.reg_dict.keys():
            if register != None:
                reg_str = "."
                reg_str = reg_str.join(register.split(".")[:-1])
                regs = self.find_register_names(reg_str, display=False)
                regs = filter_list_by_level(regs, register)
                is_bitfield = 0
                for reg in regs:
                    if (
                        self.reg_dict[reg]["address"]
                        == self.reg_dict[register]["address"]
                    ):
                        is_bitfield = 1
                self.reg_dict[register]["is_bitfield"] = is_bitfield

    def checkLoad(self):
        """Check if the registers are loaded.

        Raises:
            NameError: If registers are not loaded or the board is not connected.
        """
        if self.reg_list == []:
            raise NameError("Registers not loaded!")
        if self.state != "Connected":
            raise NameError("Board not connected!")

    def list_register_names(self):
        """List register names.

        Raises:
            None
        """
        self.checkLoad()
        lines = []
        for reg in self.reg_list:
            if reg["name"] != None:
                if lines == []:
                    lines.append(["Name", "Address", "Bitmask", "Size"])
                lines.append(
                    [reg["name"], "0x" + reg["address"], reg["bitmask"], reg["size"]]
                )
        if lines != []:
            pprint_table(lines)

    def get_register_name_by_address(self, add):
        """Get register name by address.

        Args:
            add (int): Register address.

        Returns:
            str: Register name or "Unknown register address" if not found.
        """
        for reg in self.reg_list:
            if int(reg["address"], 16) == add:
                return reg["name"]
        return "Unknown register address"

    def find_register(self, register_name, display=False):
        """
        Find register information for provided search string.
        :param register_name: Regular expression to search against
        :param display: True to output result to console
        :return: List of found registers
        """
        # Run checks
        self.checkLoad()
        # Go through all registers and store the name of registers
        # which generate a match
        matches = []
        for reg in self.reg_list:
            if reg["name"] != None:
                if re.search(register_name, reg["name"]) != None:
                    matches.append(reg)
        # Display to screen if required
        if display:
            lines = []
            for m in matches:
                if lines == []:
                    lines.append(["Name", "Address", "Mask", "Size"])
                print(str(m))
                lines.append([m["name"], "0x" + m["address"], m["bitmask"], m["size"]])
            if lines != []:
                pprint_table(lines)
        # Return matches
        return matches

    def find_register_names(self, register_name, display=False):
        """Find register names for the provided search string.

        Args:
            register_name (str): Regular expression to search against.
            display (bool, optional): True to output result to console. Defaults to False.

        Returns:
            list: List of found register names.
        """
        found_reg = self.find_register(register_name, False)
        name_list = []
        for n in found_reg:
            name_list.append(n["name"])
            if display == True:
                print(n["name"])
        return name_list

    def read_register(self, register, n=1, offset=0, device=None):
        """Get register value
        :param register: Register name
        :param n: Number of words to read
        :param offset: Memory address offset to read from
        :param device: Device/node can be explicitly specified
        :return: Values
        """

        if type(register) in [int, int]:
            return self.rmp.rd32(register + offset, n)
        else:
            self.checkLoad()
            if not register in self.reg_dict.keys():
                print(register)
                print("Error: register " + register + " not found!")
            else:
                # check if it is a bitfield and other bitfields are present
                is_bitfield = self.reg_dict[register]["is_bitfield"]

                if is_bitfield == 0:
                    return self.rmp.rd32(
                        int(self.reg_dict[register]["address"], 16) + offset, n
                    )
                else:
                    rd = self.rmp.rd32(
                        int(self.reg_dict[register]["address"], 16) + offset, 1
                    )
                    rd = (
                        rd & int(self.reg_dict[register]["bitmask"], 16)
                    ) >> get_shift_from_mask(self.reg_dict[register]["bitmask"])
                    return rd

    def write_register(self, register, values, offset=0, device=None):
        """Set register value
        :param register: Register name
        :param values: Values to write
        :param offset: Memory address offset to write to
        :param device: Device/node can be explicitly specified
        """
        if type(register) in [int, int]:
            self.rmp.wr32(register + offset, values)
        else:
            self.checkLoad()
            if not register in self.reg_dict.keys():
                print("Error: register " + register + " not found!")
            else:
                # check if it is a bitfield and other bitfields are present
                is_bitfield = self.reg_dict[register]["is_bitfield"]

                if is_bitfield == 0:
                    self.rmp.wr32(
                        int(self.reg_dict[register]["address"], 16) + offset, values
                    )
                else:
                    rd = self.rmp.rd32(
                        int(self.reg_dict[register]["address"], 16) + offset, 1
                    )
                    if type(values) == list:
                        wdat = values[0]
                    else:
                        wdat = values
                    wdat = wdat << get_shift_from_mask(
                        self.reg_dict[register]["bitmask"]
                    )
                    self.rmp.wr32(
                        int(self.reg_dict[register]["address"], 16) + offset, wdat | rd
                    )
                return

    def get_bios(self):
        """Generate a BIOS string based on specific register values.

        Returns:
            str: BIOS information string.
        """
        string = "CPLD_"
        string += (
            hex(self.rmp.rd32(0x8))
            + "_"
            + hex(self.rmp.rd32(0x4) << 32 | self.rmp.rd32(0x0))
        )
        string += "-MCU_"
        string += (
            hex(self.rmp.rd32(0x30000))
            + "_"
            + hex(self.rmp.rd32(0x30008) << 32 | self.rmp.rd32(0x30004))
        )
        final_string = "v?.?.? (%s)" % string
        """
        for BIOS_REV in self.BIOS_REV_list:
            if BIOS_REV[1] == string:
                final_string = "v%s (%s)" % (BIOS_REV[0], string)
                break
        """
        return final_string

    def get_mac(self):
        """Retrieve the MAC address and format it as a string.

        Returns:
            str: MAC address string.
        """
        mac = self.bsp.get_field("MAC")
        mac_str = ""
        for i in range(0, len(mac) - 1):
            mac_str += "{0:02x}".format(mac[i]) + ":"
        mac_str += "{0:02x}".format(mac[len(mac) - 1])
        return mac_str

    def get_board_info(self):
        """Retrieve information about the board.

        Returns:
            dict: Board information as a dictionary.
        """
        mng_info = {
            "ip_address": self.bsp.long2ip(self.rmp.rd32(0x110)),
            "netmask": self.bsp.long2ip(self.rmp.rd32(0x114)),
            "gateway": self.bsp.long2ip(self.rmp.rd32(0x118)),
            "ip_address_eep": self.bsp.get_field("ip_address"),
            "netmask_eep": self.bsp.get_field("netmask"),
            "gateway_eep": self.bsp.get_field("gateway"),
            "MAC": self.get_mac(),
            "SN": self.bsp.get_field("SN"),
            "PN": self.bsp.get_field("PN"),
            "bios": self.get_bios(),
        }
        if self.bsp.get_field("BOARD_MODE") == 0x1:
            mng_info["BOARD_MODE"] = "SUBRACK"
        elif self.bsp.get_field("BOARD_MODE") == 0x2:
            mng_info["BOARD_MODE"] = "CABINET"
        else:
            mng_info["BOARD_MODE"] = "UNKNOWN"
            # print("Board Mode Read value ", self.bsp.get_field("BOARD_MODE"))

        location = [
            self.bsp.get_field("CABINET_LOCATION"),
            self.bsp.get_field("SUBRACK_LOCATION"),
            self.bsp.get_field("SLOT_LOCATION"),
        ]
        mng_info["LOCATION"] = (
            str(location[0]) + ":" + str(location[1]) + ":" + str(location[2])
        )

        pcb_rev = self.bsp.get_field("PCB_REV")
        if pcb_rev == 0xFF:
            pcb_rev_string = ""
        else:
            pcb_rev_string = str(pcb_rev)

        hw_rev = self.bsp.get_field("HARDWARE_REV")
        mng_info["HARDWARE_REV"] = (
            "v"
            + str(hw_rev[0])
            + "."
            + str(hw_rev[1])
            + "."
            + str(hw_rev[2])
            + pcb_rev_string
        )

        return mng_info

    def read_spi(self, address):
        """Read SPI data from the specified address.

        Args:
            address (int): The address to read from.

        Returns:
            int: The read value.
        """
        return self.bsp.spi.spi_access("rd", address, 0)

    def write_spi(self, address, value):
        """Write SPI data to the specified address.

        Args:
            address (int): The address to write to.
            value (int): The value to write.
        """
        self.bsp.spi.spi_access("wr", address, value)

    def pll_read_with_update(self, address):
        """Read from SPI with PLL update.

        Args:
            address (int): The address to read from.

        Returns:
            int: The read value.
        """
        self.write_spi(0xF, 0x1)
        return self.bsp.spi.spi_access("rd", address, 0)

    def pll_write_with_update(self, address, value):
        """Write to SPI with PLL update.

        Args:
            address (int): The address to write to.
            value (int): The value to write.
        """
        self.bsp.spi.spi_access("wr", address, value)
        self.write_spi(0xF, 0x1)

    def pll_ldcfg(self, cfg_filename):
        """Load PLL configuration from a file.

        Args:
            cfg_filename (str): The path to the configuration file.
        """
        cfgfile = open(cfg_filename, "r")
        cfglines = cfgfile.readlines()
        cfgfile.close()
        opnum = len(cfglines)
        print("Writing PLL configuration...")
        for i in range(1, opnum):
            address = cfglines[i].split(",")[0]
            value = cfglines[i].split(",")[1].splitlines()[0]
            self.write_spi(int(address, 16), int(value, 16))
        self.write_spi(0xF, 0x1)

    def pll_dumpcfg(self, cfg_filename):
        """Dump PLL configuration to a file.

        Args:
            cfg_filename (str): The path to the configuration file.
        """
        cfgfile = open(cfg_filename, "w")
        print("Reading PLL configuration...")
        cfgfile.write("Address,Data\n")
        for address in range(0, MAX_PLL_REG_ADD):
            data = self.read_spi(address)
            haddress = hex(address)
            hdata = hex(data)
            haddress = haddress[2:].zfill(4)
            hdata = hdata[2:].zfill(2)
            cfgfile.write("0x" + haddress.upper() + "," + "0x" + hdata.upper() + "\n")

    def pll_calib(self):
        """Calibrate PLL.

        This function performs calibration by writing specific values to SPI addresses.

        Raises:
            None
        """
        print("Calibrating PLL...")
        self.write_spi(0x2000, 0x0)
        self.write_spi(0xF, 0x1)
        self.write_spi(0x2000, 0x2)
        self.write_spi(0xF, 0x1)
        self.write_spi(0x2000, 0x0)
        self.write_spi(0xF, 0x1)

    def pll_ioupdate(self):
        """Update PLL IO.

        This function updates PLL IO by writing a specific value to the SPI address.

        Raises:
            None
        """
        self.write_spi(0xF, 0x1)
        print("PLL IO Updated ")

    def disconnect(self):
        """Disconnect from the network.

        This function closes the network connection and sets the state to "Unconnected".

        Raises:
            None
        """
        self.rmp.CloseNetwork()
        self.state = "Unconnected"
