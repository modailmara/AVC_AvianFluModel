import numpy as np

from constants import COMMUNITY_POPULATION, HUMAN_INFECT_HUMAN_PROB, HUMAN_INFECTED_STEPS, HUMAN_RECOVERED_STEPS, \
    COMMUNITY_CONTACTS_PER_STEP


class SIRModel(object):
    """
    Simple Susceptible-Infected-Recovered system dynamics model
    """

    def __init__(self, population=COMMUNITY_POPULATION, infection_probability=HUMAN_INFECT_HUMAN_PROB,
                 recovery_steps=HUMAN_INFECTED_STEPS, recovered_expire_steps=HUMAN_RECOVERED_STEPS,
                 num_contacts=COMMUNITY_CONTACTS_PER_STEP):
        # counts for each disease state - start off clear of the disease
        self.susceptible = population
        self.infected = 0
        self.recovered = 0

        # model parameters
        self.infection_prob = infection_probability
        self.recovery_prob = 1 / recovery_steps
        self.recovered_expire_prob = 1 / recovered_expire_steps
        self.num_contacts = num_contacts

    @property
    def population(self):
        """
        Total count of all entities, across all disease states
        :return: Number of entities
        :rtype: int
        """
        return self.susceptible + self.infected + self.recovered

    @property
    def proportion_susceptible(self):
        """

        :return:
        :rtype: float
        """
        return self.susceptible / self.population

    @property
    def proportion_infected(self):
        """

        :return: Proportion of the population that is infected.
        :rtype: float
        """
        return self.infected / self.population

    def progress_infection(self):
        """
        Progress one step of the disease
        - infected can infect susceptible
        - infected recover
        - recovery immunity expires
        """
        potential_new_infections = np.random.binomial(self.num_contacts * self.infected, self.proportion_susceptible)

        new_infected = min(self.susceptible, np.random.binomial(potential_new_infections, self.infection_prob))
        new_recovered = np.random.binomial(self.infected, self.recovery_prob)
        new_recovery_ended = np.random.binomial(self.recovered, self.recovered_expire_prob)

        # adjust the state counts
        self.susceptible -= min(new_infected, self.susceptible)
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

    def step(self):
        self.progress_infection()

