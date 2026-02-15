# services/timetable_config.py

TIMETABLE = {
    "Ev": {
        "first_departure": "07:00",
        "last_departure": "22:00",
        "freq_peak_min": 15,
        "freq_offpeak_min": 30,
        "peak_windows": [("08:00", "10:00"), ("17:00", "20:00")]
    },
    "Red": {
        "first_departure": "07:00",
        "last_departure": "22:00",
        "freq_peak_min": 15,
        "freq_offpeak_min": 30,
        "peak_windows": [("08:00", "10:00"), ("17:00", "20:00")]
    },
    "Green": {
        "first_departure": "07:00",
        "last_departure": "22:00",
        "freq_peak_min": 10,
        "freq_offpeak_min": 15,
        "peak_windows": [("08:00", "10:00"), ("17:00", "20:00")]
    },
    "Pink": {
        "female_only": True,
        "service_windows": [("08:00", "09:00"), ("13:00", "14:00"), ("17:00", "19:00")],
        "freq_peak_min": 20,
        "freq_offpeak_min": 60
    },
    "Double Decker": {
        "first_departure": "06:00",
        "last_departure": "22:00",
        "freq_peak_min": 15,
        "freq_offpeak_min": 15,
        "peak_windows": [("06:00","22:00")]
    }
}
