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

    def _add_node_for_agent(self, node_name, step):
        self.infection_graph.add_node(node_name, step=step)

    def add_infection_source(self, node_name):
        """

        :param source_agent:
        :type source_agent:
        """
        self._add_node_for_agent(node_name, 0)
        self.source_nodes[node_name] = 0

    def add_infection_event(self, source_name, target_name, time_step):
        """
        Adds an infection event to the network: source <=> edge <=> infectious.
        The source_agent already exists. Use add_infection_source() for infection source nodes.

        :param source_agent: The agent that infectious another agent. None if this is a starting infection.
        :type source_agent: DairyFarmAgent or PeopleAgent object
        :param infected_agent:
        :type infected_agent:
        :param time_step:
        :type time_step:
        """
        # create a node for the new infectious agent
        self._add_node_for_agent(target_name, time_step)

        if (source_name, target_name) in self.infection_graph.edges:
            # existing edge so increase the weight
            self.infection_graph.edges[source_name, target_name]['weight'] += 1
        else:
            # new edge
            self.infection_graph.add_edge(source_name, target_name, step=time_step, weight=1)

    def add_community_spillover(self, source_name, time_step):
        """

        :param source_agent:
        :type source_agent:
        :param time_step:
        :type time_step:
        """
        self._add_community_infection_edge(source_name, time_step, True)

    def add_community_infection(self, target_name, time_step):
        self._add_community_infection_edge(target_name, time_step, False)

    def _add_community_infection_edge(self, agent_name, step, is_agent_source):
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

        self._add_node_for_agent(agent_name, step)
        if is_agent_source:
            source_name = agent_name
            target_name = COMMUNITY_NODE_NAME
        else:
            source_name = COMMUNITY_NODE_NAME
            target_name = agent_name

        if (source_name, target_name) in self.infection_graph.edges:
            # existing edge so increase the weight
            self.infection_graph.edges[source_name, target_name]['weight'] += 1
        else:
            # new edge
            self.infection_graph.add_edge(source_name, target_name, step=step, weight=1)

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

        # The uuid is to make sure there is a separate file for each iteration. The iteration number would be ideal
        # but I don't think I can access it from here.
        filename = "{}::{}::{}::{}".format(scenario_name, label, param_value, uuid.uuid4())

        # write the edgelist
        nx.write_edgelist(self.infection_graph, working_dir / '{}.{}'.format(filename, 'csv'), delimiter=',',
                          data=['weight', 'step'])
        # write the graphml
        nx.write_graphml(self.infection_graph, working_dir / '{}.{}'.format(filename, 'graphml'))
