import binascii
from enum import Enum
from config_params import DIFS,SIFS
import logging

_logger = logging.getLogger(__name__)

class PacketType(Enum):
    RTS = 0
    CTS = 1
    DATA = 2
    ACK = 3


# Polinomio CRC-32 standard (IEEE 802.3)
CRC32_POLYNOMIAL = 0x04C11DB7

def crc32_fast(data: bytes) -> int:
    """crc-32 bit with masking 32 bit integer, this is because crc32 could be bigger"""
    return binascii.crc32(data) & 0xFFFFFFFF

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
        self.crc = None # Sender calculation

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.append(self.packet_type.value)
        data.extend(self.sender_address.to_bytes(2, 'big'))
        data.extend(self.receiver_address.to_bytes(2, 'big'))
        data.extend(self.data_size.to_bytes(4, 'big'))
        data.extend(self.duration.to_bytes(4, 'big'))
        return bytes(data)

    def calculate_crc(self) -> int:
        data = self.to_bytes()
        return crc32_fast(data)

    def attach_crc(self):
        self.crc = self.calculate_crc()

    def verify_crc(self, verify_receiver: int) -> bool:
        if self.crc is None:
            return False
        return self.calculate_crc() == self.crc and self.receiver_address == verify_receiver