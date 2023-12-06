__author__ = "Cristian Albanese"

spi_if_ba = 0x00050000

address_offset = 0x00
write_data_offset = 0x04
read_data_offset = 0x08
chip_select_offset = 0x0C
sclk_offset = 0x10
cmd_offset = 0x14


class MANAGEMENT_SPI:
    def __init__(self, board, rmp, pll_cs):
        self.spi_if_base_address = spi_if_ba
        self.pll_cs = pll_cs
        self.board = board
        self.rmp = rmp

    def spi_access(self, op, add, dat):
        """!@brief Access an SPI connected device

        This function provide access to an SPI connected device.

        @param op  -- str -- "wr" or "rd"
        @param idx -- int -- This parameter selects the active chip select for the current transaction.
                   When more then one SPI device share clock and data line, it is necessary to
                   specify which device should be addressed.
        @param add -- int -- SPI device address, register offset to be accessed within the SPI device
        @param dat -- int -- Write data for write operations or don't care for read operations

        Returns -- int -- read data for read operations or don't care for write operations
        """
        while True:
            if (self.rmp.rd32(self.spi_if_base_address + cmd_offset) & 0x1) == 0:
                break
        pkt = []
        pkt.append(add)
        pkt.append(dat << 8)
        pkt.append(0x0)
        pkt.append(self.pll_cs)
        pkt.append(0x1)

        self.rmp.wr32(self.spi_if_base_address + address_offset, pkt)

        if op == "wr":
            self.rmp.wr32(self.spi_if_base_address + cmd_offset, 0x01)
        elif op == "rd":
            self.rmp.wr32(self.spi_if_base_address + cmd_offset, 0x03)
        while True:
            if (self.rmp.rd32(self.spi_if_base_address + cmd_offset) & 0x1) == 0:
                break
        return self.rmp.rd32(self.spi_if_base_address + read_data_offset) & 0xFF
