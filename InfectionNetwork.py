import networkx as nx

from constants import COMMUNITY, Location
from Models.LocationAgents import DairyFarmAgent

COMMUNITY_NODE_NAME = 'C'


class InfectionNetwork:
    """
    Keeps a record of the complete infection network - who, when, and where of all infection events.

    Nodes correspond to agents, and are named by the agent's "name" property

    Edges correspond to infection events. Properties:
      - 'step': model time step when the infection occurred
      - 'location': Location where the infection occurred: HOSPITAL, COMMUNITY, FARM
      - 'department' (optional): if in the hospital, the department where the infection occurred
    """

    def __init__(self):
        self.infection_graph = nx.MultiDiGraph()
        self.source_nodes = {}

    def _add_node_for_agent(self, agent, step):
        if agent.short_name not in self.infection_graph.nodes:
            if isinstance(agent, DairyFarmAgent):
                role = 'FARM'
            else:
                role = agent.role
            self.infection_graph.add_node(agent.short_name, role=role, step=step)

    def add_infection_source(self, source_agent):
        """

        :param source_agent:
        :type source_agent:
        """
        self._add_node_for_agent(source_agent, 0)
        self.source_nodes[source_agent.short_name] = 0

    def add_infection_event(self, infected_agent, source_agent, time_step):
        """
        Adds an infection event to the network: source <=> edge <=> infected.
        :param source_agent: The agent that infected another agent. None if this is a starting infection.
        :type source_agent: DairyFarmAgent or PeopleAgent object
        :param infected_agent:
        :type infected_agent:
        :param time_step:
        :type time_step:
        """
        # create a node for the new infected agent
        self._add_node_for_agent(infected_agent, time_step)

        if source_agent is not None:
            # not a starting node so create a node for the source of the infection
            self._add_node_for_agent(source_agent, time_step)

            # create an edge from source to infected, annotate with time and place
            self.infection_graph.add_edge(source_agent.short_name, infected_agent.short_name,
                                          step=time_step, location=infected_agent.location,
                                          department=infected_agent.department)

    def add_community_spillover(self, source_agent, time_step):
        """

        :param source_agent:
        :type source_agent:
        :param time_step:
        :type time_step:
        """
        self._add_community_infection_edge(source_agent, time_step, True)

    def add_community_infection(self, infected_agent, time_step):
        self._add_community_infection_edge(infected_agent, time_step, False)

    def _add_community_infection_edge(self, agent, step, is_agent_source):
        """

        :param agent:
        :type agent:
        :param step:
        :type step: int
        :param is_agent_source:
        :type is_agent_source: boolean
        """
        if COMMUNITY_NODE_NAME not in self.infection_graph.nodes:
            # add a community node
            self.infection_graph.add_node(COMMUNITY_NODE_NAME, step=step)

        self._add_node_for_agent(agent, step)
        if is_agent_source:
            source_node_name = agent.short_name
            infected_node_name = COMMUNITY_NODE_NAME
        else:
            source_node_name = COMMUNITY_NODE_NAME
            infected_node_name = agent.short_name

        self.infection_graph.add_edge(source_node_name, infected_node_name,
                                      step=step, location=Location.COMMUNITY, department=None)


