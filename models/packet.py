from enum import Enum
from config_params import DIFS,SIFS

class PacketType(Enum):
    RTS = 0
    CTS = 1
    DATA = 2
    ACK = 2

class Packet:


    def __init__(self, packet_type: PacketType, sender_address: int, receiver_address: int, data_size: int=0):
        """
        The data_size is specified only for RTS packet
        """
        self.packet_type = packet_type
        self.sender_address = sender_address
        self.receiver_address = receiver_address
        self.data_size = data_size
        # RTS + CTS + DATA + ACK + SIFS (Duration Estimation in ticks)
        self.duration = 1 + 1 + data_size + 1 + SIFS