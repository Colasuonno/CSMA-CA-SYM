from config_params import NodeStatus
from models.v2.node2 import Node2
from enum import Enum
import random
from models.packet import Packet, PacketType
from utils.timers import NodeTimer, NodeTimerType
import logging

_logger = logging.getLogger(__name__)


class Reward(Enum):
    CHANNEL_BUSY_AFTER_WAIT = -1.0
    CHANNEL_CLEAR_AFTER_WAIT = 0.0
    TIMEOUT = -3.0
    CTS_RECEIVED = 5.0


"""

OVERALL STRATEGY:

- One state
- N actions

No clue of previous state :(

epsilon-greedy approach 

"""


class NodeAction(Enum):
    # Note that when a node is already sending the packet (RTS)
    # we don't need to execute an action
    WAIT_SHORT = 2
    WAIT_MEDIUM = 10
    WAIT_LONG = 50


ACTIONS = [act for act in NodeAction]


# Epsilon-greedy
class RLKArmedBanditNode(Node2):

    def __init__(self, node_id: int, channel, epsilon: float=0.03):
        super().__init__(node_id, channel)

        self.rl_action_before_sending: NodeAction | None = None
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

        match packet.packet_type:
            case PacketType.CTS:
                # We received CTS, it means everything worked, let's reward
                # We can't receive a CTS after a wait, that's why we place SEND
                self.evaluate(self.rl_action_before_sending, Reward.CTS_RECEIVED.value)
                self.rl_action_before_sending = None

        super().receive_packet(t, packet)



    def timer_tick(self, t):

        super().timer_tick(t)

        if not self.timer:
            return

        if self.timer.waiting_ticks == 0:
            if self.timer.timer_type == NodeTimerType.RL_WAIT:
                # We need to perform RL Action

                busy = self.channel_busy()

                reward = Reward.CHANNEL_BUSY_AFTER_WAIT.value if busy else Reward.CHANNEL_CLEAR_AFTER_WAIT.value
                self.evaluate(self.timer.rl_action, reward)

                if not busy:
                    # Channel is clear, send the packet
                    match self.status:
                        case NodeStatus.SENDING_RTS:
                            self.status = NodeStatus.WAITING_CTS
                        case _:
                            raise Exception(str(self.node_id) + " (SEND) Invalid timer status " + str(self.status))

                    self.rl_action_before_sending = self.timer.rl_action
                    self.send_packet_from_timer(t)
                    self.reset_timer()
                else:
                    action = self.pick_action()
                    self.timer = NodeTimer(NodeTimerType.RL_WAIT, action.value, self.current_packet_buff, action, None)

    def print_policy(self, channel):
        _logger.info(f"\n=== Node {self.node_id} Policy ===")
        _logger.info(f"  Position: ({self.x}, {self.y})")
        _logger.info(f"  Epsilon: {self.epsilon}")

        # Calcola distanza media dagli altri nodi
        other_nodes = [n for n in channel.nodes if n.node_id != self.node_id]
        if other_nodes:
            total_distance = sum(self.distance(n) for n in other_nodes)
            avg_distance = total_distance / len(other_nodes)
            _logger.info(f"  Avg distance from other nodes: {avg_distance:.2f}")

            # Opzionale: mostra anche min/max
            distances = [self.distance(n) for n in other_nodes]
            _logger.info(f"  Min distance: {min(distances):.2f}")
            _logger.info(f"  Max distance: {max(distances):.2f}")
        else:
            _logger.info(f"  No other nodes in channel")

        _logger.info(f"  --- Q Values ---")
        for action in ACTIONS:
            _logger.info(f"    {action.name}: Q={self.Q[action]:.4f}, N={int(self.N[action])}")

        best_action = max(ACTIONS, key=lambda a: self.Q[a])
        _logger.info(f"  Best action: {best_action.name}")

    def enter_cw(self, t):
        if self.status == NodeStatus.TIMEOUT:

            if self.rl_action_before_sending:
                # Timeout after send
                self.evaluate(self.rl_action_before_sending, Reward.TIMEOUT.value)
                self.rl_action_before_sending = None

            # Timeout for other reasons (after RTS maybe))

            self.status = NodeStatus.END_BACKOFF_TIMEOUT
            self.reset_timer()
            self.reset_timeout()
        else:
            # override and use karmed bandit node
            # We just wait 1 tick before taking action

            action = self.pick_action()

            # Perform action and wait for reward.
            self.timer = NodeTimer(NodeTimerType.RL_WAIT, action.value, self.current_packet_buff, action, None)
