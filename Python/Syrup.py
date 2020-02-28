# TODO come up with a dumb backronym for SYRUP
from tkinter import *

import pandas as pd
import serial

import SerialUtils

DRY_RUN = False

with open("config.txt", "r") as file:
    serialPorts = file.readlines()
    COMPortOne = serialPorts[0].strip()
    if DRY_RUN:
        panel = None
        print("Setting up panel on port " + COMPortOne)
    else:
        panel = serial.Serial(COMPortOne, '38400', parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)


def light_well(well_name):
    SerialUtils.send_serial_command(panel, "well_on", well_name=well_name)


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
        self.plateData = pd.DataFrame()
        self.currentPlatePosition = 0
        self.fileName = ""
        self.pt = None

        self.master = master
        self.master.title("SYRUP Beta Edition")
        self.master.maxsize(500, 500)
        self.master.minsize(500, 500)

        c = Canvas(self.master)
        c.configure(yscrollincrement='10c')

        # create all of the main containers
        top_frame = Frame(self.master, bg='grey', width=450, height=50, pady=3)

        # layout all of the main containers
        self.master.grid_rowconfigure(1, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        top_frame.grid(row=0, sticky="ew")

        # Create container for table
        self.center = Frame(self.master, bg='gray2', width=450, height=500, pady=3)
        self.center.grid(row=1, sticky="nsew")

        # create the widgets for the top frame
        self.fileButton = Button(top_frame, text="Select location file", command=self.open_file)
        self.backButton = Button(top_frame, text="Previous plate", command=self.previous_well)
        self.nextButton = Button(top_frame, text="Next plate", command=self.next_well)

        # layout the widgets in the top frame
        self.fileButton.grid(row=0, column=1)
        top_frame.grid_columnconfigure(2, weight=3)
        self.backButton.grid(row=0, column=3)
        self.nextButton.grid(row=0, column=4)



if __name__ == '__main__':
    mainWindow = Tk()
    syrupGUIInstance = SyrupGUI(mainWindow)
    mainWindow.protocol("WM_DELETE_WINDOW", on_closing)
    mainWindow.mainloop()

