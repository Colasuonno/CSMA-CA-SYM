import logging
import random

from config_params import ChannelStatus, CW_MIN

_logger = logging.getLogger(__name__)




class WaitingTimer:

    def __init__(self, end_fn, wait_ticks: int, *args):
        self.wait_ticks = wait_ticks
        self.end_fn = end_fn
        self.args = args

    def tick(self):
        """
        This function is called every tick
        :param t: the current tick
        """
        self.wait_ticks -= 1

        if self.wait_ticks == 0:
            self.trigger_on_finish()


    def trigger_on_finish(self):
        self.end_fn(*self.args)



def start_timer(wait_ticks: int, end_fn, *args) -> WaitingTimer:
    return WaitingTimer(end_fn, wait_ticks, *args)



class ContentionWindowTimer(WaitingTimer):


    def __init__(self, cw_size: int, channel, end_fn, wait_ticks: int, *args):
            super().__init__(end_fn, wait_ticks, *args)
            self.channel = channel
            self.cw_size = cw_size


    def tick(self):
        """
        Decrease the timer only if the channel is idle
        :return:
        """

        if self.channel.status == ChannelStatus.CLEAR:
            super().tick()

def start_cw_timer(channel, cw_size: int, end_fn, *args) -> WaitingTimer:
    return ContentionWindowTimer(cw_size, channel, end_fn, random.randint(0, cw_size), *args)