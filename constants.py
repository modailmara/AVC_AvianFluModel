"""
Constants about behaviour of agents and disease epidemiology.

Enum classes for the state-transition models
"""
from enum import Enum

# CONSTANTS

# time
# total steps from midnight to midnight
STEPS_PER_DAY = 6
# step numbers that are part of the working day - all VTH staff are at the hospital or farms, farmers are at farms
DAYTIME_STEPS = round(1 / 3 * STEPS_PER_DAY)
WORK_DAY_STEPS = list(range(1, DAYTIME_STEPS + 1))
# steps not at work - all person agents are in the community. in order from knockoff time
NIGHTTIME_STEPS = STEPS_PER_DAY - DAYTIME_STEPS
COMMUNITY_STEPS = list(range(DAYTIME_STEPS + 1, STEPS_PER_DAY + 1))

# community
COMMUNITY_POPULATION = 3000
COMMUNITY_CONTACTS_PER_DAY = 12
COMMUNITY_CONTACTS_PER_STEP = round(COMMUNITY_CONTACTS_PER_DAY / STEPS_PER_DAY)

# farm
DEFAULT_DAIRY_HERD_SIZE = 50
CATTLE_CATTLE_CONTACTS_PER_DAY = 30
CATTLE_CATTLE_CONTACTS_PER_STEP = round(CATTLE_CATTLE_CONTACTS_PER_DAY / STEPS_PER_DAY)
CATTLE_FARMER_CONTACTS_PER_DAY = 30
CATTLE_FARMER_CONTACTS_PER_STEP = round(CATTLE_FARMER_CONTACTS_PER_DAY / STEPS_PER_DAY)  # when the farmer is there
CATTLE_VET_CONTACTS_PER_DAY = 12
CATTLE_VET_CONTACTS_PER_STEP = round(CATTLE_VET_CONTACTS_PER_DAY / STEPS_PER_DAY)  # when there is a vet on the farm

CATTLE_BIRD_CONTACTS_PER_DAY = 12
CATTLE_BIRD_CONTACTS_PER_STEP = round(CATTLE_BIRD_CONTACTS_PER_DAY / STEPS_PER_DAY)
BIRD_INFECT_COW_PROB = 0.01

# numbers of agents
NUM_FARM_SERVICES_VETS = 11  # vets (5) and students (6)
NUM_FARM_SERVICES_TECHS = 2
NUM_LARGE_ANIMAL_VETS = 21  # includes vets (3), staff(6), and students (12)
NUM_SMALL_ANIMAL_VETS = 60  # small animal vets (10), staff (20), and students (30)
NUM_FLOATING_STAFF = 28  # floating vets (3), staff (7), and students (18)
NUM_FARMS = 10

# vet visits to farms
CHANCE_FARM_NEEDS_VET = .2  # prob a farm will request a vet visit
VET_DAYS_AT_FARM = 1 / 6  # num days the vet stays at the farm during a visit
VET_STEPS_AT_FARM = round(VET_DAYS_AT_FARM / STEPS_PER_DAY)

# avian flu disease parameters
HUMAN_INFECT_CATTLE_PROB = 0  # prob of a human infecting a cow assuming contact
HUMAN_INFECT_HUMAN_PROB = .1  # prog of a human infecting another human assuming contact
HUMAN_INFECTED_DAYS = 10  # num days a human stays in Infected state
HUMAN_INFECTED_STEPS = HUMAN_INFECTED_DAYS * STEPS_PER_DAY
HUMAN_RECOVERED_DAYS = 20  # num days a human stays in Recovered state
HUMAN_RECOVERED_STEPS = HUMAN_RECOVERED_DAYS * STEPS_PER_DAY

CATTLE_INFECT_HUMAN_PROB = .1
CATTLE_INFECT_CATTLE_PROB = .05
CATTLE_INFECTED_DAYS = 10
CATTLE_INFECTED_STEPS = CATTLE_INFECTED_DAYS * STEPS_PER_DAY
CATTLE_RECOVERED_DAYS = 20
CATTLE_RECOVERED_STEPS = CATTLE_RECOVERED_DAYS * STEPS_PER_DAY


# -----------------------------
# Enums

class Time(Enum):
    DAY = 0  # at work
    NIGHT = 1


class Location(Enum):
    """
    Locations that mobile agents (e.g. PersonAgent) can be. The locations are types of static agents
    """
    HOSPITAL = 0
    FARM = 1
    COMMUNITY = 2


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
    LARGE_ANIMAL = "large_animal"
    SMALL_ANIMAL = "small_animal"
    FARM_SERVICES = "farm_services"


class FarmMilkingSystem(Enum):
    """
    Types of dairy farm milking systems
    """
    PARLOUR = 'parlour'
    AMS = 'ams'
    PIPELINE = 'pipeline'
    ROTARY_PARLOUR = 'rotary parlour'


class FarmHousing(Enum):
    """
    Types of housing on dairy farms
    """
    FREESTALL = 'freestall'
    TIE_STALL = 'tie stall'
    STRAW_PACK = 'straw pack'
    TIE_AND_STRAW = 'tie stall and straw pack'

