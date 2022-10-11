'''
master_main.py - An example MicroPython project, using the micropython-modbus 
library. 

This example code is dedicated to the public domain. To the extent possible 
under law, Extel Technologies has waived all copyright and related or 
neighboring rights to "master_main.py". This work is published from: Australia. 

https://creativecommons.org/publicdomain/zero/1.0/
'''

import logging
import machine
import struct

import modbus
import modbus.defines as cst
from modbus import modbus_rtu


LOGGER = logging.getLogger("main")
LOGGER.setLevel(logging.DEBUG)

uart_tx = machine.Pin(16)
uart_rx = machine.Pin(17)

# pin_cts = machine.Pin(machine.Pin.cpu.G9, machine.Pin.OUT)

# def serial_prep(mode):
#     if mode == modbus_rtu.serial_cb_tx_begin:
#         LOGGER.debug("Begin Tx")
#         # SP485E IC needs CTS high to allow transmit
#         pin_cts.value(1)
#     elif mode == modbus_rtu.serial_cb_tx_end:
#         LOGGER.debug("End Tx")
#         # Once Tx is done, switch back to allowing receive
#         pin_cts.value(0)
#     elif mode == modbus_rtu.serial_cb_rx_begin:
#         LOGGER.debug("Begin Rx")
#         # Probably already in Rx mode, but just in case
#         pin_cts.value(0)
#     elif mode == modbus_rtu.serial_cb_rx_end:
#         LOGGER.debug("End Rx")
#     else:
#         raise ValueError("Given 'mode' does not have a defined action")

def main():
    LOGGER.info("Opening UART0")
    uart = machine.UART(
        0, tx=uart_tx, rx=uart_rx,
        baudrate=9600, bits=8, parity=None, stop=1, timeout=2000, timeout_char=100,
    )

    # master = modbus_rtu.RtuMaster(uart, serial_prep_cb=serial_prep)
    master = modbus_rtu.RtuMaster(uart)
    LOGGER.info('Setting verbose')
    master.set_verbose(True)


    LOGGER.info("Reading from register 0x00")
    # 'execute' returns a pair of 16-bit words
    f_word_pair = master.execute(1, cst.READ_INPUT_REGISTERS, 0x00, 2)
    # Re-pack the pair of words into a single byte, then un-pack into a float
    volts = struct.unpack('<f', struct.pack('<h', int(f_word_pair[1])) + struct.pack('<h', int(f_word_pair[0])))[0]
    print(volts)

    # LOGGER.info("Reading from register 0x06")
    # # 'execute' returns a pair of 16-bit words
    # f_word_pair = master.execute(51, cst.READ_INPUT_REGISTERS, 0x06, 2)
    # # Re-pack the pair of words into a single byte, then un-pack into a float
    # amps = struct.unpack('<f', struct.pack('<h', int(f_word_pair[1])) + struct.pack('<h', int(f_word_pair[0])))[0]

    # LOGGER.info("Measured from Line 1:\r\nVolts: {}\r\nAmps: {}".format(volts, amps))

if __name__ == "__main__":
    main()
