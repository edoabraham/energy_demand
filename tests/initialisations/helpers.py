"""
"""
from energy_demand.initalisations import helpers
from energy_demand.read_write import read_data

def test_init_dict_brackets(): 
    """Test
    """
    first_level_keys = ["a", "b"]
    one_level_dict = helpers.init_dict_brackets(first_level_keys)
    expected = {"a": {}, "b": {}}

    assert one_level_dict == expected

def test_get_nested_dict_key():
    """Test
    """
    nested_dict = {"a": {"c": 1, "d": 3}, "b": {"e": 4}}
    keys = helpers.get_nested_dict_key(nested_dict)
    expected = ["c", "d", "e"]

    assert keys == expected

def test_set_same_eff_all_tech():
    """Test
    """
    eff_to_assign = 0.5
    techs = {"tech_a": {'eff_achieved': 0}}
    techs_eff = helpers.set_same_eff_all_tech(techs)

    expected = {"tech_a": {'eff_achieved': eff_to_assign}}

    assert techs_eff == expected

def set_same_eff_all_tech():

    technologies = {
        'boilerA': read_data.TechnologyData(
            fuel_type='gas',
            eff_by=0.5,
            eff_ey=0.5,
            year_eff_ey=2015,
            eff_achieved=1.0,
            diff_method='linear',
            market_entry=1990,
            tech_max_share=1.0,
            fueltypes={'gas': 1})}

    result = helpers.set_same_eff_all_tech(technologies, tech_eff_achieved_f=0.4)


    result['boilerA'].eff_achieved == 0.4
