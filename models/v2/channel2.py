from config_params import ChannelStatus, ChannelStatType, NodeStatType
from models.packet import Packet, PacketType

import logging

_logger = logging.getLogger(__name__)


class Channel2:


    def __init__(self):
        self.nodes = []
        self.status = ChannelStatus.CLEAR
        self.sending_packet: Packet | None = None
        self.sending_seconds = 0

    def tick(self, t):

        if self.sending_packet is None:
            return

        if self.sending_seconds > 0:
            self.sending_seconds -= 1

        if self.sending_seconds == 0:
            _logger.info("@ " + str(t) + " End trasmission Channel is sending packet " + str(self.sending_packet))
            [n.receive_packet(t, self.sending_packet) for n in self.nodes if n.status.can_receive_packet()]

            self.sending_packet = None
            self.status = ChannelStatus.CLEAR


    def send_packet(self, packet: Packet):

        sender = self.nodes[packet.sender_address]

        if self.status == ChannelStatus.BUSY:

            match packet.packet_type:
                case PacketType.DATA:
                    sender.stats.append_stat(NodeStatType.DATA_PACKET_LOSS, 1)
                case _:
                    sender.stats.append_stat(NodeStatType.CONTROL_PACKET_LOSS, 1)


            _logger.error("Channel is busy packet " + str(packet) +" is lost")
        else:
            self.sending_packet = packet
            self.status = ChannelStatus.BUSY
            self.sending_seconds = packet.data_size



