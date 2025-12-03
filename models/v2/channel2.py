from config_params import ChannelStatus, ChannelStatType, NodeStatType, DISTANCE_WHICH_A_NODE_CAN_EAR_OTHER_NODE
from models.channel_stat import ChannelStat
from models.packet import Packet, PacketType

import logging

_logger = logging.getLogger(__name__)


class Channel2:


    def __init__(self):
        self.nodes = []
        self.stats = ChannelStat(self)
        self.status = ChannelStatus.CLEAR
        self.sending_packet: Packet | None = None
        self.sending_seconds = 0

    def tick(self, t):

        if self.sending_packet is None:
            return

        if self.sending_seconds > 0:
            self.sending_seconds -= 1

        if self.sending_seconds == 0:

            curr_packet = self.sending_packet

            self.sending_packet = None
            self.status = ChannelStatus.CLEAR

            sender = self.nodes[curr_packet.sender_address]

            available_nodes = self.get_nodes_from_pos(sender)

            [n.receive_packet(t, curr_packet) for n in available_nodes if n.status.can_receive_packet()]



    def get_nodes_from_pos(self, source):
        """
        Get available nodes from a given node source
        :param source: the node source
        :return: the list of earable nodes
        """
        res = []

        for node in self.nodes:
            if node.node_id == source.node_id:
                continue

            if node.distance(source) <= DISTANCE_WHICH_A_NODE_CAN_EAR_OTHER_NODE:
               res.append(node)


        return res

    def send_packet(self, t, packet: Packet):

        sender = self.nodes[packet.sender_address]

        if self.status == ChannelStatus.BUSY:

            match packet.packet_type:
                case PacketType.DATA:
                    sender.stats.append_stat(NodeStatType.DATA_PACKET_LOSS, 1)
                case _:
                    sender.stats.append_stat(NodeStatType.CONTROL_PACKET_LOSS, 1)


            _logger.error("@" + str(t) + " Channel is busy packet " + str(packet) +" is lost")
        else:
            _logger.info("Setting to busy @ " + str(t) + " Channel is sending packet " + str(packet))
            self.sending_packet = packet
            self.status = ChannelStatus.BUSY
            self.sending_seconds = packet.data_size



