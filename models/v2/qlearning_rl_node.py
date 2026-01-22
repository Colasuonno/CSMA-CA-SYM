from config_params import NodeStatus
from models.v2.node2 import Node2
from enum import Enum
import random
from collections import deque
from models.packet import Packet, PacketType
from utils.timers import NodeTimer, NodeTimerType
import logging

_logger = logging.getLogger(__name__)


class Reward(Enum):
    SUCCESSFUL_TRANSMISSION = 10.0

    TIMEOUT_AFTER_SENDING = -5.0
    COLLISION_SEND_WHILE_BUSY = -3.0

    WAIT_WHEN_CHANNEL_BUSY = 0.5
    WAIT_WHEN_CHANNEL_CLEAR = -0.3

    LONG_WAIT_PENALTY = -0.1


"""

OVERALL STRATEGY:

- One state
- N actions

No clue of previous state :(

epsilon-greedy approach 

"""


class NodeAction(Enum):
    SEND_NOW = 1
    WAIT_TINY = 3
    WAIT_SHORT = 7
    WAIT_MEDIUM = 15
    WAIT_LONG = 30
    WAIT_VERY_LONG = 50


class NavLevel(Enum):
    NONE = 0        # NAV = 0
    LOW = 1         # NAV 1-10
    MEDIUM = 2      # NAV 11-30
    HIGH = 3        # NAV > 30


class RetryLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class TrafficLevel(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2

class NodeState(Enum):

    WAITING = 5
    HAS_TO_SEND_PACKET = 0
    SENDING_WHILE_CHANNEL_BUSY = 1
    SENDING_WHILE_CHANNEL_CLEAR = 2
    TIMEDOUT_AFTER_SEND = 3
    PACKET_RECEIVED = 4


class ChannelState(Enum):
    CLEAR = 0
    BUSY = 1


ACTIONS = [act for act in NodeAction]


# Epsilon-greedy
class QLearningNode(Node2):

    def __init__(self, node_id: int, channel, alpha: float =0.1, gamma: float=0.9, epsilon: float=0.03):
        super().__init__(node_id, channel)

        self.rl_action_before_sending: NodeAction | None = None
        self.last_state_before_sending = None
        self.epsilon = epsilon
        self.epsilon_decay = 0.9995 # Don't explore forever pls :)
        self.alpha = alpha
        self.gamma = gamma



        # Contextual infos
        self.retry_count = 0
        self.max_retries = 5
        self.traffic_window_size = 100
        self.recent_busy_events = deque(maxlen=self.traffic_window_size)
        self.recent_collision_events = deque(maxlen=self.traffic_window_size)

        self.actions = ACTIONS
        self.Q = self._initialize_q_table()
        self.state_visit_count = {}


    def _initialize_q_table(self) -> dict:
        """Inizializza Q-table per tutte le combinazioni di stato"""
        Q = {}
        for nav in NavLevel:
            for retry in RetryLevel:
                for traffic in TrafficLevel:
                    for channel in ChannelState:
                        state = (nav, retry, traffic, channel)
                        Q[state] = {action: 0.0 for action in self.actions}
        return Q

    def _discretize_nav(self) -> NavLevel:
        if self.nav_seconds == 0:
            return NavLevel.NONE
        elif self.nav_seconds <= 10:
            return NavLevel.LOW
        elif self.nav_seconds <= 30:
            return NavLevel.MEDIUM
        else:
            return NavLevel.HIGH

    def _discretize_retry(self) -> RetryLevel:
        if self.retry_count == 0:
            return RetryLevel.NONE
        elif self.retry_count <= 2:
            return RetryLevel.LOW
        elif self.retry_count <= 4:
            return RetryLevel.MEDIUM
        else:
            return RetryLevel.HIGH

    def _estimate_traffic_level(self) -> TrafficLevel:
        if len(self.recent_busy_events) < 10:
            return TrafficLevel.LOW

        # Calcola percentuale di eventi "busy" recenti
        busy_ratio = sum(self.recent_busy_events) / len(self.recent_busy_events)
        collision_ratio = sum(self.recent_collision_events) / len(
            self.recent_collision_events) if self.recent_collision_events else 0

        # Combina le metriche
        traffic_score = busy_ratio * 0.6 + collision_ratio * 0.4

        if traffic_score < 0.3:
            return TrafficLevel.LOW
        elif traffic_score < 0.6:
            return TrafficLevel.MEDIUM
        else:
            return TrafficLevel.HIGH

    def _get_channel_state(self) -> ChannelState:
        return ChannelState.BUSY if self.channel_busy() else ChannelState.CLEAR

    def get_current_state(self) -> tuple:


        # State for qlearning action decision is based on:
        # - Last NAV
        # - # Retries
        # - Traffic Level
        # - Channel Busy/Clear

        return (
            self._discretize_nav(),
            self._discretize_retry(),
            self._estimate_traffic_level(),
            self._get_channel_state()
        )

    def _record_busy_event(self, is_busy: bool):
        self.recent_busy_events.append(1 if is_busy else 0)

    def _record_collision_event(self, is_collision: bool):
        self.recent_collision_events.append(1 if is_collision else 0)

    def evaluate(self, from_state: tuple, action: NodeAction, to_state: tuple, reward: float):

        # Q-Learning update
        max_next_q = max(self.Q[to_state].values())
        td_target = reward + self.gamma * max_next_q
        td_error = td_target - self.Q[from_state][action]
        self.Q[from_state][action] += self.alpha * td_error

        # Epsilon decay
        if self.epsilon > 0.01:
            self.epsilon *= self.epsilon_decay

        return reward

    def pick_action(self, state: tuple) -> NodeAction:

        #epsilon greedy
        if random.random() < self.epsilon:
            return random.choice(self.actions)


        best_action = max(self.actions, key=lambda a: self.Q[state][a])
        return best_action

    def receive_packet(self, t, packet: Packet):

        if self.should_skip_packet(packet):
            return

        match packet.packet_type:
            case PacketType.CTS:
                # Successo! Il CTS è arrivato
                if self.last_state_before_sending is not None:
                    current_state = self.get_current_state()
                    self.evaluate(
                        self.last_state_before_sending,
                        NodeAction.SEND_NOW,
                        current_state,
                        Reward.SUCCESSFUL_TRANSMISSION.value
                    )
                    self._record_collision_event(False)

                # Reset retry count on success
                self.retry_count = 0
                self.rl_action_before_sending = None
                self.last_state_before_sending = None

        super().receive_packet(t, packet)

    def timer_tick(self, t):
        super().timer_tick(t)

        if not self.timer:
            return

        if self.timer.waiting_ticks == 0:
            if self.timer.timer_type == NodeTimerType.RL_WAIT:
                self._handle_rl_timer_expired(t)

    def _handle_rl_timer_expired(self, t):
        current_state = self.get_current_state()
        busy = self.channel_busy()

        # Record per traffic estimation
        self._record_busy_event(busy)

        if self.timer.rl_action == NodeAction.SEND_NOW:
            self._handle_send_action(t, current_state, busy)
        else:
            self._handle_wait_action(t, current_state, busy)

    def _handle_send_action(self, t, current_state: tuple, busy: bool):
        previous_state = self.timer.rl_previous_state or current_state

        if busy:
            # Collisione - canale occupato durante il tentativo di invio
            self.evaluate(
                previous_state,
                NodeAction.SEND_NOW,
                current_state,
                Reward.COLLISION_SEND_WHILE_BUSY.value
            )
            self._record_collision_event(True)

            self.retry_count += 1

            if self.retry_count >= self.max_retries:
                _logger.debug(f"Node {self.node_id}: Max retries reached, dropping packet")
                self.retry_count = 0
                self.status = NodeStatus.IDLE
                self.reset_timer()
                return

            # Scegli nuova azione
            new_state = self.get_current_state()
            action = self.pick_action(new_state)
            self.timer = NodeTimer(
                NodeTimerType.RL_WAIT,
                action.value,
                self.current_packet_buff,
                action,
                new_state  # Passa lo stato per il prossimo update
            )
        else:
            # Canale libero - invia!
            match self.status:
                case NodeStatus.SENDING_RTS:
                    self.status = NodeStatus.WAITING_CTS
                case _:
                    raise Exception(f"Node {self.node_id}: Invalid status {self.status} for SEND")

            # Salva lo stato per quando riceveremo CTS (o timeout)
            self.last_state_before_sending = previous_state
            self.rl_action_before_sending = NodeAction.SEND_NOW
            self.send_packet_from_timer(t)
            self.reset_timer()

    def _handle_wait_action(self, t, current_state: tuple, busy: bool):
        """Gestisce le azioni di WAIT"""
        previous_state = self.timer.rl_previous_state or current_state
        action_taken = self.timer.rl_action

        # Calcola reward basato sul risultato dell'attesa
        if busy:
            # Buona decisione - il canale era occupato
            reward = Reward.WAIT_WHEN_CHANNEL_BUSY.value
        else:
            # Potevamo inviare - tempo perso
            reward = Reward.WAIT_WHEN_CHANNEL_CLEAR.value
            # Penalità extra per attese lunghe quando non necessario
            if action_taken in [NodeAction.WAIT_LONG, NodeAction.WAIT_VERY_LONG]:
                reward += Reward.LONG_WAIT_PENALTY.value * (action_taken.value // 10)

        self.evaluate(previous_state, action_taken, current_state, reward)

        # Scegli la prossima azione
        new_state = self.get_current_state()
        action = self.pick_action(new_state)
        self.timer = NodeTimer(
            NodeTimerType.RL_WAIT,
            action.value,
            self.current_packet_buff,
            action,
            new_state
        )

    def print_policy(self, channel):
        _logger.info(f"\n{'=' * 60}")
        _logger.info(f"=== Node {self.node_id} - Q-Learning Policy ===")
        _logger.info(f"{'=' * 60}")
        _logger.info(f"Position: ({self.x}, {self.y})")
        _logger.info(f"Current Epsilon: {self.epsilon:.4f}")

        # Mostra le policy più visitate
        _logger.info(f"\n--- Most Visited States and Best Actions ---")
        sorted_states = sorted(
            self.state_visit_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        for state, visits in sorted_states:
            nav, retry, traffic, ch_state = state
            best_action = max(self.actions, key=lambda a: self.Q[state][a])
            best_q = self.Q[state][best_action]
            _logger.info(
                f"  State: NAV={nav.name:6}, Retry={retry.name:6}, "
                f"Traffic={traffic.name:6}, Channel={ch_state.name:5} | "
                f"Visits: {visits:5} | Best: {best_action.name:15} (Q={best_q:+.2f})"
            )

        # Mostra Q-values per stati chiave
        _logger.info(f"\n--- Key State Q-Values ---")
        key_states = [
            (NavLevel.NONE, RetryLevel.NONE, TrafficLevel.LOW, ChannelState.CLEAR),
            (NavLevel.NONE, RetryLevel.NONE, TrafficLevel.HIGH, ChannelState.BUSY),
            (NavLevel.HIGH, RetryLevel.HIGH, TrafficLevel.HIGH, ChannelState.BUSY),
        ]

        for state in key_states:
            nav, retry, traffic, ch_state = state
            _logger.info(
                f"\n  State: NAV={nav.name}, Retry={retry.name}, Traffic={traffic.name}, Channel={ch_state.name}")
            for action in self.actions:
                q_val = self.Q[state][action]
                marker = " <-- BEST" if q_val == max(self.Q[state].values()) else ""
                _logger.info(f"    {action.name:15}: Q={q_val:+.4f}{marker}")

    def enter_cw(self, t):

        if self.status == NodeStatus.TIMEOUT:
            # Timeout dopo invio - penalizza
            if self.last_state_before_sending is not None:
                current_state = self.get_current_state()
                self.evaluate(
                    self.last_state_before_sending,
                    NodeAction.SEND_NOW,
                    current_state,
                    Reward.TIMEOUT_AFTER_SENDING.value
                )
                self._record_collision_event(True)

            # Incrementa retry
            self.retry_count += 1
            self.rl_action_before_sending = None
            self.last_state_before_sending = None

            if self.retry_count >= self.max_retries:
                _logger.debug(f"Node {self.node_id}: Max retries after timeout, dropping packet")
                self.retry_count = 0
                self.status = NodeStatus.IDLE
                self.reset_timer()
                self.reset_timeout()
                return

            self.status = NodeStatus.END_BACKOFF_TIMEOUT
            self.reset_timer()
            self.reset_timeout()
        else:
            # Nuovo tentativo di invio - usa Q-Learning
            current_state = self.get_current_state()
            action = self.pick_action(current_state)

            self.timer = NodeTimer(
                NodeTimerType.RL_WAIT,
                action.value,
                self.current_packet_buff,
                action,
                current_state  # Salva lo stato per l'update
            )
