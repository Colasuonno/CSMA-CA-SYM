import random

from models.v2.node2 import Node2
from models.v2.channel2 import Channel2
from config_params import N_NODES, SIMULATION_TICKS, NodeStatus
import utils.waiting_timer
import logging

_logger = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)




if __name__ == '__main__':

    channel = Channel2()

    for n in range(N_NODES):
        channel.nodes.append(Node2(n, channel))

    _logger.info("Init all nodes")

    for t in range(SIMULATION_TICKS):

        # We need to tick all nodes, we randomly do it

        starting_node = random.randint(0, N_NODES-1)

        for n in range(N_NODES):
            channel.nodes[(n + starting_node) % N_NODES].tick(t)


        channel.tick(t)


    _logger.info("Simulation ended")

    for n in range(N_NODES):
        channel.nodes[n].stats.print_stats()

    #channel.stats.print_stats()
