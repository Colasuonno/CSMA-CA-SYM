from config_params import NodeStatus
from models.v2.node2 import Node2
from enum import Enum
import random
from models.packet import Packet, PacketType
from utils.timers import NodeTimer, NodeTimerType
import logging

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
class RLQLearningNode(Node2):


    def __init__(self, node_id: int, channel, epsilon=0.1, alpha=0.1, gamma=0.9):
        super().__init__(node_id, channel)

        self.epsilon = epsilon
        self.alpha = alpha
        self.gamma = gamma
        self.events = [e for e in NodeEvent]
        self.actions = [a for a in NodeAction]

        self.Q = {e: {a: 0.0 for a in self.actions} for e in self.events}
    
    def print_policy(self):
        """Stampa la policy appresa"""
        _logger.info("\n=== POLICY APPRESA ===\n")
        for event in self.events:
            best_action = max(self.actions, key=lambda a: self.Q[event][a])
            _logger.info(f"Evento: {event.name:25} → Azione: {best_action.name}")
            for action in self.actions:
                _logger.info(f"    Q[{action.name:12}] = {self.Q[event][action]:+.2f}")
            _logger.info()
    
    def evaluate(self, event: NodeEvent, action: NodeAction, next_event: NodeEvent):
        reward = self.evaluate_reward(event, action)

        max_next_q = max(self.Q[next_event].values())
        td_target = reward + self.gamma * max_next_q
        self.Q[event][action] += self.alpha * (td_target - self.Q[event][action])

        return reward

    def pick_action(self, state):
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        return max(self.actions, key=lambda a: self.Q[state][a])


    def receive_packet(self, t, packet: Packet):

        if self.should_skip_packet(packet):
            return

        match packet.packet_type:
            case PacketType.CTS:

                if self.timer and self.timer.timer_type == NodeTimerType.RL_WAIT:

                    # POSITIVE REWARD SINCE EVERYTHING IS OK
                    next_event = NodeEvent.TRASMISSION_SUCCESS
                    self.evaluate(self.timer.rl_event, self.timer.rl_action, next_event)

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

                        
                            next_event = NodeEvent.CHANNEL_BUSY
                            self.evaluate(self.timer.rl_event, self.timer.rl_action, next_event)

                            # Update current timer event
                            self.timer.rl_event = next_event

                            # Pick new action and go on
                            action = self.pick_action(self.timer.rl_event)
                            self.timer = NodeTimer(NodeTimerType.RL_WAIT, 1, self.current_packet_buff, action, self.timer.rl_event)

                        else:
                            
                            next_event = NodeEvent.CHANNEL_FREE
                            
                            self.evaluate(self.timer.rl_event, self.timer.rl_action, next_event)

                            # Update current timer event
                            self.timer.rl_event = next_event

                            # Modify the node state for the sym to work
                            match self.status:
                                case NodeStatus.SENDING_RTS:
                                    self.status = NodeStatus.WAITING_CTS

                            self.send_packet_from_timer(t)

                    case NodeAction.WAIT:
                        # Still wait some ticks

                        # Evaluate reward

                        # So based on node status, waiting has different rewards

                        next_event = NodeEvent.HAS_TO_SEND_PACKET

                        match self.status:
                            case NodeStatus.SENDING_RTS:
                               next_event = NodeEvent.HAS_TO_SEND_PACKET
                            case NodeStatus.TIMEOUT:
                                next_event = NodeEvent.TRANSMISSION_FAILED

                        self.evaluate(self.timer.rl_event, self.timer.rl_action, next_event)

                        # Update current timer event
                        self.timer.rl_event = next_event
                        
                        # Pick new action
                        action = self.pick_action(self.timer.rl_event)
                        self.timer = NodeTimer(NodeTimerType.RL_WAIT, 1, self.current_packet_buff, action, self.timer.rl_event)

    def evaluate_reward(self, event: NodeEvent, action: NodeAction):
        match event:

            case NodeEvent.HAS_TO_SEND_PACKET:

                match action:
                    case NodeAction.SEND:
                        return 2.0
                    case NodeAction.WAIT:
                        return 0.5
            case NodeEvent.CHANNEL_FREE:
                match action:
                    case NodeAction.SEND:
                        return 3.0
                    case NodeAction.WAIT:
                        return -1.0
            case NodeEvent.CHANNEL_BUSY:
                match action:
                    case NodeAction.SEND:
                        return -5.0
                    case NodeAction.WAIT:
                        return 1.5
            case NodeEvent.TRASMISSION_SUCCESS:
                match action:
                    case NodeAction.SEND:
                        return -1.0
                    case NodeAction.WAIT:
                        return 0.0
            case NodeEvent.TRANSMISSION_FAILED:
                match action:
                    case NodeAction.SEND:
                        return -8.0
                    case NodeAction.WAIT:
                        return 2.0

    def enter_cw(self):


        if self.status == NodeStatus.TIMEOUT:
            # it means sending the packet failed, so

            next_event = NodeEvent.TRANSMISSION_FAILED

            self.evaluate(NodeEvent.HAS_TO_SEND_PACKET, self.timer.rl_action, next_event)
            
            self.status = NodeStatus.END_BACKOFF_TIMEOUT
            self.reset_timer()
            self.reset_timeout()
        else:
            # override and use karmed bandit node
            # We just wait 1 tick before taking action
            if not self.timer or not self.timer.rl_event:
                event = NodeEvent.HAS_TO_SEND_PACKET
            else:
                event = self.timer.rl_event

            action = self.pick_action(event)

            # Perform action and wait for reward.

            self.timer = NodeTimer(NodeTimerType.RL_WAIT, 1, self.current_packet_buff, action,
                                   NodeEvent.HAS_TO_SEND_PACKET)
