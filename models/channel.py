from enum import Enum
from typing import List
import multiprocessing
from utils.waiting_timer import start_timer
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
        self.shared_state['waiting_timer'] = None

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

        waiting_timer = self.shared_state['waiting_timer']

        if waiting_timer:
            _logger.debug("Waiting timer tick ")
            waiting_timer.tick()

    def waiting_timer_finished_trigger(self, packet):

        _logger.error("Wait sending timer for pckt " + str(packet.sender_address))

        self.waiting_timer = None
        self.set_status(ChannelStatus.CLEAR)
        self.nodes[packet.receiver_address].receive_packet(packet)

    """
    This function must be syncronized
    """
    def send(self, packet):
        if self.get_status() == ChannelStatus.BUSY:
            _logger.error("Channel busy")

        _logger.info("Sending " + str(packet.receiver_address) + " -. pd " + str(packet.duration))

        self.set_status(ChannelStatus.BUSY)
        self.shared_state["waiting_timer"] = start_timer(packet.duration, lambda params: _logger.info("WAit " + str(params[0]) +" - " + str(params[1])), (self, packet))