import random

from models.channel_stat import ChannelStat
from models.v2.node2 import Node2
from models.v2.karmedbandit_rl_node import RLKArmedBanditNode
from models.v2.qlearning_rl_node import RLQLearningNode
from models.v2.channel2 import Channel2
from config_params import N_NODES, SIMULATION_TICKS, NodeStatus
import logging

_logger = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)




if __name__ == '__main__':


    channel = Channel2()

    for n in range(N_NODES):
        channel.nodes.append(RLKArmedBanditNode( n, channel))

    _logger.info("Init all nodes")

    for t in range(SIMULATION_TICKS):

        if t % 10000 == 0:
            _logger.info(f"@{t}")
            channel.stats.print_stats()

        # We need to tick all nodes, we randomly do it

        starting_node = random.randint(0, N_NODES-1)

        for n in range(N_NODES):
            channel.nodes[(n + starting_node) % N_NODES].tick(t)


        channel.tick(t)


    _logger.info("Simulation ended")

    for n in range(N_NODES):
        #channel.nodes[n].stats.print_stats()
        channel.nodes[n].print_policy(channel)

    channel.stats.print_stats()
