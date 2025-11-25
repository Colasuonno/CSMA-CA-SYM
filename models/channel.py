from enum import Enum

from config_params import ChannelStatus, NodeStatus, NodeStatType
from utils.waiting_timer import start_timer, WaitingTimer
import logging

_logger = logging.getLogger(__name__)




class Channel:

    def __init__(self):
        self.nodes = []
        self.status = ChannelStatus.CLEAR
        self.waiting_timer: WaitingTimer | None = None


    def tick(self):
        if self.waiting_timer:
            self.waiting_timer.tick()

    def end_success_packet_delivery(self, packet):

        # Reset sending timer
        self.waiting_timer = None

        sender= self.nodes[packet.sender_address]
        receiver = self.nodes[packet.receiver_address]

        # Channel is now free
        self.status = ChannelStatus.CLEAR

        sender.status = NodeStatus.IDLE
        receiver.status = NodeStatus.IDLE

        sender.stats.append_stat(NodeStatType.SENT_PACKET, 1)
        receiver.stats.append_stat(NodeStatType.RECEIVED_PACKET, 1)




    """
    This function must be syncronized
    """
    def send(self, packet):
        if self.status == ChannelStatus.BUSY:
            _logger.error("Channel busy")

        self.status = ChannelStatus.BUSY
        self.waiting_timer = start_timer(packet.duration, lambda channel, pkt: channel.end_success_packet_delivery(
            pkt
        ), self, packet)