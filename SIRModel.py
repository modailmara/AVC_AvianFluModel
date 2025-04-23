from random import random

from constants import COMMUNITY_POPULATION, HUMAN_INFECT_HUMAN_PROB, HUMAN_RECOVERY_RATE, HUMAN_RECOVERY_EXPIRE_RATE


class SIRModel(object):
    """
    Simple Susceptible-Infected-Recovered system dynamics model
    """

    def __init__(self, population=COMMUNITY_POPULATION, infection_probability=HUMAN_INFECT_HUMAN_PROB,
                 recovery_rate=HUMAN_RECOVERY_RATE, recovered_expire_rate=HUMAN_RECOVERY_EXPIRE_RATE):
        # counts for each disease state - start off clear of the disease
        self.susceptible = population
        self.infected = 0
        self.recovered = 0

        # model parameters
        # number of contact events per infected per step
        self.contacts_per_infected = 1
        self.infection_probability = infection_probability
        self.recovery_rate = recovery_rate
        self.recovered_expire_rate = recovered_expire_rate

    @property
    def population(self):
        """
        Total count of all entities, across all disease states
        :return: Number of entities
        :rtype: int
        """
        return self.susceptible + self.infected + self.recovered

    def progress_infection(self):
        """
        Progress one step of the disease
        """
        # calculate how many should change disease state
        # available in 3.12:
        # random.binomialvariate(self.infected, self.contacts_per_infected * self.infection_probability)
        new_infection_prob = self.contacts_per_infected * self.infection_probability
        new_infected = sum(random() < new_infection_prob for i in range(self.infected))
        new_recovered = sum(random() < self.recovery_rate for i in range(self.infected))
        new_recovery_ended = sum(random() < self.recovered_expire_rate for i in range(self.recovered))

        # adjust the state counts
        self.susceptible -= new_infected
        self.susceptible += new_recovery_ended
        self.infected += new_infected
        self.infected -= new_recovered
        self.recovered += new_recovered
        self.recovered -= new_recovery_ended
        # print('  S: {}\n  I: {}\n  R: {}\n'.format(self.susceptible, self.infected, self.recovered))

    def infect_susceptible(self, num_to_infect):
        """
        Changes some of the model entities from susceptible to infected. If there are less susceptible than the number
        specified, will only infect the number of susceptible.

        :param num_to_infect: The requested number to change susceptible -> infected
        :type num_to_infect: int
        :return: Number of entities infected
        :rtype: int
        """
        num_infected = min(self.susceptible, num_to_infect)
        self.susceptible -= num_infected
        self.infected += num_infected

        return num_infected

