from config_params import NodeStatus
from models.v2.node2 import Node2
from enum import Enum
import random
from models.packet import Packet, PacketType
from utils.timers import NodeTimer, NodeTimerType
import logging


"""

    def evaluate_reward(self, event: NodeEvent, action: NodeAction):
        match event:

            case NodeEvent.HAS_TO_SEND_PACKET:

                match action:
                    case NodeAction.SEND:
                        return 2.0
                    case NodeAction.WAIT:
                        return 0.5
                    case NodeAction.IDLE:
                        return -2.0
            case NodeEvent.CHANNEL_FREE:
                match action:
                    case NodeAction.SEND:
                        return 3.0
                    case NodeAction.WAIT:
                        return -0.5
                    case NodeAction.IDLE:
                        return -1.0
            case NodeEvent.CHANNEL_BUSY:
                match action:
                    case NodeAction.SEND:
                        return -5.0
                    case NodeAction.WAIT:
                        return 1.5
                    case NodeAction.IDLE:
                        return 1.0
            case NodeEvent.TRANSMISSION_SUCCESS:
                match action:
                    case NodeAction.SEND:
                        return -1.0
                    case NodeAction.WAIT:
                        return 0.0
                    case NodeAction.IDLE:
                        return 10.0
            case NodeEvent.TRANSMISSION_FAILED:
                match action:
                    case NodeAction.SEND:
                        return -8.0
                    case NodeAction.WAIT:
                        return 2.0
                    case NodeAction.IDLE:
                        return -3.0
            case NodeEvent.NOTHING_HAPPENED:
                match action:
                    case NodeAction.SEND:
                        return -2.0
                    case NodeAction.WAIT:
                        return 0.0
                    case NodeAction.IDLE:
                        return 0.5
"""

_logger = logging.getLogger(__name__)

class NodeEvent(Enum):

    TRASMISSION_SUCCESS = 0
    TRANSMISSION_FAILED = 1
    CHANNEL_BUSY = 2
    CHANNEL_FREE = 3
    HAS_TO_SEND_PACKET = 4



class NodeAction(Enum):
    """Azioni che l'agente può fare"""
    SEND = 1
    WAIT = 2


ACTIONS = [act for act in NodeAction]

# Epsilon-greedy
class RLKArmedBanditNode(Node2):


    def __init__(self, epsilon: float, node_id: int, channel):
        super().__init__(node_id, channel)

        self.epsilon = epsilon
        self.Q = {a: 0.0 for a in ACTIONS}
        self.N = {a: 0.0 for a in ACTIONS}

    def evaluate(self, action: NodeAction, reward: float):
        self.N[action] += 1
        n = self.N[action]

        self.Q[action] = self.Q[action] + (1 / n) * (reward - self.Q[action])


    def pick_action(self):
        if random.random() < self.epsilon:
            return ACTIONS[random.randint(0, len(ACTIONS) - 1)]
        return max(ACTIONS, key=lambda a: self.Q[a])


    def receive_packet(self, t, packet: Packet):

        if self.should_skip_packet(packet):
            return

        _logger.info("@ " + str(t) + " " + "Node " + str(self.node_id) + " Received packet " + str(packet))

        match packet.packet_type:
            case PacketType.CTS:

                if self.timer and self.timer.timer_type == NodeTimerType.RL_WAIT:

                    # POSITIVE REWARD SINCE EVERYTHING IS OK
                    reward = 10.0

                    _logger.info(f"RECEIVED CTS REWARD FOR RL ACTION: {self.timer.rl_action} IS: {reward}")
                    self.evaluate(self.timer.rl_action, reward)

                    # Stop agent now since """"backoff phase""""" is finished

                else:
                    _logger.error("Old packet..... (rl)")
                    return

        super().receive_packet(t, packet)


    def timer_tick(self, t):

        super().timer_tick(t)

        if not self.timer:
            return

        if self.timer.waiting_ticks == 0:
            if self.timer.timer_type == NodeTimerType.RL_WAIT:
                # We need to perform RL Action
                match self.timer.rl_action:
                    case NodeAction.SEND:

                        # Ok we need to send the packet, first we check if the channel is busy
                        if self.channel_busy():
                            # There is a problem so....
                            # NEGATIVE -3 REWARD
                            reward = -3.0
                            self.evaluate(self.timer.rl_action, reward)


                            # Pick new action and go on
                            action = self.pick_action()
                            self.timer = NodeTimer(NodeTimerType.RL_WAIT, 1, self.current_packet_buff, action, self.timer.rl_event)

                        else:
                            # Try to send

                            # Modify the node state for the sym to work
                            match self.status:
                                case NodeStatus.SENDING_RTS:
                                    self.status = NodeStatus.WAITING_CTS

                            self.send_packet_from_timer(t)

                    case NodeAction.WAIT:
                        # Still wait some ticks

                        # Evaluate reward

                        # So based on node status, waiting has different rewards

                        reward = 0.0

                        match self.status:
                            case NodeStatus.SENDING_RTS:
                                # it's ok
                                reward = 1.0
                            case NodeStatus.TIMEOUT:
                                # Don't wait on timeout, we need to recover slowly to send the RTS Again
                                reward = -1.0

                        if self.status not in [NodeStatus.TIMEOUT, NodeStatus.SENDING_RTS]:
                            _logger.info(f"Node Status on wait is: {self.status} {self.timer.timer_type}")

                        self.evaluate(self.timer.rl_action, reward)

                        # Pick new action
                        action = self.pick_action()
                        self.timer = NodeTimer(NodeTimerType.RL_WAIT, 1, self.current_packet_buff, action, self.timer.rl_event)



    def enter_cw(self):


        if self.timer and self.timer.timer_type == NodeTimerType.RL_WAIT and self.status == NodeStatus.TIMEOUT:
            # it means sending the packet failed, so

            reward = -10.0
            self.evaluate(self.timer.rl_action, reward)

            _logger.info(f"Node {self.node_id} PACKET TIMEROUT rw:")
            # The idea is: we sen't a packet, we didn't received CTS
            # we reward -10 for sending in the wrong place
            # next tick we will just go again on
            # END_BACKOFF_TIMEOUT
            # Channel busy?
            action = self.pick_action()

            # We need to reset it

            # We need to create another RTS packet
            self.status = NodeStatus.SENDING_RTS
            self.enter_cw()
        else:
            # override and use karmed bandit node
            # We just wait 1 tick before taking action

            action = self.pick_action()

            # Perform action and wait for reward.

            self.timer = NodeTimer(NodeTimerType.RL_WAIT, 1, self.current_packet_buff, action,
                                   NodeEvent.HAS_TO_SEND_PACKET)
