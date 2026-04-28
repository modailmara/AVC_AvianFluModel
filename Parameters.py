import configparser

from support_functions import get_scenario_input_dir, get_input_data_dir
from constants import DEFAULT_PARAMETERS_INPUT_FILENAME, FarmHousing, FarmMilkingSystem, \
    SCENARIO_PARAMETERS_INPUT_FILENAME, Cleaning, input_to_role


class Parameters:
    """
    Access to all the parameters for running the model
    """

    def __init__(self, scenario_name=None):

        # read the configuration - default parameters first
        self.config = configparser.ConfigParser()
        param_filepaths = [get_input_data_dir() / DEFAULT_PARAMETERS_INPUT_FILENAME]
        if scenario_name is not None:
            # override with specific parameters for the scenario
            param_filepaths.append(get_scenario_input_dir(scenario_name) / SCENARIO_PARAMETERS_INPUT_FILENAME)
        self.config.read(param_filepaths)

        # ----------------- MODEL ------------
        self.IS_STOP_COMMUNITY_INFECTION = self.config['MODEL'].getboolean('IS_STOP_COMMUNITY_INFECTION')
        self.IS_QUARANTINE_FARM = self.config['MODEL'].getboolean('IS_QUARANTINE_FARM')

        # ----------------- TIME ------------
        self.STEPS_PER_DAY = self.config['TIME'].getint('STEPS_PER_DAY')
        self.DAYTIME_STEPS = self.config['TIME'].getint('DAYTIME_STEPS')
        self.work_day_steps = [step+1 for step in range(self.DAYTIME_STEPS)]

        # ----------------- FARM SERVICE VISITS TO FARMS ------------
        self.EMERGENCY_VISITS_PER_MONTH = self.config['FARM VISITS'].getint('EMERGENCY_VISITS_PER_MONTH')
        # 8 = number of weekend days in a month
        self.emergency_visits_per_step = self.EMERGENCY_VISITS_PER_MONTH / (8 * self.STEPS_PER_DAY)

        # Unscheduled calls that aren't emergencies, should result in 1-2 visits per day in business hours
        self.NON_URGENT_CALLS_PER_DAY = self.config['FARM VISITS'].getfloat('NON_URGENT_CALLS_PER_DAY')
        self.non_urgent_calls_per_step = self.NON_URGENT_CALLS_PER_DAY / self.STEPS_PER_DAY

        self.NUM_TRUCKS = self.config['FARM VISITS'].getint('NUM_TRUCKS')

        self.VET_STEPS_AT_FARM = self.config['FARM VISITS'].getfloat('VET_STEPS_AT_FARM')
        self.VET_CONTACTS_PER_STEP = self.config['FARM VISITS'].getfloat('VET_CONTACTS_PER_STEP')

        self.TRUCK_CONTACTS_PER_STEP = self.config['FARM VISITS'].getfloat('TRUCK_CONTACTS_PER_STEP')

        # maximum number of farms that can be visited in a single trip from the VTH by a farm services clinician
        self.MAX_VISITS_PER_TRIP = self.config['FARM VISITS'].getint('MAX_VISITS_PER_TRIP')

        # number of steps to travel between hospital and farm or between farms
        self.VISIT_TRAVEL_STEPS = self.config['FARM VISITS'].getint('VISIT_TRAVEL_STEPS')

        # ----------------- DISEASE ------------------------------------
        self.NUM_INIT_INFECTED_FARMS = self.config['DISEASE'].getint('NUM_INIT_INFECTED_FARMS')

        self.HUMAN_INFECT_CATTLE_PROB = self.config['DISEASE'].getfloat('HUMAN_INFECT_CATTLE_PROB')
        self.HUMAN_INFECT_HUMAN_PROB = self.config['DISEASE'].getfloat('HUMAN_INFECT_HUMAN_PROB')
        self.CATTLE_INFECT_HUMAN_PROB = self.config['DISEASE'].getfloat('CATTLE_INFECT_HUMAN_PROB')
        self.CATTLE_INFECT_CATTLE_PROB = self.config['DISEASE'].getfloat('CATTLE_INFECT_CATTLE_PROB')
        self.TRUCK_INFECT_CATTLE_PROB = self.config['DISEASE'].getfloat('TRUCK_INFECT_CATTLE_PROB')
        self.CATTLE_INFECT_TRUCK_PROB = self.config['DISEASE'].getfloat('CATTLE_INFECT_TRUCK_PROB')

        # vaccination reduces the probabilities of both being infected and infecting. Only people/humans are vaccinated
        # VACC_ROLES is either None or a comma (,) separated list of the roles of people that are getting vaccinated
        # possible roles are: farmer, farm services vet, farm services technician, farm services student,
        # large animal vet, large animal staff, large animal student, small animal vet, small animal staff,
        # small animal student, floating vet, floating clinician, floating staff, floating student
        self.VACC_ROLES = self.process_vacc_roles(self.config['DISEASE'].get('VACC_ROLES'))

        self.VACC_HUMAN_INFECT_CATTLE_PROB = self.config['DISEASE'].getfloat('VACC_HUMAN_INFECT_CATTLE_PROB')
        self.VACC_CATTLE_INFECT_HUMAN_PROB = self.config['DISEASE'].getfloat('VACC_CATTLE_INFECT_HUMAN_PROB')
        self.VACC_HUMAN_INFECT_HUMAN_PROB = self.config['DISEASE'].getfloat('VACC_HUMAN_INFECT_HUMAN_PROB')
        self.VACC_HUMAN_INFECT_ENV_PROB = self.config['DISEASE'].getfloat('VACC_HUMAN_INFECT_ENV_PROB')
        self.VACC_ENV_INFECT_HUMAN_PROB = self.config['DISEASE'].getfloat('VACC_ENV_INFECT_HUMAN_PROB')

        self.HUMAN_EXPOSED_DAYS = self.config['DISEASE'].getfloat('HUMAN_EXPOSED_DAYS')
        self.human_exposed_steps = self.convert_days_to_steps(self.HUMAN_EXPOSED_DAYS)
        self.HUMAN_INFECTIOUS_DAYS = self.config['DISEASE'].getfloat('HUMAN_INFECTIOUS_DAYS')
        self.human_infectious_steps = self.convert_days_to_steps(self.HUMAN_INFECTIOUS_DAYS)
        self.HUMAN_RECOVERED_DAYS = self.config['DISEASE'].getfloat('HUMAN_RECOVERED_DAYS')
        self.human_recovered_steps = self.convert_days_to_steps(self.HUMAN_RECOVERED_DAYS)

        self.HUMAN_SYMPTOMATIC_DAYS = self.config['DISEASE'].getfloat('HUMAN_SYMPTOMATIC_DAYS')
        self.human_symptomatic_steps = self.convert_days_to_steps(self.HUMAN_SYMPTOMATIC_DAYS)

        self.CATTLE_EXPOSED_DAYS = self.config['DISEASE'].getfloat('CATTLE_EXPOSED_DAYS')
        self.cattle_exposed_steps = self.convert_days_to_steps(self.CATTLE_EXPOSED_DAYS)
        self.CATTLE_INFECTED_DAYS = self.config['DISEASE'].getfloat('CATTLE_INFECTED_DAYS')
        self.cattle_infected_steps = self.convert_days_to_steps(self.CATTLE_INFECTED_DAYS)
        self.CATTLE_RECOVERED_DAYS = self.config['DISEASE'].getfloat('CATTLE_RECOVERED_DAYS')
        self.cattle_recovered_steps = self.convert_days_to_steps(self.CATTLE_RECOVERED_DAYS)

        # environment <-> human infection
        self.ENV_INFECT_HUMAN_PROB = self.config['DISEASE'].getfloat('ENV_INFECT_HUMAN_PROB')
        self.HUMAN_INFECT_ENV_PROB = self.config['DISEASE'].getfloat('HUMAN_INFECT_ENV_PROB')

        # environment <-> cattle interaction
        self.ENV_INFECT_CATTLE_PROB = self.config['DISEASE'].getfloat('ENV_INFECT_CATTLE_PROB')
        self.CATTLE_INFECT_ENV_PROB = self.config['DISEASE'].getfloat('CATTLE_INFECT_ENV_PROB')

        # environment <-> truck interaction
        self.ENV_INFECT_TRUCK_PROB = self.config['DISEASE'].getfloat('ENV_INFECT_TRUCK_PROB')
        self.TRUCK_INFECT_ENV_PROB = self.config['DISEASE'].getfloat('TRUCK_INFECT_ENV_PROB')

        self.ENV_INFECTIOUS_DAYS = self.config['DISEASE'].getfloat('ENV_INFECTIOUS_DAYS')
        self.env_infectious_steps = self.convert_days_to_steps(self.ENV_INFECTIOUS_DAYS)

        # ----------------- COMMUNITY -------------------------------
        self.COMMUNITY_POPULATION = self.config['COMMUNITY'].getfloat('COMMUNITY_POPULATION')
        self.COMMUNITY_CONTACTS_PER_STEP = self.config['COMMUNITY'].getint('COMMUNITY_CONTACTS_PER_STEP')

        # ----------------- FARM -------------------------------
        self.cattle_contacts_per_step = {
            FarmHousing.FREE_STALL: self.config['FARM'].getint('FREE_STALL_CONTACTS_PER_STEP'),
            FarmHousing.TIE_STALL: self.config['FARM'].getint('TIE_STALL_CONTACTS_PER_STEP'),
            FarmHousing.STRAW_PACK: self.config['FARM'].getint('STRAW_PACK_CONTACTS_PER_STEP'),
            FarmHousing.TIE_AND_STRAW: self.config['FARM'].getint('TIE_AND_STRAW_CONTACTS_PER_STEP')
        }

        self.NUM_MILKING_EVENTS_PER_DAY = self.config['FARM'].getint('NUM_MILKING_EVENTS_PER_DAY')

        # number of contacts cow<->farmer at each milking event
        self.num_milking_contacts = {
            FarmMilkingSystem.PARLOUR: self.config['FARM'].getint('PARLOUR_MILKING_CONTACTS'),
            FarmMilkingSystem.AMS: self.config['FARM'].getint('AMS_MILKING_CONTACTS'),
            FarmMilkingSystem.PIPELINE: self.config['FARM'].getint('PIPELINE_MILKING_CONTACTS'),
            FarmMilkingSystem.ROTARY_PARLOUR: self.config['FARM'].getint('ROTARY_PARLOUR_MILKING_CONTACTS')
        }

        # ----------------- CLEANING -------------------------------
        self.TRUCK_CLEANING_SCHEDULE = self.process_cleaning_schedule(
            self.config['CLEANING'].get('TRUCK_CLEANING_SCHEDULE')
        )

        self.HOSPITAL_CLEANING_SCHEDULE = self.process_cleaning_schedule(
            self.config['CLEANING'].get('HOSPITAL_CLEANING_SCHEDULE')
        )

        # ----------------- PEOPLE -------------------------------
        self.SHEET_NAME = self.config['PEOPLE'].get('SHEET_NAME').strip().lower()

    # ---------------------------------------------------------
    # useful functions

    def convert_per_day_to_per_step(self, num_per_day):
        """
        Converts a number of events per day into a number of events per step. Rounds to the nearest integer.

        :param num_per_day: Number of events per day
        :type num_per_day: int
        :return: Number of events per step
        :rtype: int
        """
        return max(1, round(num_per_day / self.STEPS_PER_DAY))

    def convert_days_to_steps(self, num_days):
        """
        Converts a number of days into a number of steps. Rounds to the nearest integer.

        :param num_days: Number of days to convert
        :type num_days: numeric
        :return: Number of model steps
        :rtype: int
        """
        return round(num_days * self.STEPS_PER_DAY)

    @staticmethod
    def process_vacc_roles(input_string):
        """
        Turns a comma separated string list of roles specifying VACC_ROLES. Returns a list of enumerationg values.
        :param input_string: Comma separated list of model people roles
        :type input_string: str
        :return: List of enumeration values for the input roles
        :rtype: list
        """
        role_input_list = [role.strip().lower() for role in input_string.split(',')]
        enum_roles = []
        for role_input in role_input_list:
            if role_input in input_to_role:
                enum_roles.append(input_to_role[role_input])

        return enum_roles

    @staticmethod
    def process_cleaning_schedule(cleaning_string):
        cleaning_string = cleaning_string.strip().lower()
        if cleaning_string == 'daily':
            cleaning_schedule = Cleaning.DAILY
        elif cleaning_string == 'visit':
            cleaning_schedule = Cleaning.VISIT
        else:
            # default to none on any other input
            cleaning_schedule = Cleaning.NONE
        return cleaning_schedule