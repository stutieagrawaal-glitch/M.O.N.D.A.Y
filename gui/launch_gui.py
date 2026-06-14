import tkinter as tk

from core.monday import Monday
from gui.control_panel import MondayControlPanel


def main():

    monday = Monday()

    root = tk.Tk()

    MondayControlPanel(
        root=root,
        monday=monday
    )

    root.mainloop()


if __name__ == "__main__":
    main()