import os
import socket
import struct
import logging
logger=logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)

class eeprom():
    def __init__(self,name,mng,i2c_bus,i2c_add,eep_sec):
        self.name = name
        self.mng = mng
        self.i2c_bus = i2c_bus
        self.i2c_add = i2c_add
        self.eep_sec = eep_sec
    
    def ip2long(self, ip):
        """
        Convert an IP string to long
        """
        packed_ip = socket.inet_aton(ip)
        return struct.unpack("!L", packed_ip)[0]

    def long2ip(self, ip):
        """
        Convert long to IP string
        """
        return socket.inet_ntoa(struct.pack("!I", ip))

    def eep_rd8(self, offset, release_lock = True):
        # data, status = self.mng.fpgai2c_read8(self.i2c_add, offset, self.i2c_bus)
        # if status != 0:
        #     logger.error(self.name + " Error reading on device " + hex(self.i2c_add))
        #     return None
        # return data
        return self.mng.read_i2c(self.i2c_bus, self.i2c_add>>1, offset, "b", release_lock)

    def eep_rd32(self, offset):
        rd = 0
        release_lock = False
        for n in range(4):
            if n == 4-1:
                release_lock = True
            rd = rd << 8
            rd = rd | self.eep_rd8(offset+n, release_lock = release_lock)
        return rd

    def rd_string(self, partition):
        return self._rd_string(partition["offset"], partition["size"])

    def _rd_string(self, offset, max_len=16):
        addr = offset
        string = ""
        for i in range(max_len):
            byte = self.eep_rd8(addr, release_lock = False)
            if byte == ord("\n") or byte == 0xff or byte == 0x0:
                break
            string += chr(byte)
            addr += 1
        self.eep_rd8(offset, release_lock = True)
        return string

    def eep_wr8(self, offset, data, release_lock = True):
        # return self.mng.fpgai2c_write8(self.i2c_add, offset, data, self.i2c_bus)
        return self.mng.write_i2c(self.i2c_bus,self.i2c_add>>1, offset, "b", data, release_lock)
    
    def eep_wr32(self, offset, data):
        release_lock = False
        for n in range(4):
            if n == 4-1:
                release_lock = True
            self.eep_wr8(offset+n, (data >> 8*(3-n)) & 0xFF,release_lock=release_lock)
        return
    
    def wr_string(self, partition, string):
        return self._wr_string(partition["offset"], string, partition["size"])

    def _wr_string(self, offset, string, max_len=16):
        addr = offset
        for i in range(len(string)):
            self.eep_wr8(addr, ord(string[i]), release_lock = False)
            addr += 1
            if addr >= offset + max_len:
                break
        if addr < offset + max_len:
            self.eep_wr8(addr, ord("\n"), release_lock = True)
        else:
            self.eep_rd8(offset, release_lock = True)

    def get_field(self, key):
        if self.eep_sec[key]["type"] == "ip":
            return self.long2ip(self.eep_rd32(self.eep_sec[key]["offset"]))
        elif self.eep_sec[key]["type"] == "bytearray":
            arr = bytearray()
            for offset in range(self.eep_sec[key]["size"]):
                arr.append(self.eep_rd8(self.eep_sec[key]["offset"]+offset))
            return arr
        elif self.eep_sec[key]["type"] == "string":
            return self.rd_string(self.eep_sec[key])
        elif self.eep_sec[key]["type"] == "uint":
            val = 0
            for offset in range(self.eep_sec[key]["size"]):
                val = val * 256 + self.eep_rd8(self.eep_sec[key]["offset"]+offset)
            return val
        
    def set_field(self, key, value, override_protected=False):
        if self.eep_sec[key]["protected"] is False or override_protected:
            if self.eep_sec[key]["type"] == "ip":
                self.eep_wr32(self.eep_sec[key]["offset"], self.ip2long(value))
            elif self.eep_sec[key]["type"] == "bytearray":
                for offset in range(self.eep_sec[key]["size"]):
                    self.eep_wr8(self.eep_sec[key]["offset"] + offset,
                             ((value & (0xff << (8*(self.eep_sec[key]["size"]-1-offset))))
                              >> (8*(self.eep_sec[key]["size"]-1-offset))) & 0xff)
            elif self.eep_sec[key]["type"] == "string":
                self.wr_string(self.eep_sec[key], value)
            elif self.eep_sec[key]["type"] == "uint":
                val = value
                for offset in range(self.eep_sec[key]["size"]):
                    self.eep_wr8(self.eep_sec[key]["offset"]+offset, val & 0xff)
                    val = val >> 8
        else:
            print("Writing attempt on protected sector %s" % key)
    
    def get_fields(self):
        res={}
        for key,value in self.eep_sec.items():
            res[key] = self.get_field(key)
        return res