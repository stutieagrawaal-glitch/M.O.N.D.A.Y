
import tkinter as tk
from tkinter import ttk
from sensors.simulator import SensorSimulator
from core.monday import Monday

class MondayControlPanel:

    def __init__(self, root, monday):

        self.root = root
        self.root.title("MONDAY Control Center")

        self.monday = monday
        self.simulator = SensorSimulator()

        self.build_ui()

        self.auto_refresh()

    def build_ui(self):

        control = ttk.Frame(self.root, padding=10)
        control.pack(fill="x")

        ttk.Label(control, text="Location").grid(row=0, column=0, sticky="w")

        self.location = tk.StringVar(value="kitchen")

        ttk.Combobox(
            control,
            textvariable=self.location,
            values=[
                "kitchen",
                "living_room",
                "bedroom",
                "front_door",
                "back_door"
            ],
            state="readonly"
        ).grid(row=0, column=1)

        ttk.Label(control, text="Motion Intensity").grid(row=1, column=0, sticky="w")
        self.motion = tk.DoubleVar(value=0.8)
        ttk.Scale(control, from_=0, to=1, variable=self.motion).grid(row=1, column=1, sticky="ew")
        lbl1 = ttk.Label(control, text=f"Value: {self.motion.get():.2f}")
        lbl1.grid(row=1, column=2, sticky="w")
        self.motion.trace_add("write", lambda *args: lbl1.config(text=f"Value: {self.motion.get():.2f}"))
        
        ttk.Label(control, text="Distance (m)").grid(row=2, column=0, sticky="w")
        self.distance = tk.DoubleVar(value=1.0)
        ttk.Scale(control, from_=0, to=10, variable=self.distance).grid(row=2, column=1, sticky="ew")
        lbl2 = ttk.Label(control,text = f"Value: {self.distance.get():.2f}")
        lbl2.grid(row=2,column=2,sticky="w")
        self.distance.trace_add("write",lambda *args: lbl2.config(text=f"Value: {self.distance.get():.2f}"))

        ttk.Label(control, text="Gas Level").grid(row=3, column=0, sticky="w")
        self.gas = tk.DoubleVar(value=0.2)
        ttk.Scale(control, from_=0, to=1, variable=self.gas).grid(row=3, column=1, sticky="ew")
        lbl3 = ttk.Label(control,text = f"Value: {self.gas.get():.2f}")
        lbl3.grid(row=3,column=2,sticky="w")
        self.gas.trace_add("write",lambda *args: lbl3.config(text=f"Value: {self.gas.get():.2f}"))

        ttk.Label(control, text="Temperature").grid(row=4, column=0, sticky="w")
        self.temp = tk.DoubleVar(value=25)
        ttk.Scale(control, from_=0, to=50, variable=self.temp).grid(row=4, column=1, sticky="ew")
        lbl4 = ttk.Label(control,text = f"Value: {self.temp.get():.2f}")
        lbl4.grid(row=4,column=2,sticky="w")
        self.temp.trace_add("write",lambda *args: lbl4.config(text=f"Value: {self.temp.get():.2f}"))
        

        ttk.Label(control, text="Power Draw").grid(row=5, column=0, sticky="w")
        self.power = tk.DoubleVar(value=900)
        ttk.Scale(control, from_=0, to=3000, variable=self.power).grid(row=5, column=1, sticky="ew")
        lbl5 = ttk.Label(control,text = f"Value: {self.power.get():.2f}")
        lbl5.grid(row=5,column=2,sticky="w")
        self.power.trace_add("write",lambda *args: lbl5.config(text=f"Value: {self.power.get():.2f}"))


        self.wifi = tk.BooleanVar(value=True)
        self.bluetooth = tk.BooleanVar(value=True)

        ttk.Checkbutton(control, text="WiFi Present", variable=self.wifi).grid(row=6, column=0)
        ttk.Checkbutton(control, text="Bluetooth Present", variable=self.bluetooth).grid(row=6, column=1)

        buttons = ttk.Frame(self.root, padding=10)
        buttons.pack(fill="x")

        ttk.Button(buttons, text="Motion Event", command=self.send_motion).pack(side="left")
        ttk.Button(buttons, text="Gas Event", command=self.send_gas).pack(side="left")
        ttk.Button(buttons, text="Presence Event", command=self.send_presence).pack(side="left")
        ttk.Button(buttons, text="Power Event", command=self.send_power).pack(side="left")

        self.status_label = ttk.Label(self.root, text="State: LOW_POWER")
        self.status_label.pack(fill="x")

        self.log_box = tk.Text(self.root)
        self.log_box.pack(fill="both", expand=True)

    def refresh(self):

        self.status_label.config(
            text=f"State: {self.monday.state.value.upper()}"
        )

        self.log_box.delete("1.0", tk.END)

        for entry in self.monday.event_log[-50:]:
            self.log_box.insert(
                tk.END,
                f"[{entry['level'].upper()}] {entry['message']}\n"
            )

    def send_motion(self):

        event = self.simulator.generate_motion_event(
            location=self.location.get(),
            distance=self.distance.get(),
            intensity=self.motion.get()
        )

        self.monday.process_event(event)
        self.refresh()

    def send_gas(self):

        event = self.simulator.generate_gas_event(
            location=self.location.get(),
            gas_level=self.gas.get()
        )

        self.monday.process_event(event)
        self.refresh()

    def send_presence(self):

        event = self.simulator.generate_presence_event(
            wifi=self.wifi.get(),
            bluetooth=self.bluetooth.get()
        )

        self.monday.process_event(event)
        self.refresh()

    def send_power(self):

        event = self.simulator.generate_power_event(
            appliance="coffee_machine",
            watts=self.power.get()
        )

        self.monday.process_event(event)
        self.refresh()
    
    def auto_refresh(self):

        self.refresh()

        self.root.after(
            500,
            self.auto_refresh
        )
print("Control panel loaded successfully.")