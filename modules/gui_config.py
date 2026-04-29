import oyaml as yaml
import time

import numpy as np


class GUI_Config:
    G_GUI_INDEX = {
        "boot": 0,
        "Main": 1,
    }

    # Per-item font scale for value text in PyQt item widgets.
    G_ITEM_VALUE_FONT_SCALE = {
        "CPU_MEM": 0.8,
    }

    def __init__(self, layout_file, config=None):
        self.config = config
        self.layout = {}

        # Build G_UNIT dictionary based on unit system
        if config and config.G_UNIT_SYSTEM == "imperial":
            self.G_UNIT = {
                "HeartRate": (".0f", "bpm"),
                "Cadence": (".0f", "rpm"),
                "Speed": (".1f", "mph"),
                "Distance": (".1f", "mi"),
                "Power": (".0f", "W"),
                "Work": (".0f", "kJ"),
                "Position": (".5f", ""),
                "Altitude": (".0f", "ft"),
                "Wind": (".1f", "mph"),
                "Temp": (".0f", "F"),
                "GPS_error": (".0f", "ft"),
                "GPS_DOP": (".1f", ""),
                "String": ("s", ""),
                "Percent": (".0f", "%"),
                "Int": (".0f", ""),
            }
        else:  # metric (default)
            self.G_UNIT = {
                "HeartRate": (".0f", "bpm"),
                "Cadence": (".0f", "rpm"),
                "Speed": (".1f", "km/h"),
                "Distance": (".1f", "km"),
                "Power": (".0f", "W"),
                "Work": (".0f", "kJ"),
                "Position": (".5f", ""),
                "Altitude": (".0f", "m"),
                "Wind": (".1f", "m/s"),
                "Temp": ("3.0f", "C"),
                "GPS_error": (".0f", "m"),
                "GPS_DOP": (".1f", ""),
                "String": ("s", ""),
                "Percent": (".0f", "%"),
                "Int": (".0f", ""),
            }

        # Build G_ITEM_DEF using the unit dictionary
        self.G_ITEM_DEF = {
            # integrated
            "Power": (self.G_UNIT["Power"], "self.sensor.values['integrated']['power']"),
            "NP": (self.G_UNIT["Power"], "self.sensor.values['integrated']['normalized_power']"),
            "Speed": (self.G_UNIT["Speed"], "self.sensor.values['integrated']['speed']"),
            "Dist.": (self.G_UNIT["Distance"], "self.sensor.values['integrated']['distance']"),
            "Distance": (self.G_UNIT["Distance"], "self.sensor.values['integrated']['distance']"),
            "Cad.": (self.G_UNIT["Cadence"], "self.sensor.values['integrated']['cadence']"),
            "HR": (self.G_UNIT["HeartRate"], "self.sensor.values['integrated']['heart_rate']"),
            "Work": (
                self.G_UNIT["Work"],
                "self.sensor.values['integrated']['accumulated_power']",
            ),
            "W'bal": (self.G_UNIT["Work"], "self.sensor.values['integrated']['w_prime_balance']"),
            "W'bal(Norm)": (
                self.G_UNIT["Percent"],
                "self.sensor.values['integrated']['w_prime_balance_normalized']",
            ),
            "TSS": ((".0f", ""), "self.sensor.values['integrated']['tss']"),
            "Grade": (self.G_UNIT["Percent"], "self.sensor.values['integrated']['grade']"),
            "Grade(spd)": (
                self.G_UNIT["Percent"],
                "self.sensor.values['integrated']['grade_spd']",
            ),
            "GlideRatio": (
                self.G_UNIT["Altitude"], 
                "self.sensor.values['integrated']['glide_ratio']"
            ),
            "Temp": (self.G_UNIT["Temp"], "self.sensor.values['integrated']['temperature']"),
            # average_values
            "Power(3s)": (
                self.G_UNIT["Power"],
                "self.sensor.values['integrated']['ave_power_3s']",
            ),
            "Power(30s)": (
                self.G_UNIT["Power"],
                "self.sensor.values['integrated']['ave_power_30s']",
            ),
            "Power(60s)": (
                self.G_UNIT["Power"],
                "self.sensor.values['integrated']['ave_power_60s']",
            ),
            "WindSpeed": (self.G_UNIT["Wind"], "self.sensor.values['integrated']['wind_speed']"),
            "WindDir": (
                self.G_UNIT["String"], 
                "self.sensor.values['integrated']['wind_direction_str']"
            ),
            "HeadWind": (self.G_UNIT["Wind"], "self.sensor.values['integrated']['headwind']"),
            # GPS raw
            "Latitude": (self.G_UNIT["Position"], "self.sensor.values['GPS']['lat']"),
            "Longitude": (self.G_UNIT["Position"], "self.sensor.values['GPS']['lon']"),
            "Alt.(GPS)": (self.G_UNIT["Altitude"], "self.sensor.values['GPS']['alt']"),
            "Speed(GPS)": (self.G_UNIT["Speed"], "self.sensor.values['GPS']['speed']"),
            "Dist.(GPS)": (self.G_UNIT["Distance"], "self.sensor.values['GPS']['distance']"),
            "Heading_RAW(GPS)": (self.G_UNIT["Int"], "self.sensor.values['GPS']['track']"),
            "Heading(GPS)": (self.G_UNIT["String"], "self.sensor.values['GPS']['track_str']"),
            "Satellites": (self.G_UNIT["String"], "self.sensor.values['GPS']['used_sats_str']"),
            "Error(x)": (self.G_UNIT["GPS_error"], "self.sensor.values['GPS']['epx']"),
            "Error(y)": (self.G_UNIT["GPS_error"], "self.sensor.values['GPS']['epy']"),
            "Error(alt)": (self.G_UNIT["GPS_error"], "self.sensor.values['GPS']['epv']"),
            "PDOP": (self.G_UNIT["GPS_DOP"], "self.sensor.values['GPS']['pdop']"),
            "HDOP": (self.G_UNIT["GPS_DOP"], "self.sensor.values['GPS']['hdop']"),
            "VDOP": (self.G_UNIT["GPS_DOP"], "self.sensor.values['GPS']['vdop']"),
            "GPSTime": (self.G_UNIT["String"], "self.sensor.values['GPS']['utctime']"),
            "GPS Fix": (("d", ""), "self.sensor.values['GPS']['mode']"),
            "Course Dist.": (
                self.G_UNIT["Distance"],
                "self.course.index.distance",
            ),
            # ANT+ raw
            "HR(ANT+)": (
                self.G_UNIT["HeartRate"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['HR']]['heart_rate']",
            ),
            "Speed(ANT+)": (
                self.G_UNIT["Speed"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['SPD']]['speed']",
            ),
            "Dist.(ANT+)": (
                self.G_UNIT["Distance"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['SPD']]['distance']",
            ),
            "Cad.(ANT+)": (
                self.G_UNIT["Cadence"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['CDC']]['cadence']",
            ),
            # get from sensor as powermeter pairing
            # (cannot get from other pairing not including power sensor pairing)
            "Power16(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x10]['power']",
            ),
            "Power16s(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x10]['power_16_simple']",
            ),
            "Cad.16(ANT+)": (
                self.G_UNIT["Cadence"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x10]['cadence']",
            ),
            "Work16(ANT+)": (
                self.G_UNIT["Work"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x10]['accumulated_power']",
            ),
            "NP16(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['integrated']['normalized_power']",
            ),
            "Power R(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x10]['power_r']",
            ),
            "Power L(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x10]['power_l']",
            ),
            "Balance(ANT+)": (
                self.G_UNIT["String"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x10]['lr_balance']",
            ),
            "Power17(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x11]['power']",
            ),
            "Speed17(ANT+)": (
                self.G_UNIT["Speed"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x11]['speed']",
            ),
            "Dist.17(ANT+)": (
                self.G_UNIT["Distance"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x11]['distance']",
            ),
            "Work17(ANT+)": (
                self.G_UNIT["Work"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x11]['accumulated_power']",
            ),
            "NP17(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['integrated']['normalized_power']",
            ),
            "Power18(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x12]['power']",
            ),
            "Cad.18(ANT+)": (
                self.G_UNIT["Cadence"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x12]['cadence']",
            ),
            "Work18(ANT+)": (
                self.G_UNIT["Work"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x12]['accumulated_power']",
            ),
            "NP18(ANT+)": (
                self.G_UNIT["Power"],
                "self.sensor.values['integrated']['normalized_power']",
            ),
            "Torque Ef.(ANT+)": (
                self.G_UNIT["String"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x13]['torque_eff']",
            ),
            "Pedal Sm.(ANT+)": (
                self.G_UNIT["String"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['PWR']][0x13]['pedal_sm']",
            ),
            "Light(ANT+)": (
                self.G_UNIT["String"],
                "self.sensor.values['ANT+'][self.config.G_ANT['ID_TYPE']['LGT']]['light_mode']",
            ),
            # ANT+ multi
            "PWR1": (self.G_UNIT["Power"], "None"),
            "PWR2": (self.G_UNIT["Power"], "None"),
            "PWR3": (self.G_UNIT["Power"], "None"),
            "HR1": (self.G_UNIT["HeartRate"], "None"),
            "HR2": (self.G_UNIT["HeartRate"], "None"),
            "HR3": (self.G_UNIT["HeartRate"], "None"),
            # Sensor raw
            "Temp_RAW(I2C)": (self.G_UNIT["Temp"], "self.sensor.values['I2C']['temperature']"),
            "Pressure": (("4.0f", "hPa"), "self.sensor.values['I2C']['pressure']"),
            "Altitude": (self.G_UNIT["Altitude"], "self.sensor.values['I2C']['altitude']"),
            "Humidity": (self.G_UNIT["Percent"], "self.sensor.values['I2C']['humidity']"),
            "D_INDEX": (self.G_UNIT["Int"], "self.sensor.values['I2C']['discomfort_index']"),
            "Accum.Alt.": (
                self.G_UNIT["Altitude"],
                "self.sensor.values['I2C']['accumulated_altitude']",
            ),
            "Vert.Spd": (("3.1f", "m/s"), "self.sensor.values['I2C']['vertical_speed']"),
            "Ascent": (self.G_UNIT["Altitude"], "self.sensor.values['I2C']['total_ascent']"),
            "Descent": (self.G_UNIT["Altitude"], "self.sensor.values['I2C']['total_descent']"),
            "Light": (self.G_UNIT["Int"], "self.sensor.values['I2C']['light']"),
            "Infrared": (self.G_UNIT["Int"], "self.sensor.values['I2C']['infrared']"),
            "UVI": (self.G_UNIT["Int"], "self.sensor.values['I2C']['uvi']"),
            "VOC_Index": (self.G_UNIT["Int"], "self.sensor.values['I2C']['voc_index']"),
            "Raw_Gas": (self.G_UNIT["Int"], "self.sensor.values['I2C']['raw_gas']"),
            "Battery": (self.G_UNIT["Percent"], "self.sensor.values['I2C']['battery_percentage']"),
            "Motion": (("1.1f", ""), "self.sensor.values['I2C']['motion']"),
            "M_Stat": (("1.1f", ""), "self.sensor.values['I2C']['m_stat']"),
            "ACC_X": (("1.1f", ""), "self.sensor.values['I2C']['acc'][0]"),
            "ACC_Y": (("1.1f", ""), "self.sensor.values['I2C']['acc'][1]"),
            "ACC_Z": (("1.1f", ""), "self.sensor.values['I2C']['acc'][2]"),
            "MAG_X": (("1.1f", ""), "self.sensor.values['I2C']['mag'][0]"),
            "MAG_Y": (("1.1f", ""), "self.sensor.values['I2C']['mag'][1]"),
            "MAG_Z": (("1.1f", ""), "self.sensor.values['I2C']['mag'][2]"),
            "Heading": (self.G_UNIT["String"], "self.sensor.values['I2C']['heading_str']"),
            "Heading_Raw(I2C)": (self.G_UNIT["Int"], "self.sensor.values['I2C']['raw_heading']"),
            "Heading_Tilt": (self.G_UNIT["Int"], "self.sensor.values['I2C']['heading']"),
            "Pitch": (self.G_UNIT["Int"], "self.sensor.values['I2C']['grade_pitch']"),
            "Pitch_Fixed": (
                self.G_UNIT["Int"],
                "int(180/3.1415*self.sensor.values['I2C']['fixed_pitch'])"
            ),
            "Roll_Fixed": (
                self.G_UNIT["Int"],
                "int(180/3.1415*self.sensor.values['I2C']['fixed_roll'])"
            ),
            "Pitch_Raw": (
                self.G_UNIT["Int"],
                "int(180/3.1415*self.sensor.values['I2C']['pitch'])"
            ),
            "Roll_Raw": (
                self.G_UNIT["Int"],
                "int(180/3.1415*self.sensor.values['I2C']['roll'])"
            ),
            "Grade(pitch)": (self.G_UNIT["Percent"],"self.sensor.values['I2C']['grade_pitch']"),
            # General
            "Timer": (("timer", ""), "self.logger.values['count']"),
            "LapTime": (("timer", ""), "self.logger.values['count_lap']"),
            "Lap": (("d", ""), "self.logger.values['lap']"),
            "Time": (("time", ""), "0"),
            "ElapsedTime": (("timer", ""), "self.logger.values['elapsed_time']"),
            "GrossAveSPD": (self.G_UNIT["Speed"], "self.logger.values['gross_ave_spd']"),
            "GrossDiffTime": (self.G_UNIT["String"], "self.logger.values['gross_diff_time']"),
            "CPU_MEM": (self.G_UNIT["String"], "self.sensor.values['integrated']['CPU_MEM']"),
            "Send Time": (
                self.G_UNIT["String"],
                "self.sensor.values['integrated']['send_time']",
            ),
            # Statistics
            # Pre Lap Average or total
            "PLap HR": (
                self.G_UNIT["HeartRate"],
                "self.logger.record_stats['pre_lap_avg']['heart_rate']",
            ),
            "PLap CAD": (
                self.G_UNIT["Cadence"],
                "self.logger.record_stats['pre_lap_avg']['cadence']",
            ),
            "PLap DIST": (
                self.G_UNIT["Distance"],
                "self.logger.record_stats['pre_lap_avg']['distance']",
            ),
            "PLap SPD": (
                self.G_UNIT["Speed"],
                "self.logger.record_stats['pre_lap_avg']['speed']",
            ),
            "PLap PWR": (
                self.G_UNIT["Power"],
                "self.logger.record_stats['pre_lap_avg']['power']",
            ),
            "PLap WRK": (
                self.G_UNIT["Work"],
                "self.logger.record_stats['pre_lap_avg']['accumulated_power']",
            ),
            "PLap ASC": (
                self.G_UNIT["Altitude"],
                "self.logger.record_stats['pre_lap_avg']['total_ascent']",
            ),
            "PLap DSC": (
                self.G_UNIT["Altitude"],
                "self.logger.record_stats['pre_lap_avg']['total_descent']",
            ),
            # Lap Average or total
            "Lap HR": (
                self.G_UNIT["HeartRate"],
                "self.logger.record_stats['lap_avg']['heart_rate']",
            ),
            "Lap CAD": (
                self.G_UNIT["Cadence"],
                "self.logger.record_stats['lap_avg']['cadence']",
            ),
            "Lap DIST": (
                self.G_UNIT["Distance"],
                "self.logger.record_stats['lap_avg']['distance']",
            ),
            "Lap SPD": (self.G_UNIT["Speed"], "self.logger.record_stats['lap_avg']['speed']"),
            "Lap PWR": (self.G_UNIT["Power"], "self.logger.record_stats['lap_avg']['power']"),
            "Lap WRK": (
                self.G_UNIT["Work"],
                "self.logger.record_stats['lap_avg']['accumulated_power']",
            ),
            "Lap ASC": (
                self.G_UNIT["Altitude"],
                "self.logger.record_stats['lap_avg']['total_ascent']",
            ),
            "Lap DSC": (
                self.G_UNIT["Altitude"],
                "self.logger.record_stats['lap_avg']['total_descent']",
            ),
            # Entire Average
            "Ave HR": (
                self.G_UNIT["HeartRate"],
                "self.logger.record_stats['entire_avg']['heart_rate']",
            ),
            "Ave CAD": (
                self.G_UNIT["Cadence"],
                "self.logger.record_stats['entire_avg']['cadence']",
            ),
            "Ave SPD": (self.G_UNIT["Speed"], "self.logger.record_stats['entire_avg']['speed']"),
            "Ave PWR": (self.G_UNIT["Power"], "self.logger.record_stats['entire_avg']['power']"),
            # Max
            "Max HR": (
                self.G_UNIT["HeartRate"],
                "self.logger.record_stats['entire_max']['heart_rate']",
            ),
            "Max CAD": (
                self.G_UNIT["Cadence"],
                "self.logger.record_stats['entire_max']['cadence']",
            ),
            "Max SPD": (self.G_UNIT["Speed"], "self.logger.record_stats['entire_max']['speed']"),
            "Max PWR": (self.G_UNIT["Power"], "self.logger.record_stats['entire_max']['power']"),
            "LMax HR": (
                self.G_UNIT["HeartRate"],
                "self.logger.record_stats['lap_max']['heart_rate']",
            ),
            "LMax CAD": (
                self.G_UNIT["Cadence"],
                "self.logger.record_stats['lap_max']['cadence']",
            ),
            "LMax SPD": (self.G_UNIT["Speed"], "self.logger.record_stats['lap_max']['speed']"),
            "LMax PWR": (self.G_UNIT["Power"], "self.logger.record_stats['lap_max']['power']"),
            "PLMax HR": (
                self.G_UNIT["HeartRate"],
                "self.logger.record_stats['pre_lap_max']['heart_rate']",
            ),
            "PLMax CAD": (
                self.G_UNIT["Cadence"],
                "self.logger.record_stats['pre_lap_max']['cadence']",
            ),
            "PLMax SPD": (
                self.G_UNIT["Speed"],
                "self.logger.record_stats['pre_lap_max']['speed']",
            ),
            "PLMax PWR": (
                self.G_UNIT["Power"],
                "self.logger.record_stats['pre_lap_max']['power']",
            ),
        }

        try:
            with open(layout_file) as file:
                text = file.read()
                self.layout = yaml.safe_load(text)
        except FileNotFoundError:
            pass
    
    def format_text(self, name, value, G_STOPWATCH_STATUS, itemformat):
        text = "-"
        if value is None:
            pass
        elif isinstance(value, str):
            text = value
        elif np.isnan(value):
            pass
        elif name.startswith("Speed") or "SPD" in name:
            # Speed: m/s to display unit
            if self.config and self.config.G_UNIT_SYSTEM == "imperial":
                text = f"{(value * 2.23694):{itemformat}}"  # m/s to mph
            else:
                text = f"{(value * 3.6):{itemformat}}"  # m/s to km/h
        elif "Dist" in name or "DIST" in name:
            # Distance: m to display unit
            if self.config and self.config.G_UNIT_SYSTEM == "imperial":
                text = f"{(value / 1609.34):{itemformat}}"  # m to miles
            else:
                text = f"{(value / 1000):{itemformat}}"  # m to km
        elif "Alt" in name or "Altitude" in name or "Error" in name or "Ascent" in name or "Descent" in name or "Accum.Alt." in name:
            # Altitude/GPS errors/ascent/descent: m to display unit
            if self.config and self.config.G_UNIT_SYSTEM == "imperial":
                text = f"{(value * 3.28084):{itemformat}}"  # m to feet
            else:
                text = f"{value:{itemformat}}"  # m (no conversion)
        elif "Wind" in name or "HeadWind" in name:
            # Wind speed: m/s to display unit
            if self.config and self.config.G_UNIT_SYSTEM == "imperial":
                text = f"{(value * 2.23694):{itemformat}}"  # m/s to mph
            else:
                text = f"{value:{itemformat}}"  # m/s (no conversion)
        elif "Temp" in name:
            # Temperature
            if self.config and self.config.G_UNIT_SYSTEM == "imperial":
                text = f"{((value * 9/5) + 32):{itemformat}}"  # C to F
            else:
                text = f"{value:{itemformat}}"  # C (no conversion)
        elif "Work" in name or "WRK" in name:
            text = f"{(value / 1000):{itemformat}}"  # j to kj (both systems)
        elif (
            "Grade" in name or "Glide" in name
        ) and G_STOPWATCH_STATUS != "START":
            text = "-"
        elif itemformat == "timer":
            # fmt = '%H:%M:%S' #default (too long)
            fmt = "%H:%M"
            if value < 3600:
                fmt = "%M:%S"
            text = time.strftime(fmt, time.gmtime(value))
        elif itemformat == "time":
            text = time.strftime("%H:%M")
        else:
            text = f"{value:{itemformat}}"

        return text
