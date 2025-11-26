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
        self.current_tick_tosend_packets = []

    def tick(self, t: int):
        if self.waiting_timer:
            self.waiting_timer.tick()


        # Process all tosend packets

        if len(self.current_tick_tosend_packets) == 1:
            self.send(t, self.current_tick_tosend_packets[0])
        elif len(self.current_tick_tosend_packets) > 1:
            _logger.info("@ " + str(t) + " collisions on #"  + str(len(self.current_tick_tosend_packets)) + "  " + str([n.sender_address for n in self.current_tick_tosend_packets]))

            for packet in self.current_tick_tosend_packets:
                self.nodes[packet.sender_address].on_collision()

        self.current_tick_tosend_packets = []


    def end_success_packet_delivery(self, t: int,  packet):

        # Reset sending timer
        self.waiting_timer = None

        sender= self.nodes[packet.sender_address]
        receiver = self.nodes[packet.receiver_address]

        sender.cw_timer = None
        sender.waiting_timer = None

        # Channel is now free
        self.status = ChannelStatus.CLEAR

        sender.status = NodeStatus.IDLE
        receiver.status = NodeStatus.IDLE

        sender.stats.append_stat(NodeStatType.SENT_PACKET, 1)
        receiver.stats.append_stat(NodeStatType.RECEIVED_PACKET, 1)

        _logger.info("Success sent packet from " + str(sender.node_id) +" to " + str(receiver.node_id) + " with size of " + str(packet.data_size) + " started @ " + str(t))


    def try_to_send(self, packet):
        self.current_tick_tosend_packets.append(packet)

    """
    This function must be syncronized
    """
    def send(self, t: int, packet):
        if self.status == ChannelStatus.BUSY:
            _logger.error("Channel busy")

        self.status = ChannelStatus.BUSY
        self.waiting_timer = start_timer(packet.duration, lambda channel, pkt: channel.end_success_packet_delivery(t,
            pkt
        ), self, packet)