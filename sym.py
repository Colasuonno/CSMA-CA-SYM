from models.node import Node
from config_params import N_NODES, SIMULATION_TICKS
import logging
_logger = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


if __name__ == '__main__':

    nodes = []

    for n in range(N_NODES):
        nodes.append(Node(n))


    _logger.info("Init all nodes")


    for t in range(SIMULATION_TICKS):
        pass

    _logger.info("Simulation ended")
