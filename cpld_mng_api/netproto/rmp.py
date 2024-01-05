"""
@package rmp
UDP socket management and RMP packet encoding/decoding

This package provides functions for network initializing and basic 32-bit read/write
operations on the network-attached device using RMP protocol. This is rough and minimal code
not exploiting all the RMP protocol features.
"""

import sys
import socket
import array
from struct import unpack


class rmpNetwork:
    def __init__(self, this_ip, fpga_ip, udp_port, timeout):
        """
        Initialize the network.

        It opens the sockets and sets specific options such as socket receive time-out and buffer size.

        :param this_ip: str: Host machine IP address
        :param fpga_ip: str: Network-attached device IP address
        :param udp_port: int: UDP port
        :param timeout: int: Receive Socket time-out in seconds

        :return: int: socket handle
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet # UDP

        self.sock.settimeout(1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
        if fpga_ip == "255.255.255.255":
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((this_ip, 0))

        self.fpga_ip = fpga_ip
        self.this_ip = this_ip
        self.remote_udp_port = udp_port
        self.timeout = timeout
        self.psn = 0
        self.reliable = 0

    def CloseNetwork(self):
        """
        Close previously opened socket.
        """
        self.sock.close()
        return

    def recvfrom_to(self, buff):
        """
        Receive data from the socket within a timeout.

        :param buff: int: Buffer size

        :return: tuple: Received data and source address
        """
        attempt = 0
        while attempt < self.timeout or self.timeout == 0:
            try:
                return self.sock.recvfrom(10240)
            except:
                attempt += 1
        raise NameError("UDP timeout. No answer from the remote end!")

    def wr32(self, add, dat):
        """
        Write remote register at address 'add' with data 'dat'.

        It transmits a write request to the remote device.

        :param add: int: 32 bits remote address
        :param dat: int: 32 bits write data
        """
        req_add = add
        for i in range(3):
            try:
                self.psn += 1

                pkt = array.array("I")
                pkt.append(self.psn)  # psn
                pkt.append(2)  # opcode
                if type(dat) == list:
                    pkt.append(len(dat))  # noo
                else:
                    pkt.append(1)  # noo
                pkt.append(req_add)  # sa
                if type(dat) == list:
                    for d in dat:
                        pkt.append(d)
                else:
                    pkt.append(dat)  # dat

                self.sock.sendto(
                    bytes(pkt.tostring()), (self.fpga_ip, self.remote_udp_port)
                )
                data, addr = self.recvfrom_to(10240)

                data = bytes(data)

                psn = unpack("I", data[0:4])[0]
                add = unpack("I", data[4:8])[0]

                if psn == self.psn and add == req_add:
                    return
                elif psn != self.psn:
                    print("")
                    print("Failed UCP write, received wrong PSN ...")
                    print("Received: " + str(psn))
                    print("Expected: " + str(self.psn))
                    print("Retrying...")
                elif add != req_add:
                    print("")
                    print("Failed UCP write, error received ...")
                    print("Requested Add: " + hex(req_add))
                    print("Received Add: " + hex(add))
                    print("Retrying...")
                    self.socket_flush()
            except:
                if self.reliable == 1:
                    print("")
                    print("Failed UCP write:")
                    print("Requested Add: " + hex(req_add))
                    print("Retrying...")
                    pass
                else:
                    print("Failed UCP write. Exiting ...")
                    sys.exit(-1)
            print("Getting Last Executed PSN...")
            last_psn = self.rd32(0x30000004)
            print("Getting Last Executed PSN...", last_psn)

            if last_psn == self.psn:
                return
            else:
                pass
        print("")
        print("UCP write error")
        print("Requested Add: " + hex(req_add))
        print("Received Add: " + hex(add))
        exit(-1)

    def rd32(self, add, n=1):
        """
        Read remote register at address 'add'.

        It transmits a read request and waits for a read response from the remote device.
        Once the response is received it extracts relevant data from a specific offset within the
        UDP payload and returns it. In case no response is received from the remote device
        a socket time-out occurs.

        :param add: int: 32 bits remote address
        :param n: int: Number of words to read (default is 1)

        :return: int or list: Read data
        """
        req_add = add
        for i in range(3):
            self.psn += 1

            try:
                pkt = array.array("I")
                pkt.append(self.psn)  # psn
                pkt.append(1)  # opcode
                pkt.append(n)  # noo
                pkt.append(req_add)  # sa

                self.sock.sendto(
                    bytes(pkt.tostring()), (self.fpga_ip, self.remote_udp_port)
                )

                data, addr = self.recvfrom_to(10240)

                data = bytes(data)

                psn = unpack("I", data[0:4])[0]
                add = unpack("I", data[4:8])[0]

                if psn == self.psn and add == req_add:
                    dat = unpack("I" * n, data[8:])
                    dat_list = []
                    for k in range(n):
                        dat_list.append(dat[k])
                    if n == 1:
                        return dat_list[0]
                    else:
                        return dat_list
                else:
                    print("")
                    print("Failed UCP read, received wrong PSN or error detected ...")
                    print("Received: " + str(psn))
                    print("Expected: " + str(self.psn))
                    print("Requested Add: " + hex(req_add))
                    print("Received Add: " + hex(add))
                    print("Retrying...")
                    self.socket_flush()
            except:
                if self.reliable == 1:
                    print("Failed UCP read, retrying ...")
                else:
                    print("Failed UCP read, exiting ...")
                    sys.exit(-1)

        print("")
        print("UCP read error")
        print("Requested Add: " + hex(req_add))
        exit(-1)

    def socket_flush(self):
        """
        Flush UCP socket and recreate it.
        """
        print("Flushing UCP socket...")
        self.sock.close()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet # UDP

        self.sock.settimeout(1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
        if self.fpga_ip == "255.255.255.255":
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((self.this_ip, 0))
