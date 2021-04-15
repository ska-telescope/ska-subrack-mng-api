__author__ = 'Bubs'


import logging
import time
import struct
import socket

FIFOSIZE = 1024
PAGESIZE = 256
SPICLK = 13000000



MCU_UART_BA=0x70000
class mcuuartregisters():
        rnw     = MCU_UART_BA+0x0
        txdata  = MCU_UART_BA+0x4
        rxdata  = MCU_UART_BA+0x8
        status  = MCU_UART_BA+0xc



class mcuregs():
    GPReg0 = 0x30100
    samresetn=0x900


class uart_operation():
    send=0
    receive=1

class MngMcuUart():
    """ Management Class for CPLD2MCU Uart control for MCU update """
    def __init__(self, board, rmp):
        """ SPI4Flash initialiser
        :param board: Pointer to board instance
        """
        self.rmp = rmp
        self.board = board
        self.add4bytemode = False

    #######################################################################################
    def uart_send_byte(self,dataw):
        self.board[mcuuartregisters.txdata]=dataw
        self.board[mcuuartregisters.rnw]=uart_operation.send
        op_status=0
        start = time.time()
        while (1):
            if self.board[mcuuartregisters.status]&0x1==0:
                break
            else:
                now= time.time()
                #print("[uart2mcu_write] time now %d" %now)
                if (now-start>5):
                    op_status=1
                    break
        return op_status

    def uart_receive_byte(self):
        op_status=0
        start = time.time()
        rxdata=0
        while (1):
            if (self.board[mcuuartregisters.status]&0x2)==0x2:
                self.board[mcuuartregisters.rnw]=uart_operation.receive
                rxdata=self.board[mcuuartregisters.rxdata]
                print ("uart2mcu_read")
                break
            else:
                now= time.time()
                if (now-start>30):
                    print("[uart2mcu_read] time now %d" % now)
                    op_status=1
                    break
        return rxdata,op_status

    def uart_send_buffer(self,databuff):
        op_status=0
        rxdata=[]
        start = time.time()
        #print("[uart2mcu_write] time start %.6f" % start)
        for i in range (0, len(databuff)):
            self.board[mcuuartregisters.txdata]=databuff[i]
            self.board[mcuuartregisters.rnw]=uart_operation.send
            #now = time.time()
            #print("[uart2mcu_write] time now %.6f" %now)
            while (1):
                if self.board[mcuuartregisters.status]&0x1==0:
                    #now_while = time.time()
                    #print("[uart2mcu_write] time now_while %.6f" %now_while)
                    break
                else:
                    now = time.time()
                    # print("[uart2mcu_write] time now %d" %now)
                    if (now - start > 1):
                        op_status = 1
                        return op_status
        return op_status

    def uart_send_buffer_wrx(self,databuff):
        op_status=0
        rxdata=[]
        start = time.time()
        print("[uart2mcu_write] time start %.6f" % start)
        for i in range (0, len(databuff)):
            self.board[mcuuartregisters.txdata]=databuff[i]
            self.board[mcuuartregisters.rnw]=uart_operation.send
            now = time.time()
            print("[uart2mcu_write] time now %.6f" %now)
            while (1):
                if self.board[mcuuartregisters.status]&0x1==0:
                    now_while = time.time()
                    print("[uart2mcu_write] time now_while %.6f" %now_while)
                    break
                else:
                    now = time.time()
                    # print("[uart2mcu_write] time now %d" %now)
                    if (now - start > 1):
                        op_status = 1
                        return op_status
        while (1):
            if (self.board[mcuuartregisters.status]&0x2)==0x2:
                self.board[mcuuartregisters.rnw]=uart_operation.receive
                rxdata.append(self.board[mcuuartregisters.rxdata])
                #print ("uart2mcu_read")
            else:
                now= time.time()
                if (now-start>1):
                    print("[uart2mcu_read] time now %d" % now)
                    break
        return op_status,rxdata

    def start_mcu_sam_ba_monitor(self):
        print ("Start MCU Monitor")
        op_status=0
        self.board[mcuregs.GPReg0]=0xb007
        start = time.time()
        time.sleep(0.2)
        while(1):
            if self.board[mcuregs.GPReg0]==0x5e7:
                print("MCU Ready for Reset")
                self.board[mcuregs.samresetn]=0
                time.sleep(0.01)
                self.board[mcuregs.samresetn]=1
                time.sleep(0.1)
                break
            else:
                now= time.time()
                if (now-start>20):
                    op_status=1
                    break
        return op_status

    def reset_mcu(self):
        self.board[mcuregs.samresetn] = 0
        time.sleep(0.01)
        self.board[mcuregs.samresetn] = 1
        time.sleep(0.1)

