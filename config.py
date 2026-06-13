class Config:

    # --------------------------------------------------------
    # SPIKE THRESHOLDS
    # Values from 0.0 to 1.0, sensor readings above these
    # thresholds are treated as significant events
    # --------------------------------------------------------
    SPIKE_THRESHOLD_MOTION = 0.7
    SPIKE_THRESHOLD_POWER = 0.6
    SPIKE_THRESHOLD_GAS = 0.5

    # --------------------------------------------------------
    # DISTANCE THRESHOLDS in meters
    # Controls how close someone must be before triggering
    # door and outside motion events to avoid false positives
    # --------------------------------------------------------
    NIGHT_MOTION_DOOR_DISTANCE = 2.0
    NIGHT_MOTION_OUTSIDE_DISTANCE = 5.0
    DAYTIME_MOTION_DOOR_DISTANCE = 1.5

    # --------------------------------------------------------
    # TIME WINDOWS
    # AC pre activation fires this many minutes before
    # the users average arrival time
    # AC auto off fires this many minutes after user leaves range
    # --------------------------------------------------------
    AC_PRE_ACTIVATION_MINUTES = 10
    AC_AUTO_OFF_MINUTES = 10

    # Night mode hours, motion outside during this window
    # triggers a security alert
    NIGHT_MODE_START_HOUR = 0
    NIGHT_MODE_END_HOUR = 5

    # --------------------------------------------------------
    # MEMORY SETTINGS
    # --------------------------------------------------------
    SHORT_TERM_MEMORY_SIZE = 50
    LONG_TERM_MEMORY_DAYS = 30

    # --------------------------------------------------------
    # POWER ANOMALY
    # If current usage exceeds average by this multiplier
    # an anomaly warning is sent to the user
    # --------------------------------------------------------
    POWER_ANOMALY_MULTIPLIER = 1.5

    # --------------------------------------------------------
    # BASELINE POWER DRAW in watts for each appliance
    # Used for anomaly detection and recommendation comparisons
    # --------------------------------------------------------
    APPLIANCE_BASELINE_POWER = {
        "coffee_machine":   900,
        "ac":              1500,
        "refrigerator":     150,
        "lights_living_room": 60,
        "lights_kitchen":    40,
        "lights_bedroom":    30,
        "tv":               120,
        "water_heater":    2000,
    }