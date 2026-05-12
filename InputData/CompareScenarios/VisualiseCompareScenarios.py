"""
Visualises the scenario comparison.

Produces a figure like the individual scenarios but comparing different scenarios with one value each
 - box and whisker plot for time to first community exposure
 - line (95% CI) plot with community infection proportion
 - upset plots for transmissions between agents
"""
import pandas as pd
import seaborn as sns

from support_functions import get_output_data_dir, get_input_data_dir
from constants import PersonRole
from InputData.scenario_constants import NUM_ITERATIONS
from VisualiseResults import create_scenario_figure, count_transmissions

SCENARIO_NAME = "CompareScenarios"
# dict of tuples {full condition name: (chart condition name, how it appears in the network connection file), ... }
CONDITION_DICT = {
    'baseline': 'Baseline',
    'quarantine + vaccinate farmers': 'Q - V_farmers',
    'vaccinate farmers + FS clinicians': 'V_farmers+FSclinicians',
    'vaccinate farmers + FS clinicians and disinfect trucks and close common areas':
        'V_farmers+FSclinicians\nclean Trucks - no common',
}
CONDITION_PARAMS_DICT = {
    'baseline': 'baseline',
    'quarantine + vaccinate farmers': 'IS_QUARANTINE_FARM-True_VACC_ROLES-farmer',
    'vaccinate farmers + FS clinicians': 'VACC_ROLES-farmer, farm services clinician',
    'vaccinate farmers + FS clinicians and disinfect trucks and close common areas':
        'VACC_ROLES-farmer, farm services clinician_TRUCK_CLEANING_SCHEDULE-visit_SHEET_NAME-no_common',
}


def main():
    scenario_name = "CompareScenarios"

    print('Visualising scenario: {}'.format(scenario_name))

    # run the visualisation
    scenario_df = pd.read_csv(get_output_data_dir(scenario_name) / '{}_data-{}.csv'.format(scenario_name,
                                                                                           NUM_ITERATIONS))
    scenario_df.replace(to_replace=CONDITION_DICT, inplace=True)
    condition_long = []
    condition_short = []
    condition_filename = []
    for key, value in CONDITION_DICT.items():
        condition_long.append(key)
        condition_short.append(value)
        condition_filename.append(CONDITION_PARAMS_DICT[key])

    create_scenario_figure(scenario_df, scenario_name, 'condition', condition_short,
                           var_long_values=condition_long, var_filename_values=condition_filename)

    # count_transmissions(scenario_name, 'condition', condition_short)


if __name__ == "__main__":
    main()
