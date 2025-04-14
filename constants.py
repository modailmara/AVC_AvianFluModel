"""
Constants about behaviour of agents and disease epidemiology.

Enum classes for the state-transition models
"""
from enum import Enum

# CONSTANTS

# numbers of agents
NUM_FARM_SERVICES_VETS = 11  # vets (5) and students (6)
NUM_FARM_SERVICES_TECHS = 2
NUM_LARGE_ANIMAL_VETS = 21  # includes vets (3), staff(6), and students (12)
NUM_SMALL_ANIMAL_VETS = 60  # small animal vets (10), staff (20), and students (30)
NUM_FLOATING_STAFF = 28  # floating vets (3), staff (7), and students (18)

# vet visits to farms
CHANCE_FARM_NEEDS_VET = .2
VET_STEPS_AT_FARM = 1

# avian flu disease parameters
HUMAN_INFECT_CATTLE_PROB = .1
HUMAN_INFECT_HUMAN_PROB = .1
HUMAN_INFECTED_STEPS = 3
HUMAN_RECOVERED_STEPS = 10

CATTLE_INFECT_HUMAN_PROB = .1
CATTLE_INFECT_CATTLE_PROB = .05
CATTLE_RECOVERY_PROB = .5
CATTLE_RECOVERY_END_PROB = .05

BIRD_INFECT_COW_PROB = 0.01


# -----------------------------
# STATES


class Location(Enum):
    """
    Locations that mobile agents (e.g. PersonAgent) can be. The locations are types of static agents
    """
    HOSPITAL = 0
    FARM = 1


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

