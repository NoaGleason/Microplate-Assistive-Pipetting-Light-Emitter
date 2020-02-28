from abc import ABC, abstractmethod
from functools import total_ordering

import SerialUtils


def location_factory(colon_delimited: str):
    location_data = colon_delimited.split(":")


class CompoundRequest:

    def __init__(self, csv_row):
        """
        :param csv_row: A line of text in the format Request_id,Available,Barcode,State,Volume,Concentration,Weight,
        Solvation,Location. Location is in the format Freezer:Shelf:CRACK:Section:Plate Barcode:Well
        """
        row_data = csv_row.split(",")
        if len(row_data) != 9:
            raise ValueError("Line {} contains {:d} comma-delimited elements, must be exactly 9!".format(csv_row,
                                                                                                         len(row_data)))
        self.request_id = row_data[0]
        self.available = row_data[1]
        self.barcode = row_data[2]
        self.state = row_data[3]
        self.volume = float(row_data[4])
        self.concentration = float(row_data[5])
        self.weight = float(row_data[6])
        self.solvation = None if row_data[7] == "null" else row_data[7]


@total_ordering
class Location(ABC):

    @abstractmethod
    @property
    def barcode(self):
        pass

    @abstractmethod
    @property
    def well(self):
        pass

    @abstractmethod
    def __str__(self):
        pass

    @staticmethod
    def _is_valid_comparable(other):
        return hasattr(other, "barcode") and hasattr(other, "well")

    def __eq__(self, other):
        return self._is_valid_comparable(other) and other.well == self.well and other.barcode == self.barcode

    def __lt__(self, other):
        if not self._is_valid_comparable(other):
            return NotImplemented
        return (self.barcode, SerialUtils.get_row_name_from_well(self.well),
                SerialUtils.get_column_number_from_well(self.well)) < \
               (other.barcode, SerialUtils.get_row_name_from_well(other.well),
                SerialUtils.get_column_number_from_well(other.well))


class FreezerLocation(Location):

    def __init__(self, freezer, shelf, crack, section, barcode, well):
        self.freezer = freezer
        self.shelf = shelf
        self.crack = crack
        self.section = section
        self._barcode = barcode
        self._well = well

    @property
    def barcode(self):
        return self._barcode

    @property
    def well(self):
        return self._well

    def __str__(self):
        return "{}:{}:{}:{}:{}:{}".format(self.freezer, self.shelf, self.crack, self.section, self.barcode, self.well)
