"""Script to run batch commands
"""
import os
import subprocess
from multiprocessing import Pool, cpu_count

from energy_demand.read_write import read_weather_data

def my_function(simulation_number):  
    print('simulation_number ' + str(simulation_number))

    all_weather_stations = False

    same_weather_yr = True
    defined_weather_yr = 2015

    # --------------------------
    # Get all weather yrs with data (maybe read existing years from data folder)
    # and select weather yr
    # --------------------------
    path_to_weather_data = "C:/Users/cenv0553/ED/data/_raw_data/A-temperature_data/cleaned_weather_stations_data"
    weather_yrs = read_weather_data.get_all_weather_yrs(path_to_weather_data)

    if same_weather_yr:
        weather_yr = defined_weather_yr
    else:
        weather_yr = weather_yrs[simulation_number]

    # --------------------------
    # Select weather station
    # --------------------------
    if all_weather_stations:
        weather_station_cnt = [] #All stationssimulation_number
    else:
        weather_station_cnt = simulation_number

    # Run energy demand main.py
    os.system("cd C:/Users/cenv0553/ed")
    os.system("python energy_demand/energy_demand/main.py {} {}".format(weather_yr, weather_station_cnt))

    print("======================")
    print("Finished model run simulation: weather_yr: {} weather_station_cnt: {}".format(weather_yr, weather_station_cnt))
    print("======================")

# ===============================
#simulation_number = range(40)
simulation_number = range(2,4)

for i in simulation_number:
    my_function(i)
