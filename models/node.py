from config_params import PROBABILITY_OF_SENDING_PACKET, DIFS
from enum import Enum
import logging
import multiprocessing
import random

_logger = logging.getLogger(__name__)



class NodeStatus(Enum):

    IDLE = 0
    WAITING_DIFS_FOR_SENDING = 3
    SENSE = 1
    SENDING_PACKET = 2


class Node:

    def __init__(self, node_id: int):
        self.node_id = node_id
        self.status = NodeStatus.IDLE
        self.t = 0 # t is timer
        self.waiting_timer = 0
        process = multiprocessing.Process(target=self.tick, daemon=True)
        process.start()
        _logger.info("Started node " + str(self.node_id) +" at thread " + str(process.pid))


    def tick(self):
        while True:

            match self.status:
                case NodeStatus.IDLE:
                    if random.random() < PROBABILITY_OF_SENDING_PACKET:
                        # We want to send a packet
                        _logger.info("Node " + str(self.node_id) + " wants to send a packet")
                        self.status = NodeStatus.WAITING_DIFS_FOR_SENDING
                        self.waiting_timer = DIFS
                case NodeStatus.WAITING_DIFS_FOR_SENDING:

                    if self.waiting_timer > 0:
                        self.waiting_timer -= 1
                    else:
                        self.waiting_timer = 0



