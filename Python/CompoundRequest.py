from functools import total_ordering

import SerialUtils


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
        self.location = Location(row_data[8])

    def get_row(self):
        return self.request_id, self.available, self.barcode, self.state, self.volume, self.concentration, self.weight,\
               self.solvation, self.location.freezer, self.location.shelf, self.location.rack, self.location.section, \
               self.location.subsection, self.location.barcode, self.location.well

    def __hash__(self):
        return hash(self.get_row())


@total_ordering
class Location:

    def __init__(self, loc_string: str):
        location_data = loc_string.split(":")
        if len(location_data) == 3:  # e.g. CMG_pulled:MT999957:B04
            self.freezer = location_data[0]
            self.shelf = None
            self.rack = None
            self.section = None
            self.subsection = None
            self.barcode = location_data[1]
            self.well = location_data[2]
        elif len(location_data) == 5:  # e.g. R1:S1:REFRAME_0001:BOX5:D8
            self.freezer = location_data[0]
            self.shelf = location_data[1]
            self.rack = location_data[2]
            self.section = location_data[3]
            self.subsection = None
            self.barcode = None
            self.well = location_data[4]
        elif len(location_data) == 6:  # e.g. F18:S5:CRACK_0578:E:MT100073:H02
            self.freezer = location_data[0]
            self.shelf = location_data[1]
            self.rack = location_data[2]
            self.section = location_data[3]
            self.subsection = None
            self.barcode = location_data[4]
            self.well = location_data[5]
        elif len(location_data) == 7:  # e.g. F100:S5:MRACK_0024:D1:A:MT001653:A032
            self.freezer = location_data[0]
            self.shelf = location_data[1]
            self.rack = location_data[2]
            self.section = location_data[3]
            self.subsection = location_data[4]
            self.barcode = location_data[5]
            self.well = location_data[6]
        else:
            raise ValueError("Location {} contains {:d} comma-delimited elements, must be 3, 5, 6, or 7!"
                             .format(loc_string, len(location_data)))

    def same_plate(self, other):
        return (self.freezer, self.shelf, self.rack, self.section, self.subsection, self.barcode) == \
               (other.freezer, other.shelf, other.rack, other.section, other.subsection, other.barcode)

    def __str__(self):
        out_str = ""
        out_str = self._conditional_append(out_str, self.freezer, ":")
        out_str = self._conditional_append(out_str, self.shelf, ":")
        out_str = self._conditional_append(out_str, self.rack, ":")
        out_str = self._conditional_append(out_str, self.section, ":")
        out_str = self._conditional_append(out_str, self.subsection, ":")
        out_str = self._conditional_append(out_str, self.barcode, ":")
        out_str = self._conditional_append(out_str, self.well, ":")
        return out_str[:-1]

    @staticmethod
    def _conditional_append(base, to_add, delimiter):
        if to_add is not None:
            return base + to_add + delimiter

    def __members(self):
        return (self.freezer, self.shelf, self.rack, self.section, self.subsection, self.barcode,
                SerialUtils.get_row_name_from_well(self.well), SerialUtils.get_column_number_from_well(self.well))

    def __hash__(self):
        return hash(self.__members())

    def __eq__(self, other):
        return type(other) is type(self) and self.__members() == other.__members()

    def __lt__(self, other):
        if type(other) is not type(self):
            return NotImplemented
        self_members = self.__members()
        other_members = other.__members()

        # Hand-write a tuple equality check since the builtin one doesn't handle None how we'd like
        for i in range(len(self_members)):
            if self_members[i] is None and other_members[i] is None:
                continue
            elif self_members[i] is None:
                return True
            elif other_members[i] is None:
                return False

            if self_members[i] != other_members[i]:
                return self_members[i] < other_members[i]
        return False
