from enum import Enum

N_NODES = 10
SIMULATION_TICKS = 100000
PROBABILITY_OF_SENDING_PACKET = 0.1
SIFS = 2  # 2 ticks
DIFS = 2 * SIFS + 5
DATA_MIN_SIZE = 10
DATA_MAX_SIZE = 100




class NodeStatType(Enum):
    SENT_PACKET = 0
    RECEIVED_PACKET = 1


DEFAULT_NODE_STATS = {
    NodeStatType.SENT_PACKET: 0,
    NodeStatType.RECEIVED_PACKET: 0
}

class ChannelStatus(Enum):
    CLEAR = 0
    BUSY = 1


class NodeStatus(Enum):
    IDLE = 0
    WAITING_DIFS_FOR_SENDING = 3
    SENSE = 1
    SENDING_PACKET = 2
    WAIT_UNTIL_CHANNEL_IS_CLEAR = 4
