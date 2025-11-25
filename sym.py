import random

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

    _logger.info("Init all nodes")

    for t in range(SIMULATION_TICKS):

        # We need to tick all nodes, we randomly do it

        starting_node = random.randint(0, N_NODES-1)

        for n in range(N_NODES):
            channel.nodes[(n + starting_node) % N_NODES].tick()


        channel.tick()


    _logger.info("Simulation ended")

    for n in range(N_NODES):
        channel.nodes[n].stats.print_stats()
