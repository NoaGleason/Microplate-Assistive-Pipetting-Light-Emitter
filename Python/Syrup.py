import tkinter.font as tkFont
import tkinter.ttk as ttk
from operator import attrgetter
from tkinter import *
from tkinter.filedialog import askopenfilename

import serial
from ttkthemes import ThemedTk

import SerialUtils
from CompoundRequest import CompoundRequest

DRY_RUN = False
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


def set_brightness(brightness: int):
    SerialUtils.send_serial_command(panel, "set_brightness", brightness=brightness)


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
        self.scannerMode = IntVar()
        self.scannerMode.set(1)
        self.searchText = StringVar()
        self.searchText.set("")
        self.brightness = IntVar()
        self.brightness.set(50)

        self.done_color = "#C3C3C3"
        self.fail_color = "#FF8888"
        self.search_color = "#FFFFFF"

        self.master = master
        self.master.title("Simple YTE1005 Reader and Updater for Plates v0.1")
        self.master.minsize(500, 500)

        # Set styles
        style = ttk.Style()

        style.configure("TButton", padding=4)
        style.configure("Search.TEntry", border=[6, 0, 6, 0], side="left")
        style.configure("TFrame", border=[10, 10, 10, 10], padding=6)
        style.configure("TLabel", padding=3)

        # create all of the main containers
        top_frame = ttk.Frame(self.master, padding=6)

        # layout all of the main containers
        self.master.grid_rowconfigure(1, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        top_frame.grid(row=0, sticky="ew")

        # Create container for table
        center = ttk.Frame(self.master)
        center.grid(row=1, sticky="nsew")

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

        # Ridiculous workaround thanks to https://stackoverflow.com/a/17639955
        estyle = ttk.Style()
        estyle.element_create("plain.field", "from", "arc")
        estyle.layout("EntryStyle.TEntry",
                      [('Entry.plain.field', {'children': [(
                          'Entry.background', {'children': [(
                              'Entry.padding', {'children': [(
                                  'Entry.textarea', {'sticky': 'nswe'})],
                                  'sticky': 'nswe'})], 'sticky': 'nswe'})],
                          'border': '1', 'sticky': 'nswe'})])

        # create the widgets for the top frame
        self.searchLabel = ttk.Label(top_frame, text="Search: ", takefocus=0)
        self.searchBar = ttk.Entry(top_frame, width="20", style="EntryStyle.TEntry", textvariable=self.searchText)
        self.scannerCheckbutton = ttk.Checkbutton(top_frame, text="Scanner Mode", takefocus=0,
                                                  variable=self.scannerMode, onvalue=1, offvalue=0)
        self.brightnessLabel = ttk.Label(top_frame, text="Brightness: ", takefocus=0)
        self.brightnessSlider = ttk.Scale(top_frame, orient=HORIZONTAL, takefocus=0, from_=0, to=255,
                                          variable=self.brightness, command=self.set_brightness)
        self.backButton = ttk.Button(top_frame, text="Previous plate", command=self.previous_plate, takefocus=0)
        self.nextButton = ttk.Button(top_frame, text="Plate complete", command=self.next_plate, takefocus=0)

        # layout the widgets in the top frame
        top_frame.grid_columnconfigure(2, weight=3)
        self.searchLabel.grid(row=0, column=1, sticky="e")
        self.searchBar.grid(row=0, column=2, sticky="w")
        self.brightnessLabel.grid(row=0, column=3, sticky="e")
        self.brightnessSlider.grid(row=0, column=4, sticky="w")
        self.scannerCheckbutton.grid(row=0, column=5)
        self.backButton.grid(row=0, column=6)
        self.nextButton.grid(row=0, column=7)
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

        self.set_brightness("50")

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
        barcode = self.searchText.get()
        # If an even code is scanned, use the corresponding odd code instead
        try:
            bar_num = int(barcode[2:])
            if bar_num % 2 == 0:
                barcode = "{}{:06}".format(barcode[:2], bar_num - 1)
        except ValueError as e:
            # If int formatting fails
            pass
        # Fancy oneline to find the first element of the array that matches the condition, or self.currentPlatePosition
        # if no match is found.
        prev_plate_pos = self.currentPlatePosition
        self.currentPlatePosition = next((i for i, v in enumerate(self.compoundRequests) if v.location.barcode ==
                                          barcode), self.currentPlatePosition)
        if self.currentPlatePosition == prev_plate_pos:
            ttk.Style().configure("EntryStyle.TEntry", background=self.fail_color)
            ttk.Style().configure("EntryStyle.TEntry", fieldbackground=self.fail_color)
            if self.scannerMode.get():
                self.searchText.set("")
        else:
            ttk.Style().configure("EntryStyle.TEntry", background=self.search_color)
            ttk.Style().configure("EntryStyle.TEntry", fieldbackground=self.search_color)
            if self.scannerMode.get():
                self.searchText.set("")
            else:
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

    def set_brightness(self, brightness: str):
        set_brightness(max(int(float(brightness)), 1))
        update_panel()

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
            self.tree.yview_moveto((self.currentPlatePosition - 1) / len(self.compoundRequests))
        update_panel()


if __name__ == '__main__':
    mainWindow = ThemedTk(theme="arc")
    syrupGUIInstance = SyrupGUI(mainWindow)
    mainWindow.protocol("WM_DELETE_WINDOW", on_closing)
    mainWindow.mainloop()
