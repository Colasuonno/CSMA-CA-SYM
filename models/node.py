from config_params import PROBABILITY_OF_SENDING_PACKET, DIFS, N_NODES, DATA_MIN_SIZE, DATA_MAX_SIZE
from enum import Enum
from models.channel import Channel, ChannelStatus
import logging
import multiprocessing
import random

from models.packet import Packet, PacketType

_logger = logging.getLogger(__name__)



class NodeStatus(Enum):

    IDLE = 0
    WAITING_DIFS_FOR_SENDING = 3
    SENSE = 1
    SENDING_PACKET = 2
    WAIT_UNTIL_CHANNEL_IS_CLEAR = 4


class Node:

    def __init__(self, channel: Channel, node_id: int):
        self.node_id = node_id
        self.channel = channel
        self.status = NodeStatus.IDLE
        self.t = 0 # t is timer
        self.waiting_timer = 0
        self.data_packet_buff: Packet | None = None

    def start(self):
        process = multiprocessing.Process(target=self.tick, daemon=True)
        process.start()
        _logger.info("Started node " + str(self.node_id) + " at thread " + str(process.pid))


    def receive_packet(self, packet: Packet):
        _logger.info("Received packet from node " + str(packet.sender_address) +  " duration " + str(packet.duration))

    def build_data_packet(self) -> Packet:

        # Let's pick a random node
        received_node = random.choice([x for x in range(0, N_NODES) if x != self.node_id])
        
        data_size = random.randint(DATA_MIN_SIZE, DATA_MAX_SIZE)
        
        _logger.info("Node " + str(self.node_id) + " generated data packet to node " + str(received_node))
        
        return Packet(PacketType.DATA, self.node_id, received_node, data_size)


    def build_rts(self) -> Packet:
        assert self.data_packet_buff is not None    
        return Packet(PacketType.RTS, self.node_id, self.data_packet_buff.receiver_address, self.data_packet_buff.data_size)


    def send_data(self):
        self.data_packet_buff = self.build_data_packet()
        self.channel.send(self.data_packet_buff)

    def request_to_send(self):
        self.data_packet_buff = self.build_data_packet()


    def tick(self):
        while True:

            match self.status:
                case NodeStatus.IDLE:
                    if random.random() < PROBABILITY_OF_SENDING_PACKET:

                        if self.channel.get_status() == ChannelStatus.BUSY:
                            # if busy wait til trasmission ends
                            self.status = NodeStatus.WAIT_UNTIL_CHANNEL_IS_CLEAR
                            continue

                        # We want to send a packet
                        _logger.info("Node " + str(self.node_id) + " wants to send a packet")
                        self.status = NodeStatus.WAITING_DIFS_FOR_SENDING
                        self.waiting_timer = DIFS

                case NodeStatus.WAITING_DIFS_FOR_SENDING:
                    if self.waiting_timer > 0:
                        self.waiting_timer -= 1
                    else:

                        if self.channel.get_status() == ChannelStatus.BUSY:
                            # if busy wait til trasmission ends
                            self.status = NodeStatus.WAIT_UNTIL_CHANNEL_IS_CLEAR
                            continue

                        self.waiting_timer = 0
                        self.send_data()



