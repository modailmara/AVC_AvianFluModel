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

# -----------------------------------------------------------
SCENARIO_NAME = 'Default'
# -----------------------------------------------------------

# infection probabilities given a contact
DEFAULT_HUMAN_INFECT_CATTLE_PROB = 0.1
DEFAULT_HUMAN_INFECT_HUMAN_PROB = 0.1
DEFAULT_CATTLE_INFECT_HUMAN_PROB = 0.1
DEFAULT_CATTLE_INFECT_CATTLE_PROB = 0.1

COMMUNITY = 'community'
FARM_INPUT_FILENAME = "farms.xlsx"
PEOPLE_INPUT_FILENAME = "people.xlsx"
DEFAULT_PARAMETERS_INPUT_FILENAME = "default-parameters.ini"
SCENARIO_PARAMETERS_INPUT_FILENAME = "scenario-parameters.ini"


class FarmHousing(Enum):
    """
    Types of housing on dairy farms
    """
    FREE_STALL = 'freestall'
    TIE_STALL = 'tie stall'
    STRAW_PACK = 'straw pack'
    TIE_AND_STRAW = 'tie stall and straw pack'


class FarmMilkingSystem(Enum):
    """
    Types of dairy farm milking systems
    """
    PARLOUR = 'parlour'
    AMS = 'ams'
    PIPELINE = 'pipeline'
    ROTARY_PARLOUR = 'rotary parlour'


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

TRUCK_ROLE = 'truck'


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
    Not all these states are currently used in the model
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






