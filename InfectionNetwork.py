import networkx as nx
import uuid

from constants import COMMUNITY, Location
from Models.LocationAgents import DairyFarmAgent, HospitalAgent
from Models.PeopleAgents import PersonAgent

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
        self.infection_graph = nx.DiGraph()
        self.infection_graph.add_node(COMMUNITY_NODE_NAME, step=0)
        self.source_nodes = {}

    def _add_node_for_agent(self, agent, step):
        if agent.short_name not in self.infection_graph.nodes:
            if isinstance(agent, DairyFarmAgent):
                role = 'FARM'
            elif isinstance(agent, HospitalAgent):
                role = 'HOSPITAL'
            elif isinstance(agent.role, str):
                role = agent.role
            else:
                role = agent.role.value
            self.infection_graph.add_node(agent.short_name, role=role, step=step)

    def add_infection_source(self, source_agent):
        """

        :param source_agent:
        :type source_agent:
        """
        self._add_node_for_agent(source_agent, 0)
        self.source_nodes[source_agent.short_name] = 0
        # print("Source: {}".format(source_agent.short_name))

    def add_infection_event(self, source_agent, infected_agent, time_step):
        """
        Adds an infection event to the network: source <=> edge <=> infected.
        The source_agent already exists. Use add_infection_source() for infection source nodes.

        :param source_agent: The agent that infected another agent. None if this is a starting infection.
        :type source_agent: DairyFarmAgent or PeopleAgent object
        :param infected_agent:
        :type infected_agent:
        :param time_step:
        :type time_step:
        """
        # create a node for the new infected agent
        self._add_node_for_agent(infected_agent, time_step)

        if (source_agent.short_name, infected_agent.short_name) in self.infection_graph.edges:
            # existing edge so increase the weight
            self.infection_graph.edges[source_agent.short_name, infected_agent.short_name]['weight'] += 1
        else:
            # new edge
            self.infection_graph.add_edge(source_agent.short_name, infected_agent.short_name, step=time_step, weight=1)

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

        if (source_node_name, infected_node_name) in self.infection_graph.edges:
            # existing edge so increase the weight
            self.infection_graph.edges[source_node_name, infected_node_name]['weight'] += 1
        else:
            # new edge
            self.infection_graph.add_edge(source_node_name, infected_node_name, step=step, weight=1)

    def write_network(self, location_dir, label, scenario_name, param_value=None):
        """

        :param location_dir:
        :type location_dir:
        :param label:
        :type label:
        :param scenario_name:
        :type scenario_name:
        :param param_value: (optional)
        :type param_value:

        :return:
        :rtype:
        """
        working_dir = location_dir / 'working'
        working_dir.mkdir(parents=True, exist_ok=True)

        filename = "{}_{}_{}_{}".format(scenario_name, label, param_value, uuid.uuid4())

        # write the edgelist
        nx.write_edgelist(self.infection_graph, working_dir / '{}.{}'.format(filename, 'csv'), delimiter=',',
                          data=['weight', 'step'])
        # write the graphml
        nx.write_graphml(self.infection_graph, working_dir / '{}.{}'.format(filename, 'graphml'))
