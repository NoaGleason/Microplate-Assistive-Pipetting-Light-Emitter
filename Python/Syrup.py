# TODO come up with a dumb backronym for SYRUP
from operator import attrgetter
from tkinter import *
import tkinter.font as tkFont
import tkinter.ttk as ttk
from tkinter.filedialog import askopenfilename
from sys import platform

import serial

import SerialUtils
from CompoundRequest import CompoundRequest

DRY_RUN = True
COLUMNS = ["Request ID", "Available", "Scripps Barcode", "State", "Volume", "Concentration", "Weight", "Solvation",
           "Freezer", "Shelf", "Rack", "Section", "Subsection", "Plate Barcode", "Well"]

with open("config.txt", "r") as file:
    serialPorts = file.readlines()
    COMPortOne = serialPorts[0].strip()
    if DRY_RUN:
        panel = None
        print("Setting up panel on port " + COMPortOne)
    else:
        panel = serial.Serial(COMPortOne, baudrate=38400, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
        print("Serial connected")


def light_well(well_name):
    SerialUtils.send_serial_command(panel, "well_on", well_name=well_name)


def update_panel():
    SerialUtils.update_panels([panel])


def clear_panel():
    SerialUtils.clear_panels([panel])


def on_closing():
    SerialUtils.close_connection([panel])
    print("Closing serial ports!")
    mainWindow.destroy()
    exit()


class SyrupGUI(Frame):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.currentPlatePosition = 0
        self.fileName = ""
        self.compoundRequests = []
        self.compoundRequestIds = {}

        self.done_color = "#C3C3C3"
        self.fail_color = "#FFAAAA"
        self.search_color = "#FFFFFF"

        self.master = master
        self.master.title("SYRUP Beta Edition")
        # self.master.maxsize(500, 500)
        self.master.minsize(500, 500)

        # create all of the main containers
        top_frame = Frame(self.master, bg='grey', width=450, height=50, pady=3)

        # layout all of the main containers
        self.master.grid_rowconfigure(1, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        top_frame.grid(row=0, sticky="ew")

        # Create container for table
        center = Frame(self.master)
        center.grid(row=1, sticky="nsew")

        # Weird workaround for https://core.tcl-lang.org/tk/tktview?name=509cafafae
        style = ttk.Style()
        if platform == "win32" or platform == "cygwin":
            style.theme_use("winnative")

        def fixed_map(option):
            # Returns the style map for 'option' with any styles starting with
            # ("!disabled", "!selected", ...) filtered out

            # style.map() returns an empty list for missing options, so this should
            # be future-safe
            return [elm for elm in style.map("Treeview", query_opt=option)
                    if elm[:2] != ("!disabled", "!selected")]

        style.map("Treeview",
                  foreground=fixed_map("foreground"),
                  background=fixed_map("background"))

        self.tree = ttk.Treeview(columns=COLUMNS, show="headings", style="Treeview")
        vsb = ttk.Scrollbar(orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(column=0, row=0, sticky='nsew', in_=center)
        vsb.grid(column=1, row=0, sticky='ns', in_=center)
        hsb.grid(column=0, row=1, sticky='ew', in_=center)

        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=1)

        for column in COLUMNS:
            self.tree.heading(column, text=column.title())
            self.tree.column(column, width=tkFont.Font().measure(column.title()))

        self.tree.tag_configure("done", background=self.done_color)

        # create the widgets for the top frame
        self.searchBar = Entry(top_frame, width="20", text="Barcode")
        self.backButton = Button(top_frame, text="Previous plate", command=self.previous_plate)
        self.nextButton = Button(top_frame, text="Next plate", command=self.next_plate)

        # layout the widgets in the top frame
        top_frame.grid_columnconfigure(2, weight=3)
        self.searchBar.grid(row=0, column=1)
        self.backButton.grid(row=0, column=3)
        self.nextButton.grid(row=0, column=4)
        self.open_file()

        # create key shortcuts
        self.searchBar.bind("<Return>", lambda e: self.goto_barcode())
        self.searchBar.bind("<Down>", lambda e: self.tree.focus_set())
        self.tree.bind("<Left>", lambda e: self.previous_plate())
        self.tree.bind("<Right>", lambda e: self.next_plate())
        self.tree.bind("<Up>", lambda e: self.previous_plate())
        self.tree.bind("<Down>", lambda e: self.next_plate())
        self.tree.bind("<Button-1>", self.goto_selection)
        self.tree.focus_force()

    def next_plate(self):
        old_plate = self.compoundRequests[self.currentPlatePosition].location
        while self.currentPlatePosition < len(self.compoundRequests) - 1 and \
                self.compoundRequests[self.currentPlatePosition].location.same_plate(old_plate):
            self.tree.item(self.compoundRequestIds[self.compoundRequests[self.currentPlatePosition]], tags=("done",))
            self.currentPlatePosition += 1
        self.parse_commands()

    def previous_plate(self):
        if self.currentPlatePosition > 0:
            self.currentPlatePosition -= 1
            self._seek_back_plate()
        self.parse_commands()

    def goto_barcode(self):
        barcode = self.searchBar.get()
        # Fancy oneline to find the first element of the array that matches the condition, or self.currentPlatePosition
        # if no match is found.
        prev_plate_pos = self.currentPlatePosition
        self.currentPlatePosition = next((i for i, v in enumerate(self.compoundRequests) if v.location.barcode ==
                                          barcode), self.currentPlatePosition)
        if self.currentPlatePosition == prev_plate_pos:
            self.searchBar.config(bg=self.fail_color)
        else:
            self.searchBar.config(bg=self.search_color)
            self.tree.focus_set()
            self.parse_commands()

    def goto_selection(self, e):
        self.currentPlatePosition = self.tree.index(self.tree.identify("item", e.x, e.y))
        self._seek_back_plate()
        self.parse_commands(scroll=False)
        return "break"

    def _seek_back_plate(self):
        plate = self.compoundRequests[self.currentPlatePosition].location
        while self.currentPlatePosition > 0 and \
                self.compoundRequests[self.currentPlatePosition - 1].location.same_plate(plate):
            self.currentPlatePosition -= 1

    def open_file(self):
        self.fileName = askopenfilename()  # show an open file dialog box and return the path to the selected file
        self.compoundRequests = []
        self.currentPlatePosition = 0
        with open(self.fileName, "r") as csv_file:
            # Clear header
            csv_file.readline()
            for line in csv_file:
                self.compoundRequests.append(CompoundRequest(line.strip()))

        self.compoundRequests.sort(key=attrgetter('location'))

        for request in self.compoundRequests:
            self.compoundRequestIds[request] = self.tree.insert("", "end", values=request.get_row())
            # adjust column's width if necessary to fit each value
            for ix, val in enumerate(request.get_row()):
                col_w = tkFont.Font().measure(str(val))
                if self.tree.column(COLUMNS[ix], width=None) < col_w:
                    self.tree.column(COLUMNS[ix], width=col_w)
        self.parse_commands()

    def parse_commands(self, scroll=True):
        # get the current source and destination wells, then send them to the send_serial_command for LEDs to be lit
        clear_panel()
        index = 0
        plate = self.compoundRequests[self.currentPlatePosition].location
        selections = []
        while self.currentPlatePosition + index < len(self.compoundRequests) and \
                self.compoundRequests[self.currentPlatePosition + index].location.same_plate(plate):
            selections.append(self.compoundRequestIds[self.compoundRequests[self.currentPlatePosition + index]])
            light_well(self.compoundRequests[self.currentPlatePosition + index].location.well)
            index += 1
        self.tree.selection_set(selections)
        if scroll:
            self.tree.yview_moveto((self.currentPlatePosition-1)/len(self.compoundRequests))
        update_panel()


if __name__ == '__main__':
    mainWindow = Tk()
    syrupGUIInstance = SyrupGUI(mainWindow)
    mainWindow.protocol("WM_DELETE_WINDOW", on_closing)
    mainWindow.mainloop()

