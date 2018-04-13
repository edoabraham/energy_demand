"""Weather Region: Depending on the number of weather stations, a ``WeatherRegion``
is generated per weather station. Within this regions,
regional load profiles are calculated."""
import uuid
import numpy as np
import logging
from energy_demand.technologies import technological_stock
from energy_demand.profiles import load_profile
from energy_demand.profiles import hdd_cdd
from energy_demand.technologies import diffusion_technologies
from energy_demand.basic import basic_functions
from energy_demand.enduse_func import get_peak_day_single_fueltype

class WeatherRegion(object):
    """WeaterRegion

    Arguments
    ----------
    name : str
        Unique identifyer of weather region
    base_yr : int
        Base year
    curr_yr : int
        Current year
    assumptions : dict
        Assumptions
    fueltypes : dict
        fueltypes
    all_enduse : list
        All enduses
    temp_by, temp_ey : array
        Temperature data
    tech_lp : dict
        Technology load profiles
    sectors : list
        Sectors

    Note
    ----
    - For each region, a technology stock is defined
    - regional specific fuel shapes are assigned to technologies
    """
    def __init__(
            self,
            name,
            base_yr,
            curr_yr,
            strategy_variables,
            t_bases,
            t_diff_param,
            tech_lists,
            technologies,
            assumptions,
            fueltypes,
            model_yeardays_nrs,
            model_yeardays,
            yeardays_month_days,
            all_enduses,
            temp_by,
            tech_lp,
            sectors,
        ):
        """Constructor of weather region
        """
        self.name = name

        # -----------------------------------
        # Calculate current year temperatures
        # -----------------------------------
        temp_cy = change_temp_climate(
            temp_by,
            yeardays_month_days,
            strategy_variables,
            base_yr,
            curr_yr)

        # Change base temperatures depending on change in t_base
        rs_t_base_heating_cy = hdd_cdd.sigm_temp(
            strategy_variables['rs_t_base_heating_future_yr']['scenario_value'],
            t_bases.rs_t_heating_by,
            base_yr,
            curr_yr,
            t_diff_param)
        '''rs_t_base_cooling_cy = hdd_cdd.sigm_temp(
            strategy_variables['rs_t_base_cooling_future_yr']['scenario_value'],
            t_bases.rs_t_cooling_by, base_yr, curr_yr,
            t_diff_param)'''

        ss_t_base_heating_cy = hdd_cdd.sigm_temp(
            strategy_variables['ss_t_base_heating_future_yr']['scenario_value'],
            t_bases.ss_t_heating_by,
            base_yr,
            curr_yr,
            t_diff_param)
        ss_t_base_cooling_cy = hdd_cdd.sigm_temp(
            strategy_variables['ss_t_base_cooling_future_yr']['scenario_value'],
            t_bases.ss_t_cooling_by,
            base_yr,
            curr_yr,
            t_diff_param)

        is_t_base_heating_cy = hdd_cdd.sigm_temp(
            strategy_variables['is_t_base_heating_future_yr']['scenario_value'],
            t_bases.is_t_heating_by,
            base_yr,
            curr_yr,
            t_diff_param)
        '''is_t_base_cooling_cy = hdd_cdd.sigm_temp(
            strategy_variables['is_t_base_cooling_future_yr']['scenario_value'],
            t_bases.is_t_cooling_by,
            base_yr,
            curr_yr,
            t_diff_param)'''

        # -------------------
        # Technology stocks
        # -------------------
        self.rs_tech_stock = technological_stock.TechStock(
            'rs_tech_stock',
            technologies,
            assumptions.enduse_overall_change['other_enduse_mode_info'],
            base_yr,
            curr_yr,
            fueltypes,
            temp_by,
            temp_cy,
            t_bases.rs_t_heating_by,
            all_enduses['rs_enduses'],
            rs_t_base_heating_cy,
            assumptions.rs_specified_tech_enduse_by)

        self.ss_tech_stock = technological_stock.TechStock(
            'ss_tech_stock',
            technologies,
            assumptions.enduse_overall_change['other_enduse_mode_info'],
            base_yr,
            curr_yr,
            fueltypes,
            temp_by,
            temp_cy,
            t_bases.ss_t_heating_by,
            all_enduses['ss_enduses'],
            ss_t_base_heating_cy,
            assumptions.ss_specified_tech_enduse_by)

        self.is_tech_stock = technological_stock.TechStock(
            'is_tech_stock',
            technologies,
            assumptions.enduse_overall_change['other_enduse_mode_info'],
            base_yr,
            curr_yr,
            fueltypes,
            temp_by,
            temp_cy,
            t_bases.is_t_heating_by,
            all_enduses['is_enduses'],
            ss_t_base_heating_cy,
            assumptions.is_specified_tech_enduse_by)

        # -------------------
        # Residential Load profiles
        # ------------------
        self.rs_load_profiles = load_profile.LoadProfileStock("rs_load_profiles")

        # --------Calculate HDD/CDD
        self.rs_hdd_by, _ = hdd_cdd.calc_reg_hdd(
            temp_by, t_bases.rs_t_heating_by, model_yeardays)
        self.rs_hdd_cy, rs_fuel_shape_heating_yd = hdd_cdd.calc_reg_hdd(
            temp_cy, rs_t_base_heating_cy, model_yeardays)
        #self.rs_cdd_by, _ = hdd_cdd.calc_reg_cdd(
        #    temp_by, t_bases.rs_t_cooling_by, model_yeardays)
        #self.rs_cdd_cy, rs_fuel_shape_cooling_yd = hdd_cdd.calc_reg_cdd(
        #    temp_cy, rs_t_base_cooling_cy, model_yeardays)

        # -------Calculate climate change correction factors
        try:
            self.f_heat_rs_y = np.nan_to_num(
                1.0 / float(np.sum(self.rs_hdd_by))) * np.sum(self.rs_hdd_cy)
            #self.f_cooling_rs_y = np.nan_to_num(
            #    1.0 / float(np.sum(self.rs_cdd_by))) * np.sum(self.rs_cdd_cy)
            self.f_cooling_rs_y = 1
        except ZeroDivisionError:
            self.f_heat_rs_y = 1
            self.f_cooling_rs_y = 1

        # yd peak factors for heating and cooling
        rs_peak_yd_heating_factor = get_shape_peak_yd_factor(self.rs_hdd_cy)

        '''
        # RESIDENITAL COOLING
        #rs_peak_yd_cooling_factor = get_shape_peak_yd_factor(self.rs_cdd_cy)
        rs_cold_techs = tech_lists['rs_cold']
        rs_cold_techs.append('placeholder_tech')

        # ----Cooling residential
        #rs_fuel_shape_cooling_yh = load_profile.calc_yh(
        #    rs_fuel_shape_cooling_yd, tech_lp['rs_shapes_cooling_dh'], model_yeardays)
        #or also (if only yd)
        #shape_yh=tech_lp['rs_shapes_dh'][cooling_enduse]['shape_non_peak_y_dh'] * ss_fuel_shape_coolin_yd[:, np.newaxis],
        rs_fuel_shape_cooling_yh = self.get_shape_cooling_yh(data, rs_fuel_shape_cooling_yd, 'rs_shapes_cooling_dh')

        for cooling_enduse in assumptions.enduse_rs_space_cooling:
            self.rs_load_profiles.add_lp(
                unique_identifier=uuid.uuid4(),
                technologies=rs_cold_techs,
                enduses=enduse, #['rs_cooling'],
                shape_yd=rs_fuel_shape_cooling_yd,
                shape_yh=rs_fuel_shape_cooling_yh,
                f_peak_yd=rs_peak_yd_cooling_factor)
        '''
        # ------Heating boiler
        rs_profile_boilers_yh = load_profile.calc_yh(
            rs_fuel_shape_heating_yd, tech_lp['rs_profile_boilers_y_dh'], model_yeardays)

        self.rs_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=tech_lists['heating_const'],
            enduses=['rs_space_heating', 'rs_water_heating'],
            shape_yd=rs_fuel_shape_heating_yd,
            shape_yh=rs_profile_boilers_yh,
            f_peak_yd=rs_peak_yd_heating_factor)

        # ------Heating CHP 
        rs_profile_chp_yh = load_profile.calc_yh(
            rs_fuel_shape_heating_yd, tech_lp['rs_profile_chp_y_dh'], model_yeardays)

        self.rs_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=tech_lists['tech_CHP'],
            enduses=['rs_space_heating', 'rs_water_heating'],
            shape_yd=rs_fuel_shape_heating_yd,
            shape_yh=rs_profile_chp_yh,
            f_peak_yd=rs_peak_yd_heating_factor)

        # ------Electric heating, storage heating (primary)
        rs_profile_storage_heater_yh = load_profile.calc_yh(
            rs_fuel_shape_heating_yd, tech_lp['rs_profile_storage_heater_y_dh'], model_yeardays)
        self.rs_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=tech_lists['storage_heating_electricity'],
            enduses=['rs_space_heating', 'rs_water_heating'],
            shape_yd=rs_fuel_shape_heating_yd,
            shape_yh=rs_profile_storage_heater_yh,
            f_peak_yd=rs_peak_yd_heating_factor)

        # ------Electric heating secondary (direct elec heating)
        rs_profile_elec_heater_yh = load_profile.calc_yh(
            rs_fuel_shape_heating_yd, tech_lp['rs_profile_elec_heater_y_dh'], model_yeardays)
        self.rs_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=tech_lists['secondary_heating_electricity'],
            enduses=['rs_space_heating', 'rs_water_heating'],
            shape_yd=rs_fuel_shape_heating_yd,
            shape_yh=rs_profile_elec_heater_yh,
            f_peak_yd=rs_peak_yd_heating_factor)

        # ------Heat pump heating
        rs_fuel_shape_hp_yh, _ = get_fuel_shape_heating_hp_yh(
            tech_lp['rs_profile_hp_y_dh'],
            self.rs_tech_stock,
            self.rs_hdd_cy,
            model_yeardays)

        self.rs_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=tech_lists['heating_non_const'],
            enduses=['rs_space_heating', 'rs_water_heating'],
            shape_yd=rs_fuel_shape_heating_yd,
            shape_yh=rs_fuel_shape_hp_yh,
            f_peak_yd=rs_peak_yd_heating_factor)

        # ------District_heating_electricity --> Assumption made that same curve as CHP
        rs_profile_chp_y_dh = load_profile.calc_yh(
            rs_fuel_shape_heating_yd, tech_lp['rs_profile_chp_y_dh'], model_yeardays)

        self.rs_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=tech_lists['tech_district_heating'],
            enduses=['rs_space_heating', 'rs_water_heating'],
            shape_yd=rs_fuel_shape_heating_yd,
            shape_yh=rs_profile_chp_y_dh,
            f_peak_yd=rs_peak_yd_heating_factor)

        '''
        # --------------------------------------------
        # Calculate load profile for hybrid technology
        # --------------------------------------------
        # ---
        # 1. Calculate share of technology use for every hour (service_distr_hybrid_h_p)
        # 2. Multiply service_distr_hybrid_h_p with heat demand (approximated by boiler shape)
        # 3. Calculate % of service of tech tech (p_tech_low, p_tech_high)
        # 4. Normalise this to obtain shape of each tech (lp_low_temp, lp_high_temp)
        # 
        #   To calculate fuel of tech_low:
        #   fuel_tech_low = total service * p_tech_low * lp_low_temp
        # -----------
        hybrid_cutoff_temp_low = 5
        hybrid_cutoff_temp_high = 8
        tech_temp_low = 'boiler_gas'
        tech_temp_lowtemp_high = 'heat_pumps_electricity'

        # Get fraction of service for hybrid technologies for every hour
        service_distr_hybrid_h_p = service_hybrid_tech_low_high_h_p(
            temp_cy,
            hybrid_cutoff_temp_low,
            hybrid_cutoff_temp_high)

        # Calculate service shares by multiplying fractions for every hour with service
        p_tech_low = service_distr_hybrid_h_p['low'] * rs_profile_boilers_yh
        p_tech_high = service_distr_hybrid_h_p['high'] * rs_profile_boilers_yh

        # Share of service
        p_tech_low_service = np.sum(p_tech_low)
        p_tech_high_service = np.sum(p_tech_high)

        # Normalise to get hybrid shapes (Create load profiles of hybrid_gas and hybrid_elec)
        lp_low_temp = p_tech_low / np.sum(p_tech_low)

        #Boiler tech lp
        lp_low_temp = lp_low_temp

        #Hybrid tech lp
        hp_hybrid_service = p_tech_high * rs_fuel_shape_hp_yh
        lp_high_temp = hp_hybrid_service / np.sum(hp_hybrid_service)

        # Hybrid boiler profile
        self.rs_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=['combined_boiler_hp_system_tech_hybrid_low_temp'],
            enduses=['rs_space_heating'],
            shape_yd=rs_fuel_shape_heating_yd,
            shape_yh=lp_low_temp)

        # Hybrid heat pump profile
        self.rs_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=['combined_boiler_hp_system_tech_hybrid_high_temp'],
            enduses=['rs_space_heating'],
            shape_yd=rs_fuel_shape_heating_yd,
            shape_yh=lp_high_temp)

        '''
        #from energy_demand.plotting import plotting_results
        #logging.info(service_distr_hybrid_h_p['low'][12])
        #logging.info("_---")
        #logging.info(service_distr_hybrid_h_p['high'][12])
        #plotting_results.plot_lp_dh_SCRAP(lp_low_temp[12])
        #plotting_results.plot_lp_dh_SCRAP(lp_high_temp[12])

        '''# Get heat pumps and add same properties but with different name
        tech_hp_hybrid = self.rs_tech_stock.get_tech('heat_pumps_hybrid_electricity', 'rs_space_heating')
        tech_hp_hybrid.set_tech_attr('share_service', p_tech_high_service)
        tech_hp_hybrid.set_tech_attr('tech_type', 'hybrid_tech')
        tech_boiler_hybrid = self.rs_tech_stock.get_tech('boiler_hybrid_gas', 'rs_space_heating')
        tech_boiler_hybrid.set_tech_attr('share_service', p_tech_low_service)
        #self.rs_tech_stock.add_tech('heat_pumps_electricity_hybrid', 'rs_space_heating', tech_hp_hybrid)
        #self.rs_tech_stock.add_tech('boiler_gas_hybrid', 'rs_space_heating', tech_boiler_hybrid)
        # ---------------------
        #TODO ONLY UPDATE NOT CREATE NEW
        hybrid_tech = technological_stock.HybridTech(
            name='combined_boiler_hp_system',
            share_service_low=p_tech_low_service,
            share_service_high=p_tech_high_service,
            tech_hybrid_low_temp=self.rs_tech_stock.get_tech('boiler_gas', 'rs_space_heating'),
            tech_hybrid_high_temp=self.rs_tech_stock.get_tech('heat_pumps_electricity', 'rs_space_heating'))

        self.rs_tech_stock.add_tech(hybrid_tech.name, 'rs_space_heating', hybrid_tech)
        '''
        # -------------------
        # Service Load profiles
        # ------------------
        self.ss_load_profiles = load_profile.LoadProfileStock("ss_load_profiles")

        # --------HDD/CDD
        ss_hdd_by, _ = hdd_cdd.calc_reg_hdd(
            temp_by, t_bases.ss_t_heating_by, model_yeardays)
        ss_hdd_cy, ss_fuel_shape_heating_yd = hdd_cdd.calc_reg_hdd(
            temp_cy, ss_t_base_heating_cy, model_yeardays)

        ss_cdd_by, _ = hdd_cdd.calc_reg_cdd(
            temp_by, t_bases.ss_t_cooling_by, model_yeardays)
        ss_cdd_cy, ss_fuel_shape_coolin_yd = hdd_cdd.calc_reg_cdd(
            temp_cy, ss_t_base_cooling_cy, model_yeardays)

        try:
            self.f_heat_ss_y = np.nan_to_num(
                1.0 / float(np.sum(ss_hdd_by))) * np.sum(ss_hdd_cy)
            self.f_cooling_ss_y = np.nan_to_num(
                1.0 / float(np.sum(ss_cdd_by))) * np.sum(ss_cdd_cy)
        except ZeroDivisionError:
            self.f_heat_ss_y = 1
            self.f_cooling_ss_y = 1

        # ----------------------------------------------
        # Apply weekend correction factor fo ss heating
        # ----------------------------------------------
        ss_peak_yd_heating_factor = get_shape_peak_yd_factor(ss_hdd_cy)
        ss_peak_yd_cooling_factor = get_shape_peak_yd_factor(ss_cdd_cy)

        # --Heating technologies for service sector
        #
        # (the heating shape follows the gas shape of aggregated sectors)
        # meaning that for all technologies, the load profile is the same
        ss_fuel_shape_any_tech, ss_fuel_shape = ss_get_sector_enduse_shape(
            tech_lp['ss_all_tech_shapes_dh'],
            ss_fuel_shape_heating_yd,
            'ss_space_heating',
            model_yeardays_nrs)

        # Apply correction factor for weekend_effect
        # ------
        ss_fuel_shape_heating_yd = ss_fuel_shape_heating_yd * assumptions.ss_weekend_f
        ss_fuel_shape_heating_yd_weighted = load_profile.abs_to_rel(ss_fuel_shape_heating_yd)
        # ------

        # Flatten list of all potential technologies
        ss_space_heating_tech_lists = list(tech_lists.values())
        all_techs_ss_space_heating = [item for sublist in ss_space_heating_tech_lists for item in sublist]

        # ----------------
        # Get peak day and calculate peak load profile for peak day
        # ----------------
        #peak_day = get_peak_day_single_fueltype(ss_fuel_shape)
        #ss_space_heating_shape_peak_dh = load_profile.abs_to_rel(ss_fuel_shape[peak_day])

        self.ss_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=all_techs_ss_space_heating,
            enduses=['ss_space_heating'],
            sectors=sectors['ss_sectors'],
            shape_yd=ss_fuel_shape_heating_yd_weighted,
            shape_yh=ss_fuel_shape_any_tech,
            f_peak_yd=ss_peak_yd_heating_factor)

        #------
        # Add cooling technologies for service sector
        #------
        coolings_techs = tech_lists['cooling_const']

        for cooling_enduse in assumptions.ss_enduse_space_cooling:
            for sector in sectors['ss_sectors']:

                # Apply correction factor for weekend_effect 'cdd_weekend_cfactors'
                ss_fuel_shape_coolin_yd = ss_fuel_shape_coolin_yd * assumptions.cdd_weekend_cfactors
                ss_fuel_shape_coolin_yd = load_profile.abs_to_rel(ss_fuel_shape_coolin_yd)

                # Ev auch tech_lp['ss_shapes_cooling_dh']
                ss_shape_yh = load_profile.calc_yh(
                    ss_fuel_shape_coolin_yd,
                    tech_lp['ss_profile_cooling_y_dh'], model_yeardays)

                self.ss_load_profiles.add_lp(
                    unique_identifier=uuid.uuid4(),
                    technologies=coolings_techs,
                    enduses=[cooling_enduse],
                    sectors=[sector],
                    shape_yd=ss_fuel_shape_coolin_yd,
                    shape_yh=ss_shape_yh,
                    f_peak_yd=ss_peak_yd_cooling_factor)

        # --------------------------------
        # Industry submodel
        # --------------------------------
        self.is_load_profiles = load_profile.LoadProfileStock("is_load_profiles")

        # --------HDD/CDD
        is_hdd_by, _ = hdd_cdd.calc_reg_hdd(
            temp_by, t_bases.is_t_heating_by, model_yeardays)
        #is_cdd_by, _ = hdd_cdd.calc_reg_cdd(
        #    temp_by, t_bases.is_t_cooling_by, model_yeardays)

        # Take same base temperature as for service sector
        is_hdd_cy, is_fuel_shape_heating_yd = hdd_cdd.calc_reg_hdd(
            temp_cy, is_t_base_heating_cy, model_yeardays)
        #is_cdd_cy, _ = hdd_cdd.calc_reg_cdd(
        #    temp_cy, ss_t_base_cooling_cy, model_yeardays)

        try:
            self.f_heat_is_y = np.nan_to_num(1.0 / float(np.sum(is_hdd_by))) * np.sum(is_hdd_cy)
            #self.f_cooling_is_y = np.nan_to_num(1.0 / float(np.sum(is_cdd_by))) * np.sum(is_cdd_cy)
            self.f_cooling_is_y = 1
        except ZeroDivisionError:
            self.f_heat_is_y = 1
            self.f_cooling_is_y = 1

        is_peak_yd_heating_factor = get_shape_peak_yd_factor(is_hdd_cy)
        #is_peak_yd_cooling_factor = self.get_shape_peak_yd_factor(is_cdd_cy)

        # Cooling for industrial enduse
        # --Heating technologies for service sector (the heating shape follows
        # the gas shape of aggregated sectors)

        # Flatten list of all potential heating technologies
        is_space_heating_tech_lists = list(tech_lists.values())
        all_techs_is_space_heating = [item for sublist in is_space_heating_tech_lists for item in sublist]

        # Apply correction factor for weekend_effect for space heating load profile
        is_fuel_shape_heating_yd = is_fuel_shape_heating_yd * assumptions.is_weekend_f
        is_fuel_shape_heating_yd = load_profile.abs_to_rel(is_fuel_shape_heating_yd)

        # Y_dh Heating profile is taken from service sector
        is_fuel_shape_any_tech, _ = ss_get_sector_enduse_shape(
            tech_lp['ss_all_tech_shapes_dh'],
            is_fuel_shape_heating_yd,
            'ss_space_heating',
            assumptions.model_yeardays_nrs)

        # Alternatively generate y_dh flat profile
        #from energy_demand.profiles import generic_shapes
        # _, shape_peak_yd_factor, shape_non_peak_yd, shape_non_peak_yh = generic_shapes.flat_shape(
        #    assumptions.model_yeardays_nrs)
        #flat_is_fuel_shape_any_tech = np.full((assumptions.model_yeardays_nrs, 24), (1.0/24.0), dtype=float)
        #flat_is_fuel_shape_any_tech = flat_is_fuel_shape_any_tech * is_fuel_shape_heating_yd[:, np.newaxis]

        self.is_load_profiles.add_lp(
            unique_identifier=uuid.uuid4(),
            technologies=all_techs_is_space_heating,
            enduses=['is_space_heating'],
            sectors=sectors['is_sectors'],
            shape_yd=is_fuel_shape_heating_yd,
            shape_yh=is_fuel_shape_any_tech, #flat_is_fuel_shape_any_tech,
            f_peak_yd=is_peak_yd_heating_factor)

def get_shape_peak_yd_factor(demand_yd):
    """From yd shape calculate maximum relative yearly service demand
    which is provided in a day

    Arguments
    ----------
    demand_yd : shape
        Demand for energy service for every day in year

    Return
    ------
    max_factor_yd : float
        yd maximum factor

    Note
    -----
    If the shape is taken from heat and cooling demand the assumption is made that
    HDD and CDD are directly proportional to fuel usage
    """
    # Total yearly demand
    tot_demand_y = np.sum(demand_yd)

    # Maximum daily demand
    max_demand_d = np.max(demand_yd)

    max_factor_yd = max_demand_d / tot_demand_y

    return max_factor_yd

def get_fuel_shape_heating_hp_yh(tech_lp_y_dh, tech_stock, rs_hdd_cy, model_yeardays):
    """Convert daily shapes to houly based on load for heatpump

    This is for non-peak.

    Arguments
    ---------
    tech_lp_y_dh : dict
        Technology load profiles
    tech_stock : object
        Technology stock
    rs_hdd_cy : array
        Heating Degree Days (model_yeardays_nrs, 1)
    model_yeardays : array
        Modelled year days

    Returns
    -------
    shape_yh : array
        Yearly shape to calculate hourly load (total sum == 1)
    shape_y_dh : array
        Shape of fuel shape for every day in a year (total sum = nr_of_days)

    Note
    ----
    -  An average heat pump efficiency is calculated for the whole day
       depending on hourly temperatures.

    -  See XY in documentation for source of heat pumps
    """
    shape_yh_hp = np.zeros((365, 24), dtype=float)
    shape_y_dh = np.zeros((365, 24), dtype=float)

    tech_eff = tech_stock.get_tech_attr(
        'rs_space_heating',
        'heat_pumps_electricity',
        'eff_cy')

    # Convert daily service demand to fuel (fuel = Heat demand / efficiency)
    # As only the shape is of interest, the HDD
    # can be used as an indicator for fuel use (which correlates) directly
    hp_daily_fuel = rs_hdd_cy[:, np.newaxis] / tech_eff

    # Distribute daily according to fuel load curves of heat pumps
    shape_yh_hp = hp_daily_fuel * tech_lp_y_dh

    # Convert absolute hourly fuel demand to relative fuel demand within a year
    shape_yh = load_profile.abs_to_rel(shape_yh_hp)

    # Convert for every day the shape to absolute shape (tot sum for a full year == 365)
    _shape_y_dh_sum_rows = np.sum(shape_yh_hp, axis=1)

    with np.errstate(divide='ignore', invalid='ignore'):
        shape_y_dh = shape_yh_hp / _shape_y_dh_sum_rows[:, np.newaxis]
    shape_y_dh[np.isnan(shape_y_dh)] = 0

    # Select only modelled days
    return shape_yh[[model_yeardays]], shape_y_dh[[model_yeardays]]

def get_shape_cooling_yh(tech_shape, cooling_shape):
    """Convert daily shape to hourly

    Arguments
    ---------
    tech_shape : dict
        Technology shape
    cooling_shape : array
        Cooling profile

    Returns
    -------
    shape_yd_cooling_tech : array
        Shape of cooling devices

    Note
    ----
    The daily cooling demand (calculated with cdd) is distributed within the day
    fuel demand curve from:

    - **Residential**: Taken from *Denholm, P., Ong, S., & Booten, C. (2012).
        Using Utility Load Data to Estimate Demand for Space Cooling and
        Potential for Shiftable Loads, (May), 23.
        Retrieved from http://www.nrel.gov/docs/fy12osti/54509.pdf*

    - **Service**: *Knight, Dunn, Environments Carbon and Cooling in
        Uk Office Environments*
    """
    shape_yd_cooling_tech = tech_shape * cooling_shape[:, np.newaxis]

    return shape_yd_cooling_tech

def ss_get_sector_enduse_shape(tech_lps, heating_lp_yd, enduse, model_yeardays_nrs):
    """Read generic shape for all technologies in a service sector enduse

    Arguments
    ---------
    tech_lps : array
        Technology load profiles
    heating_lp_yd : array
        Daily (yd) service demand shape for heat (percentage of yearly
        heat demand for every day)
    enduse : str
        Enduse where technology is used
    model_yeardays_nrs : int
        Number of modelled yeardays

    Returns
    -------
    shape_boilers_yh : array
        Shape how yearly fuel can be distributed to hourly (yh) (total sum == 1)
    shape_boilers_y_dh : array
        Shape of distribution of fuel within every day of a year (total sum == nr_of_days)
    """
    shape_yh_generic_tech = np.zeros((model_yeardays_nrs, 24), dtype=float)

    if enduse not in tech_lps:
        pass
    else:
        shape_y_dh_generic_tech = tech_lps[enduse]['shape_non_peak_y_dh']
        shape_yh_generic_tech = heating_lp_yd[:, np.newaxis] * shape_y_dh_generic_tech

    return shape_yh_generic_tech, shape_y_dh_generic_tech

def change_temp_climate(
        temp_data,
        yeardays_month_days,
        strategy_variables,
        base_yr,
        curr_yr
    ):
    """Change temperature data for every year depending
    on simple climate change assumptions

    Arguments
    ---------
    temp_data : dict
        Data
    yeardays_month_days : dict
        Month containing all yeardays
    strategy_variables : dict
        Assumption on temperature change
    base_yr : int
        Base year
    curr_yr : int
        Current year

    Returns
    -------
    temp_climate_change : dict
        Adapted temperatures for all weather stations depending on climate change assumptions
    """
    temp_climate_change = np.zeros((365, 24), dtype=float)

    # Iterate every month
    for yearday_month, month_yeardays in yeardays_month_days.items():
        month_str = basic_functions.get_month_from_int(yearday_month + 1)
        param_name_month = "climate_change_temp_d__{}".format(month_str)

        # Calculate monthly change in temperature
        lin_diff_factor = diffusion_technologies.linear_diff(
            base_yr=base_yr,
            curr_yr=curr_yr,
            value_start=0,
            value_end=strategy_variables[param_name_month]['scenario_value'],
            yr_until_changed=strategy_variables['climate_change_temp_diff_yr_until_changed']['scenario_value'])

        temp_climate_change[month_yeardays] = temp_data[month_yeardays] + lin_diff_factor

    return temp_climate_change

def service_hybrid_tech_low_high_h_p(temp_cy, hybrid_cutoff_temp_low, hybrid_cutoff_temp_high):
    """Calculate fraction of service for every hour within each hour

    Arguments
    ----------
    temp_cy : array
        Temperature of current year
    hybrid_cutoff_temp_low : int
        Temperature cut-off criteria (blow this temp, 100% service provided by lower temperature technology)
    hybrid_cutoff_temp_high : int
        Temperature cut-off criteria (above this temp, 100% service provided by higher temperature technology)

    Return
    ------
    tech_low_high_p : dict
        Share of lower and higher service fraction for every hour

    Note
    -----
            Within every hour the fraction of service provided by the low-temp technology
    and the high-temp technology is calculated
    """
    tech_low_high_p = {}

    # Substract cutoff temperature from yh temp
    hybrid_service_temp_range = hybrid_cutoff_temp_high - hybrid_cutoff_temp_low
    fast_factor = np.divide(1.0, (hybrid_service_temp_range))

    # Calculate service share (interpolate linearly)
    service_high_tech_p_FAST = fast_factor * (temp_cy - hybrid_cutoff_temp_low)

    # Set service share to 1.0
    service_high_tech_p_FAST[temp_cy > hybrid_cutoff_temp_high] = 1.0

    # Set service share to 0.0
    service_high_tech_p_FAST[temp_cy < hybrid_cutoff_temp_low] = 0.0

    # Technology split for every hour
    tech_low_high_p['low'] = 1.0 - service_high_tech_p_FAST
    tech_low_high_p['high'] = service_high_tech_p_FAST

    return tech_low_high_p
