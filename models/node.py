from config_params import PROBABILITY_OF_SENDING_PACKET, DIFS, N_NODES, DATA_MIN_SIZE, DATA_MAX_SIZE, NodeStatus, \
    NodeStatType, CW_MIN, SIFS, ACK_MAX_WAIT_TIME, PacketStatus
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
        self.data_packet_status: PacketStatus | None = None
        self.cw_timer: ContentionWindowTimer | None = None
        self.waiting_timer: WaitingTimer | None = None
        self.data_packet_buff: Packet | None = None
        self.ack_packet_buff: Packet | None = None
        self.cts_packet_buff: Packet | None = None


    def reset_node_state(self):
        self.status = NodeStatus.IDLE
        self.cw_timer = None
        self.waiting_timer = None
        self.data_packet_buff = None
        self.ack_packet_buff = None


    def receive_packet(self, t: int, packet: Packet):

        if not packet.verify_crc(self.node_id):
            return

        # Check if we are receiving ack
        _logger.info(str(self.node_id) + " with status " + str(self.status) +  " Received packet from node " + str(packet.sender_address) +  " type " + str(packet.packet_type))

        sender = self.channel.nodes[packet.sender_address]

        match packet.packet_type:
            case PacketType.ACK:
                if self.status == NodeStatus.WAITING_ACK:
                    _logger.info("Verified CRC for packet from " + str(packet.sender_address) + " to " + str(
                        packet.receiver_address) + " CRC=" + str(packet.crc))
                    self.reset_node_state()
                else:
                    _logger.error("Received an ACK from " + str(packet.sender_address) + " when not waiting for ACK")
            case PacketType.DATA:

                if self.status == NodeStatus.WAITING_DATA:
                    # We need to send packet without sensing the channel with the ACK
                    # This is unsure so we can actually lose the ACK packet
                    self.ack_packet_buff = self.build_ack_packet(packet)
                    self.status = NodeStatus.SENDING_PACKET
                    self.waiting_timer = start_timer(SIFS, lambda node: node.send_ack(t), self)

                    sender.status = NodeStatus.WAITING_ACK
                    # This timer will be deleted with Node#reset_node_state() if packet is ack is received and validated by CRC
                    sender.waiting_timer = start_timer(ACK_MAX_WAIT_TIME, lambda node: node.retransmit_data(), sender)
                else:
                    _logger.error("Received DATA packet from " + str(packet.sender_address) + " when not waiting for DATA")

            case PacketType.RTS:
                # RTS Received, we need to send CTS after sifs
                # Don't carrier sense after SIFS and send directly CTS

                sender.data_packet_status = PacketStatus.SENT_RTS
                sender.status = NodeStatus.WAITING_CTS
                self.cts_packet_buff = self.build_cts_packet(packet)
                self.status = NodeStatus.SENDING_PACKET
                self.waiting_timer = start_timer(SIFS, lambda node: node.send_cts(t), self)


            case PacketType.CTS:

                if self.status == NodeStatus.WAITING_CTS:
                    # Data buff is alreadyy generated @ this point so
                    self.status = NodeStatus.WAITING_DATA
                    sender.status = NodeStatus.SENDING_PACKET
                    self.waiting_timer = start_timer(SIFS, lambda node: node.send_data(), self)
                else:
                    _logger.error("Got CTS But not expecting it.....")










    def retransmit_data(self):
        _logger.info("Retransmitting data packet for ack lost from " + str(self.node_id) +" to " + str(self.data_packet_buff.receiver_address))
        self.stats.append_stat(NodeStatType.RETRANSMITTED_PACKET_AFTER_ACK_LOST, 1)
        self.wait_channel_clear_and_send()

    def build_rts_packet(self) -> Packet:
        if not self.data_packet_buff:
            raise Exception("No data packet buff found for RTS")

        rts = Packet(PacketType.RTS, self.node_id, self.data_packet_buff.receiver_address, DATA_MIN_SIZE // 4)
        rts.attach_crc()

        return rts

    def build_cts_packet(self, rts_packet: Packet) -> Packet:
        cts = Packet(PacketType.CTS, self.node_id, rts_packet.sender_address, DATA_MIN_SIZE // 4)
        cts.attach_crc()

        return cts

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

        self.data_packet_status = PacketStatus.GENERATED

        return Packet(PacketType.DATA, self.node_id, received_node, data_size)


    def on_collision(self, packet: Packet):
        match self.status:
            case NodeStatus.CONTENTION_WINDOW:
                new_cw_size = self.cw_timer.cw_size *2
                self.cw_timer = start_cw_timer(self.channel, new_cw_size, lambda node: node.send_data(), self)
                self.stats.append_stat(NodeStatType.CW_INCREASE, 1)
            case _:
                self.enter_cw()
                return

    def send_data(self):

        # Based on the node status we need to send different packets

        packet_buff = None

        match self.data_packet_status:
            case PacketStatus.GENERATED:
                # We generated the packet but didn't send RTS, so we need to send RTS
                packet_buff = self.build_rts_packet()
            case PacketStatus.SENT_RTS:
                # We are here since we received CTS and we are ready to send
                packet_buff = self.data_packet_buff
            case PacketStatus.SENT_DATA:
                raise Exception("Already sent and acknlowdged packet, wtf am i called for???")

        self.channel.try_to_send(packet_buff)

    def wait_DIFS_and_send(self):
        self.status = NodeStatus.WAITING_DIFS
        self.waiting_timer = start_timer(DIFS, lambda node: node.wait_channel_clear_and_send(), self)

    def wait_channel_clear_and_send(self):


        # Stop waiting
        self.waiting_timer = None

        match self.channel.status:
            case ChannelStatus.BUSY:
                # Wait until medium is clear
                self.status = NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR
            case ChannelStatus.CLEAR:
                self.send_data()

    def enter_cw(self):
        self.cw_timer = start_cw_timer(self.channel, CW_MIN, lambda node: node.send_data(), self)
        self.status = NodeStatus.CONTENTION_WINDOW
        self.stats.append_stat(NodeStatType.CW_ENTERS, 1)

    def send_cts(self, t: int):

        if not self.cts_packet_buff:
            raise Exception("No cts packet buff found")


        self.channel.send(t, self.cts_packet_buff)
        self.cts_packet_buff = None
        self.waiting_timer = None

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
                            self.wait_DIFS_and_send()
                        case ChannelStatus.BUSY:
                            self.status = NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR
            case NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR:
                if self.channel.status == ChannelStatus.CLEAR:
                    # Here we need to implement backoff
                    self.enter_cw()






