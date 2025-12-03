import math
import random

from config_params import NodeStatus, PROBABILITY_OF_SENDING_PACKET, DIFS, ChannelStatus, NodeStatType, N_NODES, \
    DATA_MIN_SIZE, DATA_MAX_SIZE, PacketStatus, CW_MIN, SIFS, MIN_X, MAX_Y, MAX_X, MIN_Y
from models.node_stat import NodeStat
from models.packet import Packet, PacketType
from utils.timers import NodeTimer, NodeTimerType

import logging

_logger = logging.getLogger(__name__)

class Node2:


    def __init__(self, node_id: int, channel):
        self.node_id = node_id
        self.channel = channel
        self.nav_seconds = 0
        self.x = random.randint(MIN_X, MAX_X)
        self.y = random.randint(MIN_Y, MAX_Y)
        self.timeout_seconds: int | None = None
        self.stats = NodeStat(node_id)
        self.status = NodeStatus.IDLE
        self.timer: NodeTimer | None = None
        # This is the current packet buff (last one not confirmed to be sent sts)
        self.current_packet_buff: Packet | None = None
        # This is the packet buff generated before sending the RTS
        self.data_packet_buff: Packet | None = None

    def send_packet_from_timer(self, t):
        self.timeout_seconds = self.timer.packet.timeout
        self.channel.send_packet(t, self.timer.packet)

        match self.timer.packet.packet_type:
            case PacketType.DATA:
                self.stats.append_stat(NodeStatType.DATA_PACKET_GENERATED, 1)
            case _:
                self.stats.append_stat(NodeStatType.CONTROL_PACKET_GENERATED, 1)


    def distance(self, node):
        """Simple euclidean distance between two nodes"""
        return math.sqrt( (self.x - node.x)**2 + (self.y - node.y)**2 )

    def reset_timer(self):
        self.timer = None

    def reset_timeout(self):
        self.timeout_seconds = None

    def timer_tick(self, t):

        if self.nav_seconds > 0:
            self.nav_seconds -= 1

        if self.timeout_seconds is not None and self.timeout_seconds > 0:
            self.timeout_seconds -= 1

        if self.timeout_seconds is not None and self.timeout_seconds == 0:
            _logger.info("@ " + str(t) + " " + str(self.node_id) + " Timeout reached, we just re-try RTS entering cw")
            self.stats.append_stat(NodeStatType.TIMEOUT_RETRY, 1)
            self.status = NodeStatus.TIMEOUT
            self.enter_cw()
            self.timeout_seconds = None
            return

        if not self.timer:
            return

        if self.timer.timer_type == NodeTimerType.BACKOFF and self.channel_busy():
            # We freeze the clock if we are in CW and channel is busy
            return

        self.timer.waiting_ticks -= 1

        if self.timer.waiting_ticks == 0:
            match self.timer.timer_type:
                case NodeTimerType.BACKOFF:
                    # Here we are sending packet so let's change status

                    match self.status:
                        case NodeStatus.SENDING_RTS:
                            self.status = NodeStatus.WAITING_CTS
                        case NodeStatus.TIMEOUT:
                            self.status = NodeStatus.END_BACKOFF_TIMEOUT
                            self.reset_timer()
                            self.reset_timeout()
                            return
                        case _:
                            raise Exception("Invalid timer status " + str(self.status))

                    self.send_packet_from_timer(t)
                    self.reset_timer()
                case NodeTimerType.NORMAL_WAIT:

                    match self.status:
                        case NodeStatus.SENDING_RTS:
                            # We just wait DIFS for RTS
                            # We enter in cw with a RTS packet
                            self.current_packet_buff = self.build_rts_packet()
                            self.enter_cw()
                        case NodeStatus.SENDING_CTS:
                            self.status = NodeStatus.WAITING_DATA
                            self.send_packet_from_timer(t)
                            self.reset_timer()
                        case NodeStatus.SENDING_DATA:
                            self.status = NodeStatus.WAITING_ACK
                            self.send_packet_from_timer(t)
                            self.reset_timer()
                        case NodeStatus.SENDING_ACK:
                            self.status = NodeStatus.IDLE
                            self.send_packet_from_timer(t)
                            self.reset_timer()
                            self.reset_timeout()
                        case _:
                            raise Exception("Invalid timer status " + str(self.status))


    def enter_cw(self):

        cw_timer = CW_MIN

        if self.timer and self.timer.timer_type == NodeTimerType.BACKOFF:
            _logger.info("Resending perhaps, from backoff timer was: " + str(self.timer.cw_timer) +" and CW MIN IS "+ str(CW_MIN))
            cw_timer = self.timer.cw_timer * 2
            self.stats.append_stat(NodeStatType.CW_INCREASE, 1)
        else:
            self.stats.append_stat(NodeStatType.CW_ENTERS, 1)

        self.timer = NodeTimer(NodeTimerType.BACKOFF, cw_timer, self.current_packet_buff)

    def tick(self, t):

        self.timer_tick(t)

        match self.status:
            case NodeStatus.IDLE:
                # Only if idle let's gen packet with prob p
                if random.random() < PROBABILITY_OF_SENDING_PACKET:
                    # Ok we need to send a packet

                    self.data_packet_buff = self.build_data_packet()

                    if self.data_packet_buff is None:

                        # No nearby node found... skipping ?
                        return

                    if self.channel_busy():
                        self.status = NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR
                    else:
                        self.status = NodeStatus.SENDING_RTS
                        self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, DIFS)

            case NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR:
                if not self.channel_busy():
                    self.status = NodeStatus.SENDING_RTS
                    self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, DIFS)

            case NodeStatus.END_BACKOFF_TIMEOUT:
                if self.channel_busy():
                    self.status = NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR
                else:

                    # Ok here there is something to explain
                    # If the node hasn't nearby packets (too far for example)
                    # the data packet buff is none, so we can't send any RTS
                    # TODO: Implement something to modify range idk???
                    # For now I just check either the buff is none
                    # and then put the node in idle
                    if not self.data_packet_buff:
                        self.status = NodeStatus.IDLE
                        self.reset_timer()
                        self.reset_timeout()
                        return

                    self.status = NodeStatus.SENDING_RTS
                    self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, DIFS)


    def channel_busy(self):
        # Both physical and virtual carrier sensing
        return self.channel.status == ChannelStatus.BUSY or self.nav_seconds > 0




    # Packets

    def should_skip_packet(self, packet):
        if self.node_id != packet.receiver_address:
            # Update nav timer
            self.nav_seconds = packet.data_size
            return True
        return False

    def receive_packet(self, t, packet: Packet):
        if self.should_skip_packet(packet):
            return

        # If we receive the packet means we actually "can" receive it

        sender = self.channel.nodes[packet.sender_address]

        match packet.packet_type:
            case PacketType.DATA:
                sender.stats.append_stat(NodeStatType.DATA_PACKET_SENT, 1)
            case _:
                 sender.stats.append_stat(NodeStatType.CONTROL_PACKET_SENT, 1)

        match packet.packet_type:
            case PacketType.RTS:
                if not self.status.can_start_new_connections():
                    _logger.error("@ " + str(t) + " " + str(self.node_id) + " Received RTS while not idle, skipping packet with status " + str(self.status) + "")
                else:
                    self.status = NodeStatus.SENDING_CTS
                    self.current_packet_buff = self.build_cts_packet(packet)
                    self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, SIFS, self.current_packet_buff)

            case PacketType.CTS:

                if self.status != NodeStatus.WAITING_CTS:
                    raise Exception("Invalid status for CTS packet " + str(self.status) + " - " + str(self.node_id))
                else:
                    self.reset_timeout()
                    self.status = NodeStatus.SENDING_DATA
                    self.current_packet_buff = self.data_packet_buff
                    self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, SIFS, self.current_packet_buff)

            case PacketType.DATA:

                if self.status != NodeStatus.WAITING_DATA:
                    raise Exception("Invalid status for DATA packet " + str(self.status))
                else:
                    self.reset_timeout()
                    self.status = NodeStatus.SENDING_ACK
                    self.current_packet_buff = self.build_ack_packet(packet)
                    self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, SIFS, self.current_packet_buff)

            case PacketType.ACK:

                if self.status != NodeStatus.WAITING_ACK:
                    raise Exception("Invalid status for ACK packet " + str(self.status))
                else:
                    self.reset_timeout()
                    self.reset_timer()
                    self.status = NodeStatus.IDLE
                    self.current_packet_buff = None
                    self.data_packet_buff = None
                    _logger.info("Verified ACK for packet " + str(packet) + "")



        _logger.info("@ " + str(t) + " " + "Node " + str(self.node_id) + " Received packet " + str(packet))




    def build_data_packet(self) -> None | Packet:

        available_nodes = self.channel.get_nodes_from_pos(self)

        if len(available_nodes) == 0:
            return None

        # Let's pick a random node
        received_node = random.choice([n.node_id for n in available_nodes])

        data_size = random.randint(DATA_MIN_SIZE, DATA_MAX_SIZE)

        pkt = Packet(PacketType.DATA, self.node_id, received_node, data_size)
        pkt.attach_crc()

        return pkt


    def build_ack_packet(self, received_packet: Packet) -> Packet:

        ack =  Packet(PacketType.ACK, self.node_id, received_packet.sender_address, DATA_MIN_SIZE // 4)
        ack.attach_crc()

        return ack

    def build_cts_packet(self, rts_packet: Packet) -> Packet:
        cts = Packet(PacketType.CTS, self.node_id, rts_packet.sender_address, DATA_MIN_SIZE // 4)
        cts.attach_crc()

        return cts

    def build_rts_packet(self) -> Packet:
        if not self.data_packet_buff:
            raise Exception("No data packet buff found for RTS " + str(self.node_id)  + " - " + str(self.status))

        rts = Packet(PacketType.RTS, self.node_id, self.data_packet_buff.receiver_address, DATA_MIN_SIZE // 4)
        rts.attach_crc()

        return rts