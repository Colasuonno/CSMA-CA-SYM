from enum import Enum
from typing import List
import multiprocessing

import logging

_logger = logging.getLogger(__name__)

class ChannelStatus(Enum):
    CLEAR = 0
    BUSY = 1


class Channel:

    def __init__(self):
        self.manager = multiprocessing.Manager()
        self.nodes = []
        self.shared_state = self.manager.dict()
        self.shared_state['status'] = ChannelStatus.CLEAR
        self.timer_until_clear = 0

    def start_all_nodes(self):
        for node in self.nodes:
            node.start()

    def get_status(self):
        """Helper method to get current status as enum"""
        return ChannelStatus(self.shared_state['status'])

    def set_status(self, new_status: ChannelStatus):
        """Helper method to set status"""
        self.shared_state['status'] = new_status.value

    def tick(self):
        match self.get_status():
            case ChannelStatus.BUSY:
                if self.timer_until_clear <= 0:
                    self.set_status(ChannelStatus.CLEAR)
                    _logger.info("Channel cleared")
                else:
                    self.timer_until_clear -= 1

    def send(self, packet):
        if self.get_status() == ChannelStatus.BUSY:
            _logger.error("Channel busy")

        _logger.info("Sending " + str(packet.receiver_address))

        self.set_status(ChannelStatus.BUSY)
        self.timer_until_clear = packet.duration
        self.nodes[packet.receiver_address].receive_packet(packet)