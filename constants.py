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
# time
# total steps from midnight to midnight
STEPS_PER_DAY = 16  # 1 step = 1.5 hours
# step numbers that are part of the working day - all VTH staff are at the hospital or farms, farmers are at farms
DAYTIME_STEPS = round(1 / 3 * STEPS_PER_DAY)
WORK_DAY_STEPS = list(range(1, DAYTIME_STEPS + 1))
# steps not at work - all person agents are in the community. in order from knockoff time
NIGHTTIME_STEPS = STEPS_PER_DAY - DAYTIME_STEPS
COMMUNITY_STEPS = list(range(DAYTIME_STEPS + 1, STEPS_PER_DAY + 1))


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
# community
COMMUNITY_POPULATION = 3000
COMMUNITY_CONTACTS_PER_STEP = 2

# -----------------------------------------------------------
# farm
# DEFAULT_DAIRY_HERD_SIZE = 50

VET_STEPS_AT_FARM = 1
VET_CONTACTS_PER_STEP = 10  # number of cows they see


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


NUM_MILKING_CONTACTS = {
    FarmMilkingSystem.PARLOUR: 2,
    FarmMilkingSystem.AMS: 1,
    FarmMilkingSystem.PIPELINE: 2,
    FarmMilkingSystem.ROTARY_PARLOUR: 2
}

# -----------------------------------------------------------
# flu disease parameters
HUMAN_INFECT_CATTLE_PROB = 0  # prob of a human infecting a cow assuming contact
HUMAN_INFECT_HUMAN_PROB = .1  # prog of a human infecting another human assuming contact
HUMAN_INFECTED_DAYS = 10  # num days a human stays in Infected state
HUMAN_INFECTED_STEPS = convert_days_to_steps(HUMAN_INFECTED_DAYS)
HUMAN_RECOVERED_DAYS = 20  # num days a human stays in Recovered state
HUMAN_RECOVERED_STEPS = convert_days_to_steps(HUMAN_RECOVERED_DAYS)

CATTLE_INFECT_HUMAN_PROB = 0.9  # per step
# CATTLE_INFECT_HUMAN_PROB = 0.0000083
CATTLE_INFECT_CATTLE_PROB = 1
CATTLE_INFECTED_DAYS = 10
CATTLE_INFECTED_STEPS = convert_days_to_steps(CATTLE_INFECTED_DAYS)
CATTLE_RECOVERED_DAYS = 100
CATTLE_RECOVERED_STEPS = convert_days_to_steps(CATTLE_RECOVERED_DAYS)


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
    FARM_SERVICES_VET = 'farm services vet'
    FARM_SERVICES_TECH = 'farm services technician'
    FARM_SERVICES_STUDENT = 'farm services student'
    LARGE_ANIMAL_VET = 'large animal vet'
    LARGE_ANIMAL_STAFF = 'large animal staff'
    LARGE_ANIMAL_STUDENT = 'large animal student'
    SMALL_ANIMAL_VET = 'small animal vet'
    SMALL_ANIMAL_STAFF = 'small animal staff'
    SMALL_ANIMAL_STUDENT = 'small animal student'
    FLOATING_VET = 'floating vet'
    FLOATING_STAFF = 'floating staff'
    FLOATING_STUDENT = 'floating student'
    FARMER = 'farmer'


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


