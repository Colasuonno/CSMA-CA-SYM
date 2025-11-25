import logging

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