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


class DTS6619:
    DATA_ADDRESS_MAP = {
        'line_a_voltage': 0x00,
        'line_b_voltage': 0x02,
        'line_c_voltage': 0x04,
        'line_a_current': 0x08,
        'line_b_current': 0x0A,
        'line_c_current': 0x0C,
        'total_active_power': 0x10,
        'line_a_active_power': 0x12,
        'line_b_active_power': 0x14,
        'line_c_active_power': 0x16,
        'total_reactive_power': 0x18,
        'line_a_reactive_power': 0x1A,
        'line_b_reactive_power': 0x1C,
        'line_c_reactive_power': 0x1E,
        'line_a_power_factor': 0x2A,
        'line_b_power_factor': 0x2C,
        'line_c_power_factor': 0x2E,
        'frequency': 0x36,
        'total_active_power': 0x100,
        'total_reactive_power': 0x400,
    }

    def __init__(self, uart_data, device_address, verbose=False):
        readable_uart = '_'.join(map(str, uart_data))
        self._logger = logging.getLogger(f"modbus_rtu.uart_{readable_uart}.d{device_address}")

        self._address = device_address
        
        uart_id = uart_data[0]
        uart_tx = machine.Pin(uart_data[1])
        uart_rx = machine.Pin(uart_data[2]) 

        self._uart = machine.UART(
            uart_id, tx=uart_tx, rx=uart_rx,
            baudrate=9600, bits=8, parity=uart_data[3], stop=1,
            timeout=1000, timeout_char=100,
        )
        self._modbus = modbus_rtu.RtuMaster(self._uart)
        if verbose:
            self._logger.setLevel(logging.DEBUG)
            self._logger.info('Setting verbose')
            self._modbus.set_verbose(True)
        else:
            self._logger.setLevel(logging.INFO)

    def execute(self, *args, **kwargs):
        return self._modbus.execute(*args, **kwargs)
    
    def decode_data(self, word_pair):
        return struct.unpack('<f', struct.pack('<h', int(word_pair[1])) + struct.pack('<h', int(word_pair[0])))[0]

    def read(self, register_name):
        if not register_name in self.DATA_ADDRESS_MAP:
            raise ValueError(f'Unknown register name: {register_name}')

        register = self.DATA_ADDRESS_MAP[register_name]
        self._logger.info(f"Reading from register {register}")
        f_word_pair = self._modbus.execute(self._address, cst.READ_INPUT_REGISTERS, register, 2)
        return self.decode_data(f_word_pair)

