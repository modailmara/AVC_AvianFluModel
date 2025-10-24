import numpy as np


class SIRModel(object):
    """
    Simple Susceptible-Infected-Recovered system dynamics model for a group of a single type of animal
    """

    def __init__(self, model, name,
                 population, infection_probability,
                 exposed_steps,
                 infectious_steps, recovered_steps,
                 num_contacts_per_step):
        """

        :param name: Name of this model. Identifies what this model represents.
        :type name: str
        :param population:
        :type population:
        :param infection_probability: Probability of infection between animals
        :type infection_probability:
        :param exposed_steps: Model steps that the animal spends in the Exposed state
        :type exposed_steps: int
        :param infectious_steps: Model steps that the animal spends in the Infectious state
        :type infectious_steps: int
        :param recovered_steps: Model steps that the animal spends in the Recovered state
        :type recovered_steps: int
        :param num_contacts_per_step: Number of other animals a single animal comes into contact with each step
        :type num_contacts_per_step: int
        """
        self.model = model
        self.name = name

        # counts for each disease state - start off clear of the disease
        self.susceptible = population
        self.exposed = [0] * exposed_steps
        self.infected = [0] * infectious_steps  # each list item is count for number of steps infected
        # each list item is count for number of steps recovered
        self.recovered = [0] * recovered_steps

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
        return self.susceptible + sum(self.exposed) + sum(self.infected) + sum(self.recovered)

    @property
    def num_susceptible(self):
        return self.susceptible

    @property
    def proportion_susceptible(self):
        """

        :return:
        :rtype: float
        """
        return self.susceptible / self.population

    @property
    def num_exposed(self):
        return sum(self.exposed)

    @property
    def proportion_exposed(self):
        return sum(self.exposed) / self.population

    @property
    def num_infected(self):
        return sum(self.infected)

    @property
    def proportion_infected(self):
        """

        :return: Proportion of the population that is infected.
        :rtype: float
        """
        return sum(self.infected) / self.population

    @property
    def num_recovered(self):
        return sum(self.recovered)

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
        new_exposed = min(self.susceptible, np.random.binomial(potential_new_infections, self.infection_prob))

        new_infected = self.exposed[-1]
        new_recovered = self.infected[-1]
        new_recovery_ended = self.recovered[-1]

        # adjust the state counts
        self.susceptible -= new_exposed
        self.susceptible += new_recovery_ended

        self.exposed = self.progress_state_list_one_step(self.exposed)
        self.exposed[0] = new_exposed

        self.infected = self.progress_state_list_one_step(self.infected)
        self.infected[0] = new_infected

        self.recovered = self.progress_state_list_one_step(self.recovered)
        self.recovered[0] = new_recovered

    def progress_state_list_one_step(self, state_list):
        """
        Progresses a list one step forward, e.g. state_list[n-1] -> state_list[n], ..., state_list[0] -> state_list[1]
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
        if num_infected > 0:
            self.susceptible -= num_infected
            self.infected[0] += num_infected

        return num_infected

    def expose_to_infection(self, num_to_expose):
        """
        Changes some of the model entities from susceptible to infected. If there are less susceptible than the number
        specified, will only infect the number of susceptible.

        :param num_to_expose: The requested number to change susceptible -> exposed
        :type num_to_expose: int

        :return: Number of entities infected
        :rtype: int
        """
        num_exposed = min(self.susceptible, num_to_expose)
        if num_exposed > 0:
            self.susceptible -= num_exposed
            self.exposed[0] += num_exposed

        return num_exposed

    def step(self):
        self.progress_infection()

