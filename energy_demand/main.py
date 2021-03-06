"""Allows to run HIRE locally outside the SMIF framework

write_national_results_amman
move data config folder into data
Note
----
Always execute from root folder. e.g.: 

    energy_demand/energy_demand/main.py 
"""
import os
import sys
import time
import logging
from collections import defaultdict
import pandas as pd

from energy_demand.basic import basic_functions, date_prop, demand_supply_interaction, testing_functions, lookup_tables
from energy_demand import model
from energy_demand.assumptions import strategy_vars_def, general_assumptions
from energy_demand.read_write import read_data, write_data, data_loader
from energy_demand.validation import lad_validation
from energy_demand.scripts import s_scenario_param, init_scripts, s_disaggregation
from energy_demand.plotting import fig_enduse_yh

def energy_demand_model(
        regions,
        data,
        criterias,
        assumptions,
        weather_stations,
        weather_yr,
        weather_by
    ):
    """Main function of energy demand model to calculate yearly demand

    Arguments
    ----------
    regions : list
        Regions
    data : dict
        Data container
    assumptions : dict
        Assumptions
    weather_yr: int
        Year of weather data

    Returns
    -------
    result_dict : dict
        A nested dictionary containing all data for energy supply model with
        timesteps for every hour in a year.
        [fueltype : region : timestep]
    modelrun_obj : dict
        Object of a yearly model run

    Note
    ----
    This function is executed in the wrapper
    """
    logging.info("... Number of modelled regions: %s", len(regions))

    modelrun = model.EnergyDemandModel(
        regions=regions,
        data=data,
        criterias=criterias,
        assumptions=assumptions,
        weather_stations=weather_stations,
        weather_yr=weather_yr,
        weather_by=weather_by)

    # Calculate base year demand
    fuels_in = testing_functions.test_function_fuel_sum(
        data, data['fuel_disagg'], criterias['mode_constrained'], assumptions.enduse_space_heating)

    # Log model results
    write_data.logg_info(modelrun, fuels_in, data)

    return modelrun

if __name__ == "__main__":
    """Pass the path to the .ini file as argument

    Example:
    pthon energy_demand/energy_demand/main.py C:/Users/cenv0553/ed/energy_demand/local_run_config_file.ini

    TOOD IS path_config_data necessary?
    """
    
    # Update cluster file: #os.path.dirname(__file__), '..', 'local_run_config_file_cluster.ini'))
    if os.path.isfile(sys.argv[1]):
        path_config  = sys.argv[1]
    else:
        raise Exception("The defined .ini file does not exist_ {}".format(sys.argv[1]))
    config = data_loader.read_config_file(path_config)

    data = {}
    sim_yrs = [2015, 2020, 2025, 2030, 2035, 2040, 2045, 2050]
    #sim_yrs = [2015, 2020, 2050] #, 2050]
    sim_yrs = [2015, 2030, 2050]

    if len(sys.argv) > 3: #user defined arguments are provide
        scenario_name = str(sys.argv[2])
        weather_realisation = str(sys.argv[3]) # Weather realisation 
    else:
        scenario_name = "_dm_10P_"
        weather_realisation = 'NF1'

    print("-------------------------------------")
    print("Information")
    print("-------------------------------------")
    print("local_data_path             " + str(sys.argv[1]))
    print("Configuration path:         " + str(path_config))
    print("Simulated yrs               " + str(sim_yrs))

    #name_config_path = 'h_c'
    #name_config_path = 'l_c'
    #name_config_path = 'h_max'
    #name_config_path = 'h_min'
    name_config_path = 'h_min_zero'
    #name_config_path = 'h_min_5dm'
    name_config_path = 'h_min_10dm'
    #name_config_path = 'l_max'
    #name_config_path = 'l_min'

    # Local path configurations
    if config['CRITERIA']['cluster_calc']:
        path_weather_data = "/soge-home/staff/cenv0553/_weather_realisation"
    else:
        path_weather_data = "C:/Users/cenv0553/ED/data/scenarios"

    if name_config_path == 'h_max' or name_config_path == 'l_max':
        local_scenario = 'pop-b_econ-c_fuel-c' #high
    elif name_config_path == 'h_c' or name_config_path == 'l_c':
        local_scenario = 'pop-baseline16_econ-c16_fuel-c16' #middle
    elif name_config_path == 'h_min' or name_config_path == 'l_min' or name_config_path in ['h_min_zero', 'h_min_5dm', 'h_min_10dm']:
        local_scenario = 'pop-f_econ-c_fuel-c' #low

    # --- Paths
    path_strategy_vars = os.path.join(config['DATA_PATHS']['path_strategy_vars'], name_config_path)
    name_region_set = os.path.join(config['PATHS']['path_local_data'], 'region_definitions', "lad_2016_uk_simplified.shp")
    name_population_dataset = os.path.join(os.path.join(config['PATHS']['path_local_data'], ".."), 'scenarios', 'MISTRAL_pop_gva', 'data', '{}/population__lad.csv'.format(local_scenario))
    name_gva_dataset = os.path.join(os.path.join(config['PATHS']['path_local_data'], ".."),'scenarios', 'MISTRAL_pop_gva', 'data', '{}/gva_per_head__lad_sector.csv'.format(local_scenario))
    name_gva_dataset_per_head = os.path.join(os.path.join(config['PATHS']['path_local_data'], ".."), 'scenarios', 'MISTRAL_pop_gva', 'data', '{}/gva_per_head__lad.csv'.format(local_scenario))

    # --------------------
    # Create scenario path
    # --------------------
    name_scenario_run = "{}_result_local_{}".format(scenario_name, str(time.ctime()).replace(":", "_").replace(" ", "_"))
    path_new_scenario = os.path.join(config['PATHS']['path_result_data'], name_scenario_run)

    # -----------------------------------------------------------------------
    # Create new folders
    # -----------------------------------------------------------------------
    basic_functions.del_previous_setup(path_new_scenario)
    basic_functions.create_folder(path_new_scenario)

    # --------------------
    # Load all other paths
    # --------------------
    data['paths'] = config['CONFIG_DATA']
    data['local_paths'] = config['DATA_PATHS']
    data['result_paths'] = basic_functions.get_result_paths(path_new_scenario)

    for folder, folder_path in data['result_paths'].items():
        basic_functions.create_folder(folder_path)

    # ----------------------------------------------------------------------
    # Load data
    # ----------------------------------------------------------------------
    data['scenario_data'] = defaultdict(dict)
    data['enduses'], data['sectors'], data['fuels'], lookup_enduses, lookup_sector_enduses = data_loader.load_fuels(data['paths'])
    data['regions'] = read_data.get_region_names(name_region_set)
    data['reg_coord'] = basic_functions.get_long_lat_decimal_degrees(read_data.get_region_centroids(name_region_set))

    data['scenario_data']['population'] = data_loader.read_scenario_data(name_population_dataset)
    data['scenario_data']['gva_industry'] = data_loader.read_scenario_data_gva(name_gva_dataset, all_dummy_data=False)
    data['scenario_data']['gva_per_head'] = data_loader.read_scenario_data(name_gva_dataset_per_head)

    # -----------------------------
    # Assumptions
    # -----------------------------
    data['assumptions'] = general_assumptions.Assumptions(
        lookup_enduses=lookup_enduses,
        lookup_sector_enduses=lookup_sector_enduses,
        base_yr=config['CONFIG']['base_yr'],
        weather_by=config['CONFIG']['user_defined_weather_by'],
        simulation_end_yr=config['CONFIG']['user_defined_simulation_end_yr'],
        curr_yr=2015,
        sim_yrs=sim_yrs,
        paths=data['paths'],
        enduses=data['enduses'],
        sectors=data['sectors'],
        reg_nrs=len(data['regions']))

    # -----------------------------------------------------------------------------
    # Calculate population density for base year
    # -----------------------------------------------------------------------------
    region_objects = read_data.get_region_objects(name_region_set)
    data['pop_density'] = {}
    for region in region_objects:
        region_name = region['properties']['name']
        region_area = region['properties']['st_areasha']
        data['pop_density'][region_name] = data['scenario_data']['population'][data['assumptions'].base_yr][region_name] / region_area

    # -----------------------------------------------------------------------------
    # Load standard strategy variable values from .py file
    # Containing full information
    # -----------------------------------------------------------------------------        
    default_streategy_vars = strategy_vars_def.load_param_assump(
        default_values=True)

    # -----------------------------------------------------------------------------
    # Load standard smif parameters and generate standard single timestep narrative for simulation end year
    # -----------------------------------------------------------------------------
    strategy_vars = strategy_vars_def.generate_default_parameter_narratives(
        default_streategy_vars=default_streategy_vars,
        end_yr=2050,
        base_yr=config['CONFIG']['base_yr'])

    # -----------------------------------------
    # User defines stragey variable from csv files
    # -----------------------------------------
    user_defined_vars = data_loader.load_local_user_defined_vars(
        default_strategy_var=default_streategy_vars,
        path_csv=path_strategy_vars,
        simulation_base_yr=data['assumptions'].base_yr,
        simulation_end_yr=config['CONFIG']['user_defined_simulation_end_yr'])

    strategy_vars = data_loader.replace_variable(user_defined_vars, strategy_vars)

    # Replace strategy variables not defined in csv files
    strategy_vars_out = strategy_vars_def.autocomplete_strategy_vars(
        strategy_vars,
        narrative_crit=True)

    data['assumptions'].update('strategy_vars', strategy_vars_out)

    # -----------------------------------------------------------------------------
    # Load necessary data
    # -------------------------------------------------------------------------------
    data['tech_lp'] = data_loader.load_data_profiles(
        data['paths'], data['local_paths'],
        data['assumptions'].model_yeardays,
        data['assumptions'].model_yeardays_daytype,)

    technologies = general_assumptions.update_technology_assumption(
        data['assumptions'].technologies,
        data['assumptions'].strategy_vars['f_eff_achieved'],
        data['assumptions'].strategy_vars['gshp_fraction'])
    data['assumptions'].technologies.update(technologies)

    if config['CRITERIA']['virtual_building_stock_criteria']:
        data['scenario_data']['floor_area']['rs_floorarea'], data['scenario_data']['floor_area']['ss_floorarea'], data['service_building_count'], rs_regions_without_floorarea, ss_regions_without_floorarea = data_loader.floor_area_virtual_dw(
            data['regions'],
            data['sectors'],
            data['local_paths'],
            data['scenario_data']['population'][data['assumptions'].base_yr],
            data['assumptions'].base_yr)

        # Add all areas with no floor area data
        data['assumptions'].update("rs_regions_without_floorarea", rs_regions_without_floorarea)
        data['assumptions'].update("ss_regions_without_floorarea", ss_regions_without_floorarea)

    print("Start Energy Demand Model with python version: " + str(sys.version))
    print("-----------------------------------------------")
    print("Number of Regions                        " + str(data['assumptions'].reg_nrs))

    # Obtain population data for disaggregation
    if config['CRITERIA']['msoa_crit']:
        name_population_dataset = data['local_paths']['path_population_data_for_disaggregation_MSOA']
    else:
        name_population_dataset = data['local_paths']['path_population_data_for_disaggregation_lad']
    data['pop_for_disag'] =  data_loader.read_scenario_data(name_population_dataset)

    # ---------------------------------------------
    # Make selection of weather stations and data
    # Load all temperature and weather station data
    # ---------------------------------------------
    data['weather_stations'], data['temp_data'] = data_loader.load_temp_data(
        data['local_paths'],
        sim_yrs=sim_yrs,
        weather_realisation=weather_realisation,
        path_weather_data=path_weather_data,
        same_base_year_weather=False,
        crit_temp_min_max=config['CRITERIA']['crit_temp_min_max'],
        load_np=False,
        load_parquet=False,
        load_csv=True)

    # Plot map with weather station
    '''if config['CRITERIA']['cluster_calc'] != True:
        data_loader.create_weather_station_map(
            data['weather_stations'],
            os.path.join(path_new_scenario, 'weatherst_distr_weathyr.pdf'),
            path_shapefile=data['local_paths']['lad_shapefile'])'''

    # ------------------------------------------------------------
    # Disaggregate national energy demand to regional demands
    # ------------------------------------------------------------
    data['fuel_disagg'] = s_disaggregation.disaggr_demand(
        data,
        crit_temp_min_max=config['CRITERIA']['crit_temp_min_max'],
        spatial_calibration=config['CRITERIA']['spatial_calibration'])

    # ------------------------------------------------------------
    # Calculate spatial diffusion factors
    # ------------------------------------------------------------
    real_values = data['pop_density']
    f_reg, f_reg_norm, f_reg_norm_abs, crit_all_the_same = init_scripts.create_spatial_diffusion_factors(
        narrative_spatial_explicit_diffusion=data['assumptions'].strategy_vars['spatial_explicit_diffusion'],
        fuel_disagg=data['fuel_disagg'],
        regions=data['regions'],
        real_values=real_values,
        narrative_speed_con_max=data['assumptions'].strategy_vars['speed_con_max'])

    print("Criteria all regions the same:           " + str(crit_all_the_same))

    # ------------------------------------------------
    # Calculate parameter values for every region
    # ------------------------------------------------
    regional_vars = init_scripts.spatial_explicit_modelling_strategy_vars(
        data['assumptions'].strategy_vars,
        data['assumptions'].spatially_modelled_vars,
        data['regions'],
        data['fuel_disagg'],
        f_reg,
        f_reg_norm,
        f_reg_norm_abs)
    data['assumptions'].update('strategy_vars', regional_vars)

    # -----------------------------------------------------------------
    # Calculate parameter values for every simulated year based on narratives
    # and add also general information containter for every parameter
    # -----------------------------------------------------------------
    print("... starting calculating values for every year")
    regional_vars, non_regional_vars = s_scenario_param.generate_annual_param_vals(
        data['regions'],
        data['assumptions'].strategy_vars,
        sim_yrs)

    # ------------------------------------------------
    # Calculate switches (not generic)
    # ------------------------------------------------
    try:
        service_switches_raw = pd.read_csv(os.path.join(path_strategy_vars, "switches_service.csv"))
        service_switches = read_data.service_switch(service_switches_raw)
    except:
        service_switches = []

    fuel_switches = read_data.read_fuel_switches(os.path.join(path_strategy_vars, "switches_fuel.csv"), data['enduses'], data['assumptions'].fueltypes, data['assumptions'].technologies)
    capacity_switches = read_data.read_capacity_switch(os.path.join(path_strategy_vars, "switches_capacity.csv"))

    # Load Generic fuel switches
    crit_switch_happening = testing_functions.switch_testing(
        fuel_switches=fuel_switches,
        service_switches=service_switches,
        capacity_switches=capacity_switches)
    data['assumptions'].update('crit_switch_happening', crit_switch_happening)

    print("... starting calculating switches")
    annual_tech_diff_params = init_scripts.switch_calculations(
        sim_yrs,
        data,
        f_reg,
        f_reg_norm,
        f_reg_norm_abs,
        crit_all_the_same,
        service_switches=service_switches,
        fuel_switches=fuel_switches,
        capacity_switches=capacity_switches)

    for region in data['regions']:
        regional_vars[region]['annual_tech_diff_params'] = annual_tech_diff_params[region]

    data['assumptions'].update('regional_vars', regional_vars)
    data['assumptions'].update('non_regional_vars', non_regional_vars)

    # ------------------------------------------------
    # Spatial Validation
    # ------------------------------------------------
    print("AA " + str(data['result_paths']['data_results_validation']))

    if config['CRITERIA']['validation_criteria'] == True and config['CRITERIA']['cluster_calc'] != True:
        lad_validation.spatial_validation_lad_level(
            data['fuel_disagg'],
            data['result_paths']['data_results_validation'],
            data['paths'],
            data['regions'],
            data['reg_coord'],
            config['CRITERIA']['plot_crit'])

    # -----------------------------------
    # Only selection of regions to simulate
    # -------------------------------------
    if config['CRITERIA']['reg_selection']:
        region_selection = read_data.get_region_selection(
            os.path.join(
                data['local_paths']['local_path_datafolder'],
                "region_definitions",
                config['CRITERIA']['reg_selection_csv_name']))
        #region_selection = ['E02003237', 'E02003238']

        setattr(data['assumptions'], 'reg_nrs', len(region_selection))
    else:
        region_selection = data['regions']

    # -------------------------------------------
    # Create .ini file with simulation information
    # -------------------------------------------
    write_data.write_simulation_inifile(
        path_new_scenario,
        data,
        region_selection)

    # Write population data to file
    for sim_yr in data['assumptions'].sim_yrs:
        write_data.write_scenaric_population_data(
            sim_yr,
            os.path.join(path_new_scenario, 'model_run_pop'),
            list(data['scenario_data']['population'][sim_yr].values()))

    # -----------------------
    # Main model run function
    # -----------------------
    for sim_yr in data['assumptions'].sim_yrs:

        print("Local simulation for year:  " + str(sim_yr))
        setattr(data['assumptions'], 'curr_yr', sim_yr) # Set current year
        print("CURRYR: " + str(data['assumptions'].curr_yr))
        if config['CRITERIA']['constant_weather']:
            weather_yr_scenario = config['CONFIG']['weather_yr_scenario']
        else:
            weather_yr_scenario = sim_yr

        # --------------------------------------
        # Update result_paths and create folders
        # --------------------------------------
        path_folder_weather_yr = os.path.join(path_new_scenario, str("simulation_results"))

        data['weather_yr_result_paths'] = basic_functions.get_weather_result_paths(
            path_folder_weather_yr)

        for folder, path_folder in data['weather_yr_result_paths'].items():
            basic_functions.create_folder(path_folder)

        technologies = general_assumptions.update_technology_assumption(
            data['assumptions'].technologies,
            narrative_f_eff_achieved=data['assumptions'].non_regional_vars['f_eff_achieved'][sim_yr],
            narrative_gshp_fraction=data['assumptions'].non_regional_vars['gshp_fraction'][sim_yr],
            crit_narrative_input=False)
        data['assumptions'].technologies.update(technologies)

        # ------------------------------------------
        # Run model
        # -------------------------------------------
        sim_obj = energy_demand_model(
            region_selection,
            data,
            config['CRITERIA'],
            data['assumptions'],
            data['weather_stations'],
            weather_yr=weather_yr_scenario,
            weather_by=data['assumptions'].weather_by)

        # ------------------------------------------------
        # Temporal Validation
        # ------------------------------------------------
        if (config['CRITERIA']['validation_criteria'] == True and sim_yr == data['assumptions'].base_yr) and config['CRITERIA']['cluster_calc'] != True:
            lad_validation.spatio_temporal_val(
                sim_obj.ed_fueltype_national_yh,
                sim_obj.ed_fueltype_regs_yh,
                data['weather_yr_result_paths'],
                data['paths'],
                region_selection,
                data['assumptions'].seasons,
                data['assumptions'].model_yeardays_daytype,
                config['CRITERIA']['plot_crit'])

        # -------------------------------------
        # # Generate YAML file with keynames for `sector_model`
        # -------------------------------------
        if config['CRITERIA']['mode_constrained']:
            supply_results = demand_supply_interaction.constrained_results(
                sim_obj.results_constrained,
                sim_obj.results_unconstrained,
                data['assumptions'].submodels_names,
                data['assumptions'].technologies)
        else:
            supply_results = demand_supply_interaction.unconstrained_results(
                sim_obj.results_unconstrained,
                data['assumptions'].submodels_names)

        # --------------------------
        # Write out all calculations
        # --------------------------
        if config['CRITERIA']['write_txt_additional_results']:
            if config['CRITERIA']['crit_plot_enduse_lp']:

                # Maybe move to result folder in a later step
                path_folder_lp = os.path.join(data['weather_yr_result_paths']['data_results'], 'individual_enduse_lp')
                basic_functions.delete_folder(path_folder_lp)
                basic_functions.create_folder(path_folder_lp)
                winter_week, _, _, _ = date_prop.get_seasonal_weeks()

                # Plot electricity
                fueltype_int_elec = lookup_tables.basic_lookups()['fueltypes']['electricity']
                for enduse, ed_yh in sim_obj.tot_fuel_y_enduse_specific_yh.items():
                    fig_enduse_yh.run(
                        name_fig="individ__electricity_{}_{}".format(enduse, sim_yr),
                        path_result=path_folder_lp,
                        ed_yh=ed_yh[fueltype_int_elec],
                        days_to_plot=winter_week)

            # -------------------------------------------
            # Write annual results to txt files
            # -------------------------------------------
            path_runs = data['weather_yr_result_paths']['data_results_model_runs']

            print("... Start writing results to file: " + str(path_runs))
            plot_only_selection = True
            if plot_only_selection:
                write_data.write_only_peak_total_regional(
                    sim_yr,
                    "only_total",
                    path_runs,
                    sim_obj.ed_fueltype_regs_yh,
                    'tot_fueltype_reg')

                write_data.write_only_peak(
                    sim_yr,
                    "only_peak",
                    path_runs,
                    sim_obj.ed_fueltype_regs_yh,
                    'fueltype_reg_peak_day')

                # PLot only residential total regional annual demand and
                '''write_data.write_residential_tot_demands(
                    sim_yr,
                    path_runs,
                    sim_obj.ed_residential_tot_reg_y,
                    "ed_residential_tot_reg_y")
                write_data.write_supply_results(
                    sim_yr,
                    "ed_fueltype_regs_yh",
                    path_runs,
                    sim_obj.ed_fueltype_regs_yh,
                    "result_tot_submodels_fueltypes")'''
            else:
                write_data.write_residential_tot_demands(
                    sim_yr,
                    path_runs,
                    sim_obj.ed_residential_tot_reg_y,
                    "ed_residential_tot_reg_y")
                write_data.write_supply_results(
                    sim_yr,
                    "ed_fueltype_regs_yh",
                    path_runs,
                    sim_obj.ed_fueltype_regs_yh,
                    "result_tot_submodels_fueltypes")
                write_data.write_enduse_specific(
                    sim_yr,
                    path_runs,
                    sim_obj.tot_fuel_y_enduse_specific_yh,
                    "out_enduse_specific")
                write_data.write_lf(
                    path_runs,
                    "result_reg_load_factor_y",
                    [sim_yr],
                    sim_obj.reg_load_factor_y,
                    'reg_load_factor_y')
                write_data.write_lf(
                    path_runs,
                    "result_reg_load_factor_yd",
                    [sim_yr],
                    sim_obj.reg_load_factor_yd,
                    'reg_load_factor_yd')

            print("... Finished writing results to file")

    print("-------------------------")
    print("... Finished running HIRE")
    print("-------------------------")
