import random
from enum import Enum

from models.packet import Packet


class NodeTimerType(Enum):
    NORMAL_WAIT = 0
    BACKOFF = 2

class NodeTimer:

    def __init__(self, timer_type: NodeTimerType, ticks: int, packet: Packet | None = None):
        if timer_type == NodeTimerType.BACKOFF:
            self.waiting_ticks = random.randint(1, ticks)
            self.cw_timer = self.waiting_ticks
        else:
            self.waiting_ticks = ticks
            self.cw_timer = None
        self.timer_type = timer_type
        self.packet = packet

