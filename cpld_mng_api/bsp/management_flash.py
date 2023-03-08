__author__ = 'Bubs'

import logging
import time
import struct
import socket
# import netproto.rmp as rmp

FIFOSIZE = 1024
PAGESIZE = 256
SPICLK = 13000000


class FlasdhDev():
    def __init__(self, name="", description="", jedecID=0, pageSize=0, sectorSize=0, sectorCount=0, slaveID=0):
        self.name = name
        self.description = description
        self.jedecID = jedecID
        self.pageSize = pageSize
        self.sectorSize = sectorSize
        self.sectorCount = sectorCount
        self.slaveID = slaveID



"""
FlashDevice_CPLD = FlasdhDev(name="Flash_CPLD",
                             description="winbond,w25q32jv",
                             jedecID=0xef4016,
                             pageSize=256,
                             sectorSize=64 * 1024,
                             sectorCount=64,
                             slaveID=0x00000000)
"""
FlashDevice_CPLD = FlasdhDev(name="Flash_CPLD",
                             description="winbond,w25q128jv",
                             jedecID=0xef7018,
                             pageSize=256,
                             sectorSize=64 * 1024,
                             sectorCount=256,
                             slaveID=0x00000000)


FlashDevices = [FlashDevice_CPLD]


class spiregisters():
    spi_cs_ow = 0x0800
    spi_cs0 = 0x0800
    spi_tx_byte = 0x0804
    spi_rx_byte = 0x0808
    spi_tx_buf_len = 0x080c
    spi_rx_buf_len = 0x0810
    spi_fifo_addr = 0x0814
    spi_mux = 0x0818
    spi_rxtxbuffer = 0x80000



class MngProgFlash():
    """ Management Class for CPLD and FPGA SPI Flash bitfile storage/access class """
    def __init__(self, board, rmp):
        """ SPI4Flash initialiser
        :param board: Pointer to board instance
        """
        self.rmp = rmp
        self.board = board
        self.add4bytemode = False

    #######################################################################################

    # #####################    SPI METHODS SECTION   ###############################
    def spi_chipselect(self, isactive):
        # mask = 0x0001
        self.board[spiregisters.spi_cs0]=0x10001

    def spi_resetfifo(self):
        self.board[spiregisters.spi_fifo_addr]=0

    def spi_trigger(self, length):
        self.board[spiregisters.spi_tx_byte]=length

    def spi_config(self, spi_cs_ow):
        reg=self.board[spiregisters.spi_cs_ow]
        if spi_cs_ow==1:
            self.board[spiregisters.spi_cs_ow]=reg|(0x00001)
        else:
            self.board[spiregisters.spi_cs_ow] = reg & (0x10000)
    def spi_rx_available(self):
        tmp = self.board[spiregisters.spi_rx_byte]
        return tmp

    def spi_tx_remaining(self):
        tmp = self.board[spiregisters.spi_rx_byte]
        return tmp

    def spi_sync(self, slaveid, txBuffer, cmd, length):
        _length = length
        self.spi_config(1)
        self.spi_chipselect(False)

        if length >= 256:
            formatted_cmd = list(struct.unpack_from('I' * (len(cmd) // 4), cmd))
            txBuffer = formatted_cmd + txBuffer
            self.board[spiregisters.spi_rxtxbuffer] = txBuffer[0: (260 // 4)]
            self.spi_trigger(260)
            while (1):
                remaining = self.spi_tx_remaining()
                if remaining <= 0:
                    break
            self.spi_resetfifo()
            ba = spiregisters.spi_rxtxbuffer
            rxbuffer = self.board.read_register(ba, n=(260 // 4),offset=0)
            self.spi_chipselect(True)
            self.spi_resetfifo()
            return rxbuffer[1:]
        elif length < 4:
            formatted_cmd = list(struct.unpack_from('I' * (len(cmd) // 4), cmd))
            txBuffer = formatted_cmd + txBuffer
            self.board[spiregisters.spi_rxtxbuffer] = txBuffer[0: length * 4]
            self.spi_trigger(length)
            while (1):
                remaining = self.spi_tx_remaining()
                if remaining <= 0:
                    break
            self.spi_resetfifo()
            ba = spiregisters.spi_rxtxbuffer
            rxbuffer = self.board.read_register(ba, n=2, offset=0)
            self.spi_chipselect(True)
            self.spi_resetfifo()
            return rxbuffer[0]
        else:
            formatted_cmd = list(struct.unpack_from('I' * (len(cmd) // 4), cmd))
            txBuffer = formatted_cmd + txBuffer
            self.board[spiregisters.spi_rxtxbuffer] = txBuffer[0: length // 4]
            print (self.board[spiregisters.spi_fifo_addr])
            self.spi_trigger(length)
            while (1):
                remaining = self.spi_tx_remaining()
                if remaining <= 0:
                    break
            self.spi_resetfifo()
            ba = spiregisters.spi_rxtxbuffer
            print("preread")
            rxbuffer = self.board.read_register(ba, n=length // 4, offset=0)
            print("after read")
            self.spi_chipselect(True)
            self.spi_resetfifo()
            print("complete")
            if (cmd[0] & 0xff) == 0x9F:
                return rxbuffer

    def spi_mux_selection(self, slaveid):
        self.board[spiregisters.spi_mux] = slaveid

    # ########## FLASH COMMAND METHODS SECTION ####################################

    def SPITransaction(self, device, TxBuffer, cmd, size):
        RxBuffer = self.spi_sync(device.slaveID, TxBuffer, cmd, size)
        return RxBuffer

    def FlashDevice_readReg(self, device, reg):
        cmd = bytearray(4)
        txBuffer = [0] * 4
        cmd[0] = reg
        cmd[1] = 0
        rxBuffer = self.SPITransaction(device, txBuffer, cmd, 2)
        res = (rxBuffer & 0xFF00) >> 8
        return res

    def FlashDevice_writeReg(self, device, reg, value=None):
        cmd = bytearray(4)
        txBuffer = [0] * 4
        cmd[0] = reg
        if value is None:
            self.SPITransaction(device, txBuffer, cmd, 1)
        else:
            cmd[1] = value
            self.SPITransaction(device, txBuffer, cmd, 2)

    def FlashDevice_prepareCommand(self, command, address, device):
        txBuffer = bytearray(4)
        txBuffer[0] = command
        txBuffer[1] = (address >> 16) & 0xFF
        txBuffer[2] = (address >> 8) & 0xFF
        txBuffer[3] = address & 0xFF
        return txBuffer

    def FlashDevice_Enter4byteAddMode(self, device):
        self.add4bytemode = True
        self.FlashDevice_writeReg(device, 0x06)  # write enable command
        self.FlashDevice_writeReg(device, 0xC5, 0xf)
        while (1):
            sr = self.FlashDevice_readReg(device, 0xc8)
            if (sr & 0x01) == 1:
                break
        self.FlashDevice_writeReg(device, 0x06)  # write enable command

    def FlashDevice_Exit4byteAddMode(self, device):
        self.add4bytemode = False
        self.FlashDevice_writeReg(device, 0x06)  # write enable command
        self.FlashDevice_writeReg(device, 0xC5, 0x0)
        while (1):
            sr = self.FlashDevice_readReg(device, 0xc8)
            if (sr & 0x01) == 0:
                break
        self.FlashDevice_writeReg(device, 0x06)  # write enable command

    def FlashDevice_writeEnable(self, device):
        self.FlashDevice_writeReg(device, 0x06)

    def FlashDevice_writeDisable(self, device):
        self.FlashDevice_writeReg(device, 0x04)

    def FlashDevice_waitTillReady(self, device):
        while (1):
            sr = self.FlashDevice_readReg(device, 0x05)
            if (sr & 0x01) == 0:
                break

    def FlashDevice_readIdentification(self, device):
        txBuffer = [0] * 32
        cmd = bytearray(4)
        cmd[0] = 0x9F
        # cmd[1] = 0x1
        rxBuffer = self.SPITransaction(device, txBuffer, cmd, 12)
        id = ((rxBuffer[0] & 0xFF000000) >> 24) | ((rxBuffer[0] & 0xFF0000) >> 8) | ((rxBuffer[0] & 0xFF00) << 8)
        return id

    def FlashDevice_readPage(self, device, address, size):
        txBuffer = [0] * 512
        if (size > device.pageSize):
            print("FlashDevice_readPage size > pageSize!")
            return -1
        buffer = self.FlashDevice_prepareCommand(0x03, address, device)
        rxBuffer = self.SPITransaction(device, txBuffer, buffer, size + 4)
        return rxBuffer

    """
    def FlashDevice_read(self,device,address,size):
        page_size = 0
        rxBuffer=[]
        #rxBuffer=bytearray(size+4)
        page_offset = address & (device.pageSize - 1)
        #/* do all the bytes fit onto one page? */
        if (page_offset + size <= device.pageSize):
            rxBuffer=self.FlashDevice_readPage(device, address, size)
            return rxBuffer
        else:
            bytecount=0
            #/* the size of data remaining on the first page */
            page_size = device.pageSize - page_offset
            bytecount=bytecount+page_size
            rxbuff1=self.FlashDevice_readPage(device, address, page_size)
            #for k in range(0,bytecount):
            rxBuffer=rxbuff1
            #/* write everything in nor->page_size chunks */
            for i in range(page_size,size,page_size):
                page_size = size - i
                if (page_size > device.pageSize):
                    page_size = device.pageSize

                rxbuff2=self.FlashDevice_readPage(device, address + i, page_size)
                rxBuffer=rxBuffer+rxbuff2
            return rxBuffer
    """

    def FlashDevice_readsector(self, device, address):
        rxbuffer = []
        page_size = device.pageSize
        num_of_pages = device.sectorSize // page_size
        for i in range(0, num_of_pages):
            rxbuff = self.FlashDevice_readPage(device, address + i * page_size, page_size)
            rxbuffer = rxbuffer + rxbuff
        return rxbuffer

    def FlashDevice_eraseSector(self, device, address):
        self.FlashDevice_writeEnable(device)
        self.FlashDevice_waitTillReady(device)
        txBuffer = [0] * 4
        buff = self.FlashDevice_prepareCommand(0xD8, address, device)
        if device.slaveID != 0 and address >= 0x01000000:
            self.FlashDevice_Enter4byteAddMode(device)
            self.SPITransaction(device, txBuffer, buff, 4)
            self.FlashDevice_Exit4byteAddMode(device)
        else:
            self.SPITransaction(device, txBuffer, buff, 4)
        self.FlashDevice_waitTillReady(device)

    def FlashDevice_erase(self, device, address, size):
        stop = address + size
        while (1):
            self.FlashDevice_eraseSector(device, address)
            address += device.sectorSize
            if address >= stop:
                break
        self.FlashDevice_writeDisable(device)

    def FlashDevice_chiperase(self, device):
        self.FlashDevice_writeEnable(device)
        self.FlashDevice_waitTillReady(device)
        self.FlashDevice_writeReg(device, 0xC7)
        self.FlashDevice_waitTillReady(device)

    def FlashDevice_writePage(self, device, address, size, buffer):
        if (size > device.pageSize):
            print("FlashDevice_writePage size > pageSize!")
            return -1
        buff = self.FlashDevice_prepareCommand(0x02, address, device)
        self.FlashDevice_writeEnable(device)
        rxBuffer = self.SPITransaction(device, buffer, buff, size + 4)
        self.FlashDevice_waitTillReady(device)

    """
    def FlashDevice_write(self,device,address,size,buffer):
        page_size = 0
        page_offset = address & (device.pageSize - 1)
        #/* do all the bytes fit onto one page? */
        if (page_offset + size <= device.pageSize):
            self.FlashDevice_writePage(device, address, size, buffer)
        else:
            bytecount=0
            newbuffer=bytearray(size)
            #/* the size of data remaining on the first page */
            page_size = device.pageSize - page_offset
            self.FlashDevice_writePage(device, address, page_size, buffer)
            #self.FlashDevice_waitTillReady(device)
            bytecount = page_size
            for k in range (0,size-bytecount):
                newbuffer[k]=buffer[k+bytecount]
            #/* write everything in nor->page_size chunks */
            for i in range(page_size,size,page_size):
                page_size = size - i
                if (page_size > device.pageSize):
                    page_size = device.pageSize
                self.FlashDevice_writePage(device, address + i, page_size, newbuffer)
                #self.FlashDevice_waitTillReady(device)
                bytecount=bytecount+page_size
                for k in range (0,size-bytecount):
                    newbuffer[k]=buffer[k+bytecount]
    """

    def FlashDevice_writesector(self, device, address, buffer):
        page_size = device.pageSize
        page_offset = address & (device.pageSize - 1)

        num_of_pages = device.sectorSize // page_size
        for i in range(0, num_of_pages):
            self.FlashDevice_writePage(device, address + i * page_size, page_size,
                                       buffer[i * page_size // 4:i * page_size // 4 + page_size // 4])

    # ########## BITSTREAM MANAGE METHODS SECTION ####################################

    def loadBitstream(self, filename, sectorSize):
        print ("Open Bistream file %s" % (filename))
        with open(filename, "rb") as f:
            dump = bytearray(f.read())
        bitstreamSize = len(dump)

        sc = int(bitstreamSize // sectorSize)
        if (sc * sectorSize) != bitstreamSize:
            sc = sc + 1
        print("Loading %s (%d bytes) = %d * %d bytes sectors" % (filename, bitstreamSize, sc, sectorSize))
        s = int(sc * sectorSize)
        tmp = bytearray(s)
        for i in range(0, bitstreamSize):
            tmp[i] = dump[i]

        for i in range(0, s - bitstreamSize):
            tmp[i + bitstreamSize] = 0xff

        return tmp, bitstreamSize, s

    def saveBitstream(self, filename, memblock, bitstreamSize):
        f = open(filename, "wb")
        print ("Writing %d bytes to %s" % (bitstreamSize, filename))

        l = len(memblock)
        data = bytearray(l * 4)
        print ("lenght of array to be written: %d, in byte %d" % (l, l * 4))
        bytecount = 0
        for i in range(0, l):
            data[bytecount + 0] = memblock[i] & 0xff
            data[bytecount + 1] = (memblock[i] & 0xff00) >> 8
            data[bytecount + 2] = (memblock[i] & 0xff0000) >> 16
            data[bytecount + 3] = (memblock[i] & 0xff000000) >> 24
            bytecount += 4
        f.write(data[0:bitstreamSize])
        f.close()

    def firmwareProgram(self, flashdeviceindedx, bitstreamFilename, address, dumpFilename = None, erase_all=False,
                        erase_size=None, add_len=False):
        device = FlashDevices[flashdeviceindedx]
        self.spi_mux_selection(device.slaveID)
        sectorSize = device.sectorSize
        sectorSize_w = sectorSize // 4
        sectorOffset = address // sectorSize

        memblock1, bitstreamSize, size = self.loadBitstream(bitstreamFilename, sectorSize)
        if add_len is True:
            print("Prepending bitsream size in flash writing")
            lght = bytearray(4)
            lght[0] = (size & 0xff000000) >> 24
            lght[1] = (size & 0xff0000) >> 16
            lght[2] = (size & 0xff00) >> 8
            lght[3] = (size & 0xff)
            memblock = lght + memblock1
            size = size + 4
        else:
            memblock = memblock1

        sector_num = (size // sectorSize)
        if erase_size != None:
            sector_erase_num = (erase_size//sectorSize)
        else:
            sector_erase_num = sector_num
        end_sector_offset = sector_num + sectorOffset

        # Read bitfile and cast as a list of unsigned integers
        formatted_bitstream = list(struct.unpack_from('I' * (len(memblock) // 4), memblock))

        bufferD = []
        remaining = size

        i = sectorOffset
        j = 0
        ec = 0

        if erase_all is False:
            print ("Starting Erase from sector %d" % sector_num)
            print("--- ERASING ------------------------------------------------------------------------------------")
            sect = sector_num
            while True:
                print("Sector %03d @ %08X: Erasing" % (sect, sect * sectorSize))
                self.FlashDevice_erase(device, sect * sectorSize, sectorSize)
                sect -= 1
                if sect == 0:
                    break
        else:
            print("Starting Chip Erase ")
            print("--- ERASING ------------------------------------------------------------------------------------")
            self.FlashDevice_chiperase(device)

        print("Starting programming from sector %d" % (sectorOffset))
        print("--- PROGRAMMING ------------------------------------------------------------------------------------")
        sect = 0
        upper_flash = False
        while True:
            off = j * sectorSize
            print("Sector %03d @ %08X - bitstream offset %08X: " % (i, i * sectorSize, off))
            # print "E ",
            # self.FlashDevice_erase(device, i * sectorSize, sectorSize)
            c = 0
            # for k in range (0,sectorSize):
            #    bufferO[k]=memblock[k+off]
            if upper_flash is False and (i * sectorSize) >= 0x1000000:
                upper_flash = True
                self.FlashDevice_Enter4byteAddMode(device)
            print("W ",)
            b = formatted_bitstream[(j * sectorSize_w):((j * sectorSize_w) + sectorSize_w)]
            self.FlashDevice_writesector(device, i * sectorSize, b)
            print("V")
            bufferI = self.FlashDevice_readsector(device, i * sectorSize)
            # bufferI=self.FlashDevice_read(device, i * sectorSize, sectorSize)
            bufferD = bufferD + bufferI
            # for k in range (0,sectorSize):
            #    bufferD[k+off]=bufferI[k]
            c = 0
            # formatted_data=list(struct.unpack_from('I' * (sectorSize / 4), bufferO))
            for k in range(0, sectorSize // 4):
                if b[k] != bufferI[k]:
                    c += 1
                    print("Error detected in verify @ offset %x: expected %x, read %x" % (k, b[k], bufferI[k]))
                    break
            if c != 0:
                retry = 2
                counterr = 0
                while retry > 0:
                    print("Error detected, retring to write sector")
                    print("Sector %03d @ %08X: Erasing" % (i, i * sectorSize))
                    self.FlashDevice_erase(device, i * sectorSize, sectorSize)
                    print("W ",)
                    # b=formatted_bitstream[(j * sectorSize_w):((j * sectorSize_w) +sectorSize_w)]
                    self.FlashDevice_writesector(device, i * sectorSize, b)
                    print("V")
                    bufferI = self.FlashDevice_readsector(device, i * sectorSize)
                    # bufferI=self.FlashDevice_read(device, i * sectorSize, sectorSize)
                    bufferD = bufferD + bufferI
                    counterr = 0
                    for k in range(0, sectorSize // 4):
                        if b[k] != bufferI[k]:
                            counterr += 1
                            print("Error detected in verify @ offset %x: expected %x, read %x" % (
                                k, formatted_bitstream[(j * sectorSize_w) + k], bufferI[k]))
                            retry -= 1
                            break
                    if counterr == 0:
                        break
                if counterr != 0 and retry == 0:
                    print("Impossible to write bitstream in flash device %d" % flashdeviceindedx)
                    exit()
            ec += c
            j += 1
            i += 1
            sect += 1
            if sect == sector_num:
                break

        print("----------------------------------------------------------------------------------------------------")
        if self.add4bytemode is True:
            upper_flash = False
            self.FlashDevice_Exit4byteAddMode(device)
        if dumpFilename is not None:
            self.saveBitstream(dumpFilename, bufferD, bitstreamSize)
        return ec

    """
    def firmwareVerify(self,flashdeviceindedx,bitstreamFilename,address,dumpFilename=None):
        device = FlashDevices[flashdeviceindedx]
        self.spi_mux_selection(device.slaveID)
        sectorSize=device.sectorSize
        sectorOffset      = address/sectorSize
        memblock,bitstreamSize,size = self.loadBitstream(bitstreamFilename, sectorSize)
        bufferO = bytearray(sectorSize)
        bufferD = []#bytearray(size)
        remaining = size
        i  = sectorOffset
        j  = 0
        ec = 0
        print("Starting verify from sector %d" %sectorOffset)
        print("--- VERIFYING ------------------------------------------------------------------------------------\n")
        while (remaining > 0):
            off = j * sectorSize
            print("Sector %03d @ %08X - bitstream offset %08X: " %(i, i * sectorSize, off))
            c = 0
            for k in range(0,sectorSize):
                bufferO[k]=memblock[k+off]
            print"V",
            bufferI=self.FlashDevice_read_sector(device, i * sectorSize, sectorSize)
            bufferD=bufferD+bufferI
            formatted_data=list(struct.unpack_from('I' * (sectorSize / 4), bufferO))
            for k in range (0, sectorSize/4):
                if formatted_data[k] != bufferI[k]:
                    c+=1
                    print("Error detected in verify @ offset %x: expected %x, read %x" %(k,formatted_data[k]),bufferI[k])
            ec+=c

            remaining -= sectorSize
            j+=1
            i+=1

        print("----------------------------------------------------------------------------------------------------\n");
        errorCount = ec

        if (dumpFilename!= None):
            self.saveBitstream(dumpFilename, bufferD, bitstreamSize)
        return errorCount
    """

    def firmwareRead(self, flashdeviceindedx, address, size, dumpFilename):
        device = FlashDevices[flashdeviceindedx]
        self.spi_mux_selection(device.slaveID)
        sectorSize = device.sectorSize
        sectorOffset = address // device.sectorSize
        remaining = 0
        bitstream_sectorsize = size // sectorSize
        bitstream_sectorsize += 1
        bufferD = []  # bytearray(bitstream_sectorsize*sectorSize)
        # remaining = size
        remaining = bitstream_sectorsize * sectorSize
        i = sectorOffset
        j = 0
        ec = 0
        upper_flash = False
        print("Starting Reading from sector %d" % sectorOffset)
        print("--- READING ------------------------------------------------------------------------------------")
        while (remaining > 0):
            off = j * sectorSize
            print("Sector %03d @ %08X - bitstream offset %08X: R" % (i, i * sectorSize, off))
            c = 0
            if upper_flash == False and address >= 0x1000000:
                upper_flash = True
                self.FlashDevice_Enter4byteAddMode(device)
            bufferI = self.FlashDevice_readsector(device, i * sectorSize)
            # for k in range (0,sectorSize):
            #    bufferD[k+off]=bufferI[k]
            bufferD = bufferD + bufferI
            remaining -= sectorSize
            j += 1
            i += 1
        print("----------------------------------------------------------------------------------------------------")
        if self.add4bytemode is True:
            self.FlashDevice_Exit4byteAddMode(device)
        if dumpFilename is not None:
            self.saveBitstream(dumpFilename, bufferD, size)

    def DeviceGetInfo(self, flashdeviceindedx):
        device = FlashDevices[flashdeviceindedx]
        return device

    def DeviceGetID(self, flashdeviceindedx):
        device = FlashDevices[flashdeviceindedx]
        self.spi_mux_selection(device.slaveID)
        id = self.FlashDevice_readIdentification(device)
        return id

    def DeviceErase(self, flashdeviceindedx, address, size):
        device = FlashDevices[flashdeviceindedx]
        self.spi_mux_selection(device.slaveID)
        self.FlashDevice_erase(device, address, size)

    def DeviceEraseChip(self, flashdeviceindedx):
        device = FlashDevices[flashdeviceindedx]
        self.spi_mux_selection(device.slaveID)
        self.FlashDevice_chiperase(device)

    def DeviceWrite(self, flashdeviceindedx, address, txbuff, size):
        device = FlashDevices[flashdeviceindedx]
        self.spi_mux_selection(device.slaveID)
        data_size = len(txbuff)
        sectorSize = 64 * 1024
        sectorOffset = address // sectorSize
        sc = data_size // sectorSize
        if (sc * sectorSize) != data_size:
            sc = sc + 1
        s = sc * sectorSize
        tmp = bytearray(s)
        for i in range(0, data_size):
            tmp[i] = txbuff[i]

        for i in range(0, s - data_size):
            tmp[i + data_size] = 0xff

        formatted_bitstream = list(struct.unpack_from('I' * (len(tmp) // 4), tmp))
        i = sectorOffset
        j = 0
        sector_num = sc
        sect = 0
        while True:
            self.FlashDevice_writesector(device, i * sectorSize,
                                         formatted_bitstream[j * sectorSize // 4:(j * sectorSize // 4 + sectorSize // 4)])
            i = i + 1
            j += 1
            sect += 1
            if sect == sector_num:
                break

