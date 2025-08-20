import numpy as np

from constants import COMMUNITY_POPULATION, HUMAN_INFECT_HUMAN_PROB, HUMAN_INFECTIOUS_DAYS, HUMAN_RECOVERED_DAYS, \
    STEPS_PER_DAY, COMMUNITY_CONTACTS_PER_STEP


class SIRModel(object):
    """
    Simple Susceptible-Infected-Recovered system dynamics model
    """

    def __init__(self, model, name,
                 population=COMMUNITY_POPULATION, infection_probability=HUMAN_INFECT_HUMAN_PROB,
                 recovery_days=HUMAN_INFECTIOUS_DAYS, recovered_expire_days=HUMAN_RECOVERED_DAYS,
                 num_contacts_per_step=COMMUNITY_CONTACTS_PER_STEP):
        """

        :param name: Name of this model. Identifies what this model represents.
        :type name: str
        :param population:
        :type population:
        :param infection_probability:
        :type infection_probability:
        :param recovery_days:
        :type recovery_days:
        :param recovered_expire_days:
        :type recovered_expire_days:
        :param num_contacts_per_step: Number of other cows a single cow comes into contact with each step
        :type num_contacts_per_step: int
        """
        self.model = model
        self.name = name

        # counts for each disease state - start off clear of the disease
        self.susceptible = population
        self.infected = [0] * recovery_days * STEPS_PER_DAY  # each list item is count for number of steps infected
        # each list item is count for number of steps recovered
        self.recovered = [0] * recovered_expire_days * STEPS_PER_DAY

        # model parameters
        self.infection_prob = infection_probability
        self.num_contacts_per_step = num_contacts_per_step

    @property
    def population(self):
        """
        Total count of all entities, across all disease states
        :return: Number of entities
        :rtype: int
        """
        return self.susceptible + sum(self.infected) + sum(self.recovered)

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
        # print(" ({}) {}: {} / {} = {}".format(self.model.steps, self.name, sum(self.infected), self.population,
        #                                       sum(self.infected) / self.population))
        return sum(self.infected) / self.population

    def progress_infection(self):
        """
        Progress one step of the disease.
        - infected can infect susceptible
        - infected recover
        - recovery immunity expires
        """
        potential_new_infections = np.random.binomial(
            self.num_contacts_per_step * sum(self.infected),
            self.proportion_susceptible
        )
        new_infected = min(self.susceptible, np.random.binomial(potential_new_infections, self.infection_prob))

        new_recovered = self.infected[-1]
        new_recovery_ended = self.recovered[-1]

        # adjust the state counts
        self.susceptible -= new_infected
        self.susceptible += new_recovery_ended

        self.infected = self.progress_state_list_one_step(self.infected)
        self.infected[0] = new_infected

        self.recovered = self.progress_state_list_one_step(self.recovered)
        self.recovered[0] = new_recovered

    def progress_state_list_one_step(self, state_list):
        """
        Progresses a list one step forward, e.g. state_list[1] -> state_list[2], state_list[0] -> state_list[1]
        Assume the last list member is not needed

        :param state_list: The list to be progressed
        :type state_list: list
        :return: The list with all elements moved one index up
        :rtype: list
        """
        # go through the list in reverse so no items are overwritten before being copied
        # start at the second last item as the last one isn't needed (and would "fall off" the end anyway)
        for i in range(len(state_list) - 2, -1, -1):
            state_list[i + 1] = state_list[i]
        return state_list

    def infect_susceptible(self, num_to_infect, infection_path):
        """
        Changes some of the model entities from susceptible to infected. If there are less susceptible than the number
        specified, will only infect the number of susceptible.

        :param num_to_infect: The requested number to change susceptible -> infected
        :type num_to_infect: int
        :param infection_path: The path this infection took before getting to this SIR model
        :type infection_path: list

        :return: Number of entities infected
        :rtype: int
        """
        num_infected = min(self.susceptible, num_to_infect)
        if num_infected > 0:
            self.susceptible -= num_infected
            self.infected[0] += num_infected

            # add the infection path, need to append this SIR model name
            path = infection_path + [self.name]

            self.model.infection_paths.add_path(path, num_infected)

        return num_infected

    def step(self):
        self.progress_infection()

