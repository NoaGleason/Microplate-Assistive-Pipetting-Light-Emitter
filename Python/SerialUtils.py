from typing import List

import serial

COMMAND_CODES = {"clear": 0x00, "well_on": 0x01, "well_off": 0x02, "column_on": 0x03, "column_off": 0x04,
                 "row_on": 0x05, "row_off": 0x06, "update": 0x07, "set_brightness": 0x08}


def write_or_print(bytestring: bytes, serial_connection: serial.Serial):
    if serial_connection:
        try:
            serial_connection.write(bytestring)
            recv = serial_connection.read(2)
        except serial.SerialException:
            return False
        if recv != bytestring:
            return False
    else:
        print("Sending bytestring {:08b} {:08b}".format(bytestring[0], bytestring[1]))
    return True


def get_row_name_from_well(well: str):
    if well is None:
        return None
    row_name = well[0:1]  # for row
    return row_name


def get_column_number_from_well(well: str):
    if well is None:
        return None
    column_number = well[1:3]
    return column_number


def send_serial_command(serial_connection: serial.Serial, command: str, well_name: str = None,
                        row: str = None, column: str = None, brightness: int = None):
    """
    Send a serial command to the given port.
    :param serial_connection: The connection to send a command to. If None, prints out the command instead.
    :param command: The command to give. Must be a key of COMMAND_CODES.
    :param well_name: The name of the well, which will be used to extract the row and column. Ignored if row and column
    are not None.
    :param row: The row name to give to the command. Can be none to extract from well_name.
    :param column: The column number to give to the command. Can be none to extract from well_name.
    :param brightness: The brightness to give to the command. If not none, assumes that the given command is brightness.
    :return:
    """
    if brightness is not None:
        serial_string = make_brightness_bitstring(brightness, command)
    else:
        if not row:
            row = get_row_name_from_well(well_name)
        if not column:
            column = get_column_number_from_well(well_name)
        serial_string = make_positional_bitstring(row, int(column), command)
    return write_or_print(serial_string, serial_connection)


def clear_panels(panels: List[serial.Serial]):
    results = []
    serial_string = make_positional_bitstring("a", 1, "clear")
    for serial_connection in panels:
        results.append(write_or_print(serial_string, serial_connection))
    return results


def update_panels(panels: List[serial.Serial]):
    results = []
    serial_string = make_positional_bitstring("a", 1, "update")
    for serial_connection in panels:
        results.append(write_or_print(serial_string, serial_connection))
    return results


def close_connection(panels: List[serial.Serial]):
    clear_panels(panels)
    update_panels(panels)
    for serial_connection in panels:
        if serial_connection is not None:
            serial_connection.close()


def make_brightness_bitstring(brightness: int, command: str):
    if command not in COMMAND_CODES.keys():
        raise ValueError("Invalid command name " + command + "! Must be one of " + str(COMMAND_CODES.keys()) + ".")
    first_byte = COMMAND_CODES.get(command) << 1
    second_byte = brightness
    return bytes([first_byte, second_byte])


def make_positional_bitstring(row: str, column: int, command: str):
    if command not in COMMAND_CODES.keys():
        raise ValueError("Invalid command name " + command + "! Must be one of " + str(COMMAND_CODES.keys()) + ".")
    column -= 1
    row = ord(row.lower()) - 97
    command = COMMAND_CODES.get(command)
    # print("{0:7d} {1:5d} {2:4d}\n{0:07b} {1:05b} {2:04b}".format(command, column, row))
    first_byte = command << 1 | column >> 4
    second_byte = (column & 15) << 4 | row
    # print("{0:08b} {1:08b}".format(first_byte, second_byte))
    return bytes([first_byte, second_byte])
