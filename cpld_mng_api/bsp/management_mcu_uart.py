__author__ = "Bubs"


import logging
import time
import struct
import socket

FIFOSIZE = 1024
PAGESIZE = 256
SPICLK = 13000000


MCU_UART_BA = 0x70000


class mcuuartregisters:
    rnw = MCU_UART_BA + 0x0
    txdata = MCU_UART_BA + 0x4
    rxdata = MCU_UART_BA + 0x8
    status = MCU_UART_BA + 0xC


class mcuregs:
    GPReg0 = 0x30100
    samresetn = 0x900


class uart_operation:
    send = 0
    receive = 1


class MngMcuUart:
    """Management Class for CPLD2MCU Uart control for MCU update"""

    def __init__(self, board, rmp):
        """
        Initializes an instance of MngMcuUart.

        :param board: Pointer to board instance.
        :param rmp: The RMP (Remote Memory Probe) instance for communication.

        """
        self.rmp = rmp
        self.board = board
        self.add4bytemode = False

    def uart_send_byte(self, dataw):
        """
        Sends a single byte over UART to the MCU.

        :param dataw: The byte of data to be sent.

        :return: The operation status (0 for success, 1 for timeout).

        """
        self.board[mcuuartregisters.txdata] = dataw
        self.board[mcuuartregisters.rnw] = uart_operation.send
        op_status = 0
        start = time.time()
        while 1:
            if self.board[mcuuartregisters.status] & 0x1 == 0:
                break
            else:
                now = time.time()
                if now - start > 5:
                    op_status = 1
                    break
        return op_status

    def uart_receive_byte(self):
        """
        Receives a single byte over UART from the MCU.

        :return: A tuple containing the received byte and the operation status
                 (0 for success, 1 for timeout).

        """
        op_status = 0
        start = time.time()
        rxdata = 0
        while 1:
            if (self.board[mcuuartregisters.status] & 0x2) == 0x2:
                self.board[mcuuartregisters.rnw] = uart_operation.receive
                rxdata = self.board[mcuuartregisters.rxdata]
                break
            else:
                now = time.time()
                if now - start > 30:
                    op_status = 1
                    break
        return rxdata, op_status

    def uart_send_buffer(self, databuff):
        """
        Sends a buffer of data over UART to the MCU.

        :param databuff: The data buffer to be sent.

        :return: The operation status (0 for success, 1 for timeout).

        """
        op_status = 0
        rxdata = []
        start = time.time()
        for i in range(0, len(databuff)):
            self.board[mcuuartregisters.txdata] = databuff[i]
            self.board[mcuuartregisters.rnw] = uart_operation.send
            while 1:
                if self.board[mcuuartregisters.status] & 0x1 == 0:
                    break
                else:
                    now = time.time()
                    if now - start > 1:
                        op_status = 1
                        return op_status
        return op_status

    def uart_send_buffer_wrx(self, databuff):
        """
        Sends a buffer of data over UART to the MCU and receives a response.

        :param databuff: The data buffer to be sent.

        :return: A tuple containing the operation status (0 for success, 1 for timeout)
                 and the received data buffer.

        """
        op_status = 0
        rxdata = []
        start = time.time()
        for i in range(0, len(databuff)):
            self.board[mcuuartregisters.txdata] = databuff[i]
            self.board[mcuuartregisters.rnw] = uart_operation.send
            now = time.time()
            while 1:
                if self.board[mcuuartregisters.status] & 0x1 == 0:
                    now_while = time.time()
                    print("[uart2mcu_write] time now_while %.6f" % now_while)
                    break
                else:
                    now = time.time()
                    if now - start > 1:
                        op_status = 1
                        return op_status
        while 1:
            if (self.board[mcuuartregisters.status] & 0x2) == 0x2:
                self.board[mcuuartregisters.rnw] = uart_operation.receive
                rxdata.append(self.board[mcuuartregisters.rxdata])
            else:
                now = time.time()
                if now - start > 1:
                    print("[uart2mcu_read] time now %d" % now)
                    break
        return op_status, rxdata

    def start_mcu_sam_ba_monitor(self):
        """
        Initiates the MCU SAM-BA monitor.

        :return: The operation status (0 for success, 1 for timeout).

        """
        op_status = 0
        self.board[mcuregs.GPReg0] = 0xB007
        start = time.time()
        time.sleep(0.2)
        while 1:
            if self.board[mcuregs.GPReg0] == 0x5E7:
                self.board[mcuregs.samresetn] = 0
                time.sleep(0.01)
                self.board[mcuregs.samresetn] = 1
                time.sleep(0.1)
                break
            else:
                now = time.time()
                if now - start > 20:
                    op_status = 1
                    break
        return op_status

    def reset_mcu(self):
        """
        Resets the MCU.

        """
        self.board[mcuregs.samresetn] = 0
        time.sleep(0.01)
        self.board[mcuregs.samresetn] = 1
        time.sleep(0.1)
