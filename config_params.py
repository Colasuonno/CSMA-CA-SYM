from enum import Enum
from unittest import case

N_NODES = 100
SIMULATION_TICKS = 10000
PROBABILITY_OF_SENDING_PACKET = 0.01
SIFS = 2  # 2 ticks
DIFS = 5 * SIFS + 5
DATA_MIN_SIZE = 20
DATA_MAX_SIZE = 100
ACK_MAX_WAIT_TIME = DATA_MIN_SIZE


CW_MIN = 31

# SPATIAL SETTINGS
# This settings exists so nodes position are generated randomly, so
# they could ear each other or not, in this case we can add some
# "collisions" inductions, more is the space range, more likely is to not ear others nodes
# of course we can talk only with specific nodes
# TODO: Modify sending speed based on distance

DISTANCE_WHICH_A_NODE_CAN_EAR_OTHER_NODE = 10

MIN_X = 0
MAX_X = 100

MIN_Y = 0
MAX_Y = 100



class PacketStatus(Enum):
    GENERATED = 0
    SENT_RTS = 1
    RECEIVED_RTS = 2
    SENT_CTS = 3
    RECEIVED_CTS = 4
    SENT_DATA = 5
    RECEIVED_DATA = 6




class ChannelStatType(Enum):

    TOTAL_GENERATED_PACKETS = 0
    TOTAL_SENT_PACKETS = 1
    TOTAL_LOSS_PACKETS = 2
    TOTAL_DATA_PACKET_SENT = 6
    AVG_PACKET_LOSS_PERCENTAGE = 3
    TOTAL_TIMEOUT_NODES = 4
    TOTAL_NODES = 5
    # NEAR NODES = NODES WITH DISTANCE <= DISTANCE_WHICH_A_NODE_CAN_EAR_OTHER_NODE
    AVG_NEAR_NODES = 7

class NodeStatType(Enum):
    CONTROL_PACKET_SENT = 1
    CONTROL_PACKET_LOSS = 2
    CONTROL_PACKET_GENERATED = 10
    DATA_PACKET_GENERATED = 9
    DATA_PACKET_SENT = 0
    DATA_PACKET_LOSS = 3
    TOTAL_PACKET_GENERATED = 11
    TOTAL_PACKET_SENT = 6
    TOTAL_PACKET_LOSS = 4
    PACKET_LOSS_PERCENTAGE = 5
    CW_ENTERS = 7
    CW_INCREASE = 8
    TIMEOUT_RETRY = 12


DEFAULT_CHANNEL_STATS = {
    ChannelStatType.AVG_NEAR_NODES: 0,
    ChannelStatType.TOTAL_DATA_PACKET_SENT: 0,
    ChannelStatType.TOTAL_GENERATED_PACKETS: 0,
    ChannelStatType.TOTAL_SENT_PACKETS: 0,
    ChannelStatType.TOTAL_LOSS_PACKETS: 0,
    ChannelStatType.AVG_PACKET_LOSS_PERCENTAGE: 0,
    ChannelStatType.TOTAL_TIMEOUT_NODES: 0,
    ChannelStatType.TOTAL_NODES: N_NODES
}

DEFAULT_NODE_STATS = {
    NodeStatType.CONTROL_PACKET_SENT: 0,
    NodeStatType.CONTROL_PACKET_LOSS: 0,
    NodeStatType.CONTROL_PACKET_GENERATED: 0,
    NodeStatType.DATA_PACKET_SENT: 0,
    NodeStatType.DATA_PACKET_LOSS: 0,
    NodeStatType.DATA_PACKET_GENERATED: 0,
    NodeStatType.TOTAL_PACKET_SENT: 0,
    NodeStatType.TOTAL_PACKET_LOSS: 0,
    NodeStatType.TOTAL_PACKET_GENERATED: 0,
    NodeStatType.PACKET_LOSS_PERCENTAGE: 0,
    NodeStatType.CW_ENTERS: 0,
    NodeStatType.CW_INCREASE: 0,
    NodeStatType.TIMEOUT_RETRY: 0
}

class ChannelStatus(Enum):
    CLEAR = 0
    BUSY = 1


def waiting_packet_status():
    return [NodeStatus.WAITING_DATA, NodeStatus.WAITING_ACK, NodeStatus.WAITING_CTS,NodeStatus.IDLE, NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR]

class NodeStatus(Enum):

    # IDLE,WAITING_DIFS,WAITING_UNTIL_CHANNEL_IS_CLEAR,CONTENTION_WINDOW,SENDING_PACKET,WAITING_CTS,WAITING_ACK,WAITING_DATA,RECEIVING_PACKET


    IDLE = 0
    WAITING_UNTIL_CHANNEL_IS_CLEAR = 1
    # WAITING RTS = IDLE
    SENDING_RTS = 2
    SENDING_CTS = 3
    WAITING_CTS = 4
    SENDING_DATA = 5
    WAITING_DATA = 6
    SENDING_ACK = 7
    WAITING_ACK = 8
    TIMEOUT = 9
    END_BACKOFF_TIMEOUT = 10

    def can_start_new_connections(self):
        match self:
            case NodeStatus.IDLE | NodeStatus.SENDING_RTS | NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR:
                return True
            case _:
                return False

    def can_receive_packet(self):
        match self:
            case NodeStatus.IDLE | NodeStatus.SENDING_RTS | NodeStatus.WAITING_UNTIL_CHANNEL_IS_CLEAR | NodeStatus.WAITING_ACK | NodeStatus.WAITING_DATA | NodeStatus.WAITING_CTS:
                return True
            case _:
                return False




