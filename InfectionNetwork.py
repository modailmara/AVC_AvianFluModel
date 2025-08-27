from constants import Location, HospitalDepartment


class InfectionNode:
    """
    Represents a node in the infection network.

    Corresponds to an agent that has been infected at least once.
    """
    def __init__(self, agent):
        self.agent = agent

        self.in_infections = []  # list of incoming edges: events that infected this agent
        self.out_infections = []  # list of outgoing edges: events that this agent infected

    def add_in_infection(self, infection_edge):
        """
        New infection for this agent. Add the edge that records where and when.
        :param infection_edge: The infection network edge to add
        :type infection_edge: InfectionEdge object
        """
        self.in_infections.append(infection_edge)

    def add_out_infection(self, infection_edge):
        """
        This agent has infected another agent. Add the edge that records where and when.
        :param infection_edge: The infection network edge to add
        :type infection_edge: InfectionEdge object
        """
        self.out_infections.append(infection_edge)


class InfectionEdge:
    """
    An edge in the infection network. Records the where and when of an infection event.
    """
    def __init__(self, source_node, infected_node, time_step, location=Location.COMMUNITY, department=None):
        """

        :param source_node: Node for the agent that caused the infection
        :type source_node: InfectionNode
        :param infected_node: Node that was infected
        :type infected_node: InfectionNode
        :param location: Location of the infection event. Default is COMMUNITY.
        :type location: Location
        :param time_step: Model time step that the infection event occured
        :type time_step: int
        :param department: If the location is HOSPITAL, the department where the infection occurred.
        :type department: HospitalDepartment
        """
        self.source_node = source_node
        self.infected_node = infected_node

        self.time = time_step
        self.location = location
        self.department = department


class InfectionNetwork:
    """
    Keeps a record of the complete infection network - who, when, and where of all infection events.
    """

    def __init__(self):
        self.nodes = {}

    def add_source(self, source_agent):
        """
        Adds a source of infection to the network, i.e. no incoming edges
        :param source_agent:
        :type source_agent:
        """
        # make sure it's not already in the network
        if source_agent.id not in self.nodes:
            node = InfectionNode(source_agent)
            self.nodes[source_agent.id] = node

    def add_infection_event(self, source_agent, infected_agent, time_step,
                            location=Location.COMMUNITY, department=None):
        """
        Adds an infection event to the network: source <=> edge <=> infected.
        :param source_agent:
        :type source_agent:
        :param infected_agent:
        :type infected_agent:
        :param time_step:
        :type time_step:
        :param location:
        :type location:
        :param department:
        :type department:
        :return:
        :rtype:
        """
