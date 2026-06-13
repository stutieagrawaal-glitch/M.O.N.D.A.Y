import json
import sys
import os
from datetime import datetime, timedelta
 
# Add project root to path so all module imports resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 
from core.monday import Monday
from core.states import SensorEvent, SensorType
from sensors.simulator import SensorSimulator
 
 
def seed_historical_data(monday: Monday):
    """
    Pre populate habit memory with a few days of history so prediction
    and recommendation engines have enough data to work with from the start.
    On a live system this data builds up automatically over several days.
    """
    monday.memory.habit_patterns["wake_up_times"]      = [6.5, 6.4, 6.6, 6.5, 6.3]
    monday.memory.habit_patterns["home_arrival_times"] = [18.0, 17.9, 18.1, 18.0, 17.8]
 
    # Seed coffee machine sessions so the recommendation threshold is met
    base_time = datetime.now() - timedelta(days=6)
    for i in range(6):
        monday.memory.record_appliance_usage(
            appliance        = "coffee_machine",
            duration_minutes = 5,
            power_used       = 75.0,
            timestamp        = base_time + timedelta(days=i),
        )
 
 
def run_simulation():
    print("=" * 60)
    print("  MONDAY NEUROMORPHIC SMART HOME SYSTEM")
    print("  Starting simulation...")
    print("=" * 60)
 
    monday    = Monday()
    simulator = SensorSimulator()
 
    seed_historical_data(monday)
 
    # --------------------------------------------------------
    # SCENARIO 1: Morning routine, kitchen motion triggers
    #             coffee machine pre activation
    # --------------------------------------------------------
    print("\n=== SCENARIO 1: MORNING ROUTINE (06:30) ===")
    simulator.simulated_time = datetime.now().replace(hour=6, minute=30, second=0, microsecond=0)
 
    monday.process_event(
        simulator.generate_motion_event(location="kitchen", distance=1.0, intensity=0.8)
    )
    monday.run_periodic_checks(simulator.simulated_time)
 
    # --------------------------------------------------------
    # SCENARIO 2: AC pre activation before user arrives home
    # --------------------------------------------------------
    print("\n=== SCENARIO 2: AC PRE ACTIVATION (17:50) ===")
    simulator.simulated_time = simulator.simulated_time.replace(hour=17, minute=50)
 
    monday.process_event(
        simulator.generate_presence_event(wifi=False, bluetooth=False)
    )
 
    # --------------------------------------------------------
    # SCENARIO 3: User absent 11 minutes, AC auto off
    # --------------------------------------------------------
    print("\n=== SCENARIO 3: USER ABSENT, AC AUTO OFF ===")
    simulator.simulated_time = simulator.simulated_time.replace(hour=18, minute=0)
 
    monday.process_event(simulator.generate_presence_event(wifi=True, bluetooth=True))
    monday.state = monday.state.__class__.ACTIVE
    monday.appliances.turn_on("ac", simulator.simulated_time, monday.log)
 
    simulator.simulated_time = simulator.simulated_time.replace(hour=18, minute=1)
    monday.process_event(simulator.generate_presence_event(wifi=False, bluetooth=False))
 
    simulator.advance_time(minutes=11)
    monday.process_event(simulator.generate_presence_event(wifi=False, bluetooth=False))
 
    # --------------------------------------------------------
    # SCENARIO 4: Night motion at door, far away, ignored
    # --------------------------------------------------------
    print("\n=== SCENARIO 4: NIGHT MOTION FAR AWAY (01:00), IGNORED ===")
    simulator.simulated_time = simulator.simulated_time.replace(hour=1, minute=0)
 
    monday.process_event(
        simulator.generate_motion_event(location="front_door", distance=9.0, intensity=0.8)
    )
 
    # --------------------------------------------------------
    # SCENARIO 5: Night motion at door, close range, triggers
    # --------------------------------------------------------
    print("\n=== SCENARIO 5: NIGHT MOTION CLOSE RANGE (01:01), TRIGGERS ===")
    simulator.advance_time(minutes=1)
 
    monday.process_event(
        simulator.generate_motion_event(location="front_door", distance=1.2, intensity=0.8)
    )
 
    # --------------------------------------------------------
    # SCENARIO 6: Gas leak emergency
    # --------------------------------------------------------
    print("\n=== SCENARIO 6: GAS LEAK EMERGENCY ===")
    monday.process_event(
        simulator.generate_gas_event(location="kitchen", gas_level=0.9)
    )
 
    # --------------------------------------------------------
    # SCENARIO 7: Power anomaly on coffee machine
    # --------------------------------------------------------
    print("\n=== SCENARIO 7: POWER ANOMALY DETECTION ===")
    monday.state = monday.state.__class__.ACTIVE
    monday.emergency.clear_emergency()
 
    monday.process_event(
        simulator.generate_power_event(appliance="coffee_machine", watts=2200)
    )
 
    # --------------------------------------------------------
    # SCENARIO 8: Appliance efficiency recommendation
    # --------------------------------------------------------
    print("\n=== SCENARIO 8: APPLIANCE RECOMMENDATION CHECK ===")
    monday.run_periodic_checks(simulator.simulated_time)
 
    # --------------------------------------------------------
    # FINAL STATUS REPORT
    # --------------------------------------------------------
    print("\n=== FINAL STATUS REPORT ===")
    status = monday.get_status_report()
    print(json.dumps(status, indent=2, default=str))
    print("\nSimulation complete.")
 
 
if __name__ == "__main__":
    run_simulation()
 