from config_params import PROBABILITY_OF_SENDING_PACKET, DIFS, N_NODES, DATA_MIN_SIZE, DATA_MAX_SIZE, NodeStatus, \
    NodeStatType, CW_MIN, SIFS, ACK_MAX_WAIT_TIME
from enum import Enum
from models.channel import Channel, ChannelStatus
import logging
import random

from models.node_stat import NodeStat
from models.packet import Packet, PacketType
from utils.waiting_timer import start_timer, WaitingTimer, ContentionWindowTimer, start_cw_timer

_logger = logging.getLogger(__name__)






class Node:

    def __init__(self, channel: Channel, node_id: int):
        self.node_id = node_id
        self.channel = channel
        self.status = NodeStatus.IDLE
        self.stats = NodeStat(node_id)
        self.cw_timer: ContentionWindowTimer | None = None
        self.waiting_timer: WaitingTimer | None = None
        self.data_packet_buff: Packet | None = None
        self.ack_packet_buff: Packet | None = None


    def reset_node_state(self):
        self.status = NodeStatus.IDLE
        self.cw_timer = None
        self.waiting_timer = None
        self.data_packet_buff = None
        self.ack_packet_buff = None


    def receive_packet(self, t: int, packet: Packet):

        # Check if we are receiving ack

        if self.status == NodeStatus.WAITING_ACK:
            if packet.packet_type == PacketType.ACK:
                # Ok we ackkkk this
                # Recalc crc
                if packet.verify_crc():
                    _logger.info("Verified CRC for packet from " + str(packet.sender_address) +" to " + str(packet.receiver_address) +" CRC=" + str(packet.crc))
                    self.reset_node_state()
                else:
                    _logger.error("CRC FAILED TO VERIFY FOR PACKET: " + str(packet) + "")
            else:
                _logger.error("We are leaving the packet: " + str(packet) + " because it is not an ACK from" + str(packet.sender_address))

        _logger.info(str(self.node_id) + " Received packet from node " + str(packet.sender_address) +  " type " + str(packet.packet_type))


        if packet.packet_type == PacketType.DATA:
            # We need to send packet without sensing the channel with the ACK
            # This is unsure so we can actually lose the ACK packet
            self.ack_packet_buff = self.build_ack_packet(packet)
            self.status = NodeStatus.PACKET_RECEIVED_READY_TO_SEND_ACK

            sender = self.channel.nodes[packet.sender_address]

            sender.status = NodeStatus.WAITING_ACK
            sender.waiting_timer = start_timer(ACK_MAX_WAIT_TIME, lambda node: node.retransmit_data(), sender)



    def retransmit_data(self):
        _logger.info("Retransmitting data packet for ack lost from " + str(self.node_id) +" to " + str(self.data_packet_buff.receiver_address))
        self.stats.append_stat(NodeStatType.RETRANSMITTED_PACKET_AFTER_ACK_LOST, 1)
        self.wait_channel_clear_and_send()

    def build_ack_packet(self, received_packet: Packet) -> Packet:

        self.stats.append_stat(NodeStatType.GENERATED_PACKETS, 1)

        ack =  Packet(PacketType.ACK, self.node_id, received_packet.sender_address, DATA_MIN_SIZE // 4)
        ack.attach_crc()

        return ack


    def build_data_packet(self) -> Packet:

        self.stats.append_stat(NodeStatType.GENERATED_PACKETS, 1)

        # Let's pick a random node
        received_node = random.choice([x for x in range(0, N_NODES) if x != self.node_id])
        
        data_size = random.randint(DATA_MIN_SIZE, DATA_MAX_SIZE)

        return Packet(PacketType.DATA, self.node_id, received_node, data_size)


    def on_collision(self, packet: Packet):
        match self.status:
            case NodeStatus.CONTENTION_WINDOW:
                new_cw_size = self.cw_timer.cw_size *2
                self.cw_timer = start_cw_timer(self.channel, new_cw_size, lambda node: node.send_data(), self)
                self.stats.append_stat(NodeStatType.CW_INCREASE, 1)
                return
            case _:
                if packet.packet_type == PacketType.DATA:
                    # CW
                    self.enter_cw()
                    return

    def send_data(self):

        if not self.data_packet_buff:
            raise Exception("No data packet buff found")

        self.channel.try_to_send(self.data_packet_buff)

    def wait_DIFS(self):
        self.status = NodeStatus.WAITING_DIFS_FOR_SENDING
        self.waiting_timer = start_timer(DIFS, lambda node: node.wait_channel_clear_and_send(), self)

    def wait_channel_clear_and_send(self):


        # Stop waiting
        self.waiting_timer = None

        match self.channel.status:
            case ChannelStatus.BUSY:
                # Wait until medium is clear
                self.status = NodeStatus.WAIT_UNTIL_CHANNEL_IS_CLEAR
            case ChannelStatus.CLEAR:
                self.send_data()

    def enter_cw(self):
        self.cw_timer = start_cw_timer(self.channel, CW_MIN, lambda node: node.send_data(), self)
        self.status = NodeStatus.CONTENTION_WINDOW
        self.stats.append_stat(NodeStatType.CW_ENTERS, 1)

    def send_ack(self, t: int):

        if not self.ack_packet_buff:
            raise Exception("No ack packet buff found")


        self.channel.send(t, self.ack_packet_buff)
        self.ack_packet_buff = None
        self.waiting_timer = None

    def tick(self, t: int):

        # Tick timers
        if self.waiting_timer:
            self.waiting_timer.tick()

        if self.cw_timer:
            if self.cw_timer.wait_ticks > 0:
                self.stats.append_stat(NodeStatType.CW_TOTAL_WAITING_TICKS_TIME, 1)
            self.cw_timer.tick()

        match self.status:
            case NodeStatus.IDLE:
                if random.random() < PROBABILITY_OF_SENDING_PACKET:

                    # Ok we got the probability to transmit a packet
                    self.data_packet_buff = self.build_data_packet()

                    match self.channel.status:
                        case ChannelStatus.CLEAR:
                            # If the medium is clear we wait a DIFS
                            self.wait_DIFS()
                        case ChannelStatus.BUSY:
                            self.status = NodeStatus.WAIT_UNTIL_CHANNEL_IS_CLEAR
            case NodeStatus.WAIT_UNTIL_CHANNEL_IS_CLEAR:
                if self.channel.status == ChannelStatus.CLEAR:
                    # Here we need to implement backoff
                    self.enter_cw()
            case NodeStatus.PACKET_RECEIVED_READY_TO_SEND_ACK:
                self.status = NodeStatus.SENDING_PACKET
                self.waiting_timer = start_timer(SIFS, lambda node: node.send_ack(t), self)





