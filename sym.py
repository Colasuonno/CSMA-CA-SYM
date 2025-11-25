from models.node import Node
from models.channel import Channel
from config_params import N_NODES, SIMULATION_TICKS
import utils.waiting_timer
import logging

_logger = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)




if __name__ == '__main__':

    channel = Channel()

    for n in range(N_NODES):
        channel.nodes.append(Node(channel, n))

    channel.start_all_nodes()
    _logger.info("Init all nodes")


    for t in range(SIMULATION_TICKS):
        channel.tick()

    _logger.info("Simulation ended")

    # Close all process
    for n in range(N_NODES):
        channel.nodes[n].process.terminate()

