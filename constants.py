"""
Constants about behaviour of agents and disease epidemiology.

Enum classes for the state-transition models

Info from "Reilly Comper" <reillycomper@trentu.ca>
---------------------------------------------------
Import
Infection probability (neg. binom. function applied to # of imports) = 0.05

Disease model
Beta (rate of infection) = 0.15
Gamma (rate of recovery) = 0.125

Human spillover parameters
Spillover efficiency (probability of infection given contact)  = 0.0000083
Contacts with infectious cow (robotic milking system) = 1/day
Contacts with infectious cow  (manual milking) = 2/day
Number of workers = variable, depending on herd size IQR  = [2,8], med = 4
"""
from enum import Enum

FARM_INPUT_FILENAME = "farms.xlsx"
PEOPLE_INPUT_FILENAME = "people.xlsx"

# -----------------------------------------------------------
# ----------------- TIME ------------------------------------

# total steps for 24-hour day
STEPS_PER_DAY = 16  # 1 step = 1.5 hours
# step numbers that are part of the working day - all VTH staff are at the hospital or farms, farmers are at farms
DAYTIME_STEPS = 6  # 9am to 6pm
WORK_DAY_STEPS = [step+1 for step in range(DAYTIME_STEPS)]  # model steps count from 1


def convert_per_day_to_per_step(num_per_day):
    """
    Converts a number of events per day into a number of events per step. Rounds to the nearest integer.

    :param num_per_day: Number of events per day
    :type num_per_day: int
    :return: Number of events per step
    :rtype: int
    """
    return max(1, round(num_per_day / STEPS_PER_DAY))


def convert_days_to_steps(num_days):
    """
    Converts a number of days into a number of steps. Rounds to the nearest integer.

    :param num_days: Number of days to convert
    :type num_days: numeric
    :return: Number of model steps
    :rtype: int
    """
    return round(num_days * STEPS_PER_DAY)


# -----------------------------------------------------------
# ----------------- FARM SERVICE VISITS TO FARMS ------------
# these numbers are averages, in the code they will be converted to probabilities
# also, these are for all farms, so 2-4 emergency visits overall

# Luke: Weekends are variable for calls but I think on average there would be 2-4 calls per month on the weekends.
EMERGENCY_VISITS_PER_MONTH = 3
EMERGENCY_VISITS_PER_STEP = EMERGENCY_VISITS_PER_MONTH / (8 * STEPS_PER_DAY)  # 8 = number of weekend days in a month

# Unscheduled calls that aren't emergencies, should result in 1-2 visits per day in business hours
NON_URGENT_CALLS_PER_DAY = 2
NON_URGENT_CALLS_PER_STEP = NON_URGENT_CALLS_PER_DAY / STEPS_PER_DAY


# -----------------------------------------------------------
# ----------------- HPAI ------------------------------------

HUMAN_INFECT_CATTLE_PROB = 0.1  # prob of a human infecting a cow assuming contact. 0-1
HUMAN_INFECT_HUMAN_PROB = 0.1  # prob of a human infecting another human assuming contact. 0-1
HUMAN_INFECTIOUS_DAYS = 10  # num days a human stays in Infected state
HUMAN_RECOVERED_DAYS = 20  # num days a human stays in Recovered state

HUMAN_INFECTIOUS_STEPS = convert_days_to_steps(HUMAN_INFECTIOUS_DAYS)
HUMAN_RECOVERED_STEPS = convert_days_to_steps(HUMAN_RECOVERED_DAYS)

CATTLE_INFECT_HUMAN_PROB = 0.1
# CATTLE_INFECT_HUMAN_PROB = 0.0000083  # per contact-step. 0-1 (from Reilly Comper)
CATTLE_INFECT_CATTLE_PROB = 0.1  # probability per contact. 0-1
CATTLE_INFECTED_DAYS = 10
CATTLE_INFECTED_STEPS = convert_days_to_steps(CATTLE_INFECTED_DAYS)
CATTLE_RECOVERED_DAYS = 100
CATTLE_RECOVERED_STEPS = convert_days_to_steps(CATTLE_RECOVERED_DAYS)


# -----------------------------------------------------------
# ----------------- COMMUNITY -------------------------------

COMMUNITY = 'community'
COMMUNITY_POPULATION = 30000
COMMUNITY_CONTACTS_PER_STEP = 1

# -----------------------------------------------------------
# farm
# DEFAULT_DAIRY_HERD_SIZE = 50

VET_STEPS_AT_FARM = 1  # number of steps they spend on the farm for a visit
VET_CONTACTS_PER_STEP = 10  # number of cows they see on the farm

# maximum number of farms that can be visited in a single trip from the VTH by a farm services clinician
MAX_VISITS_PER_TRIP = 3


class FarmHousing(Enum):
    """
    Types of housing on dairy farms
    """
    FREE_STALL = 'freestall'
    TIE_STALL = 'tie stall'
    STRAW_PACK = 'straw pack'
    TIE_AND_STRAW = 'tie stall and straw pack'


CATTLE_CONTACTS_PER_STEP = {
    FarmHousing.FREE_STALL: 10,
    FarmHousing.TIE_STALL: 2,
    FarmHousing.STRAW_PACK: 10,
    FarmHousing.TIE_AND_STRAW: 5
}


class FarmMilkingSystem(Enum):
    """
    Types of dairy farm milking systems
    """
    PARLOUR = 'parlour'
    AMS = 'ams'
    PIPELINE = 'pipeline'
    ROTARY_PARLOUR = 'rotary parlour'


# number of times milking occurs on a farm
# this is more about the number of times the farmer has to interact with the milking equipment
NUM_MILKING_EVENTS_PER_DAY = 3

# number of contacts cow<->farmer at each milking event
NUM_MILKING_CONTACTS = {
    FarmMilkingSystem.PARLOUR: 2,
    FarmMilkingSystem.AMS: 1,
    FarmMilkingSystem.PIPELINE: 2,
    FarmMilkingSystem.ROTARY_PARLOUR: 2
}

# -----------------------------
# Enums


class Location(Enum):
    """
    Locations that mobile agents (e.g. PersonAgent) can be. The locations are types of static agents
    """
    HOSPITAL = 0
    FARM = 1
    COMMUNITY = 2


class PersonRole(Enum):
    """
    Roles of people agents in the hospital.
    """
    FARM_SERVICES_CLINICIAN = 'FSc'
    FARM_SERVICES_TECH = 'FSt'
    FARM_SERVICES_STUDENT = 'FSu'
    LARGE_ANIMAL_CLINICIAN = 'LAc'
    LARGE_ANIMAL_STAFF = 'LAs'
    LARGE_ANIMAL_STUDENT = 'LAu'
    SMALL_ANIMAL_CLINICIAN = 'SAc'
    SMALL_ANIMAL_STAFF = 'SAs'
    SMALL_ANIMAL_STUDENT = 'SAu'
    FLOATING_CLINICIAN = 'Fc'
    FLOATING_STAFF = 'Fs'
    FLOATING_STUDENT = 'Fu'
    FARMER = 'f'


input_to_role = {
    'farm services vet': PersonRole.FARM_SERVICES_CLINICIAN,
    'farm services clinician': PersonRole.FARM_SERVICES_CLINICIAN,
    'farm services technician': PersonRole.FARM_SERVICES_TECH,
    'farm services tech': PersonRole.FARM_SERVICES_TECH,
    'farm services student': PersonRole.FARM_SERVICES_STUDENT,
    'large animal vet': PersonRole.LARGE_ANIMAL_CLINICIAN,
    'large animal clinician': PersonRole.LARGE_ANIMAL_CLINICIAN,
    'large animal staff': PersonRole.LARGE_ANIMAL_STAFF,
    'large animal student': PersonRole.LARGE_ANIMAL_STUDENT,
    'small animal vet': PersonRole.SMALL_ANIMAL_CLINICIAN,
    'small animal clinician': PersonRole.SMALL_ANIMAL_CLINICIAN,
    'small animal staff': PersonRole.SMALL_ANIMAL_STAFF,
    'small animal student': PersonRole.SMALL_ANIMAL_STUDENT,
    'floating vet': PersonRole.FLOATING_CLINICIAN,
    'floating clinician': PersonRole.FLOATING_CLINICIAN,
    'floating staff': PersonRole.FLOATING_STAFF,
    'floating student': PersonRole.FLOATING_STUDENT,
}


class DiseaseState(Enum):
    """
    Possible disease progression states.
    SEIATR model from Malek and Hoque (2024)
    """
    SUSCEPTIBLE = 0
    EXPOSED = 1
    INFECTED = 2  # symptomatic
    ASYMPTOMATIC = 3
    TREATED = 4
    RECOVERED = 5


class FarmVetVisitState(Enum):
    """
    Farm states to indicate their interaction with a vet
    """
    OK = 0
    NEED_VET = 1
    VET_PRESENT = 2


class HospitalDepartment(Enum):
    """
    Department in the veterinary hospital
    """
    LARGE_ANIMAL = "large animal"
    SMALL_ANIMAL = "small animal"
    FARM_SERVICES = "farm services"
    COMMON = 'common'


