"""
QLAgent: Agente Q-Learning per la decisione WAIT/SEND

Ad ogni tick di backoff, l'agente decide se:
- WAIT: aspettare un altro tick
- SEND: trasmettere ora

L'apprendimento si basa su fattori osservabili:
- Collisioni/timeout recenti (storia del nodo)
- Tempo già trascorso in attesa
- Traffico percepito sul canale
"""

import random
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from collections import deque

from models.ql_types import (
    TransmissionOutcome,
    Action,
    CollisionLevel,
    WaitTimeLevel,
    TrafficLevel,
    QLState
)

import logging

_logger = logging.getLogger(__name__)


@dataclass
class QLConfig:
    """Configurazione dei parametri Q-Learning"""
    learning_rate: float = 0.1          # Alpha
    discount_factor: float = 0.95       # Gamma
    epsilon_initial: float = 1.0        # Esplorazione iniziale
    epsilon_decay: float = 0.9995       # Decay rate (più lento)
    epsilon_min: float = 0.05           # Esplorazione minima
    traffic_window_size: int = 50       # Finestra per stima traffico


@dataclass
class QLStats:
    """Statistiche dell'agente Q-Learning"""
    explorations: int = 0
    exploitations: int = 0
    total_reward: float = 0.0
    total_transmissions: int = 0
    successful_transmissions: int = 0
    total_waits: int = 0
    total_sends: int = 0
    action_history: List[Action] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_transmissions == 0:
            return 0.0
        return self.successful_transmissions / self.total_transmissions * 100

    def record_action(self, action: Action, explored: bool):
        """Registra un'azione"""
        if explored:
            self.explorations += 1
        else:
            self.exploitations += 1

        if action == Action.WAIT:
            self.total_waits += 1
        else:
            self.total_sends += 1

        # Mantieni solo ultime 100 azioni
        self.action_history.append(action)
        if len(self.action_history) > 100:
            self.action_history.pop(0)

    def record_outcome(self, outcome: TransmissionOutcome, reward: float):
        """Registra l'esito di una trasmissione"""
        self.total_transmissions += 1
        self.total_reward += reward
        if outcome == TransmissionOutcome.SUCCESS:
            self.successful_transmissions += 1


class TrafficMonitor:
    """
    Monitora il traffico sul canale.
    Tiene traccia di quante volte il canale è stato visto occupato.
    """

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.channel_observations: deque = deque(maxlen=window_size)

    def record_observation(self, channel_busy: bool):
        """Registra se il canale era occupato in questo tick"""
        self.channel_observations.append(1 if channel_busy else 0)

    def get_traffic_level(self) -> TrafficLevel:
        """Stima il livello di traffico"""
        if len(self.channel_observations) < 5:
            return TrafficLevel.MEDIUM  # Default

        busy_ratio = sum(self.channel_observations) / len(self.channel_observations)
        return TrafficLevel.from_busy_ratio(busy_ratio)

    def get_busy_ratio(self) -> float:
        """Restituisce la percentuale di canale occupato"""
        if len(self.channel_observations) == 0:
            return 0.0
        return sum(self.channel_observations) / len(self.channel_observations)

    def reset(self):
        self.channel_observations.clear()


class RewardCalculator:
    """
    Calcola i reward per le azioni WAIT/SEND.

    Obiettivi:
    - Massimizzare successi
    - Minimizzare collisioni/timeout
    - Penalizzare attese troppo lunghe
    """

    # Reward per esiti trasmissione
    REWARD_SUCCESS = 10.0
    REWARD_TIMEOUT = -5.0
    REWARD_COLLISION = -3.0

    # Reward/penalità per azione WAIT
    WAIT_PENALTY_BASE = -0.1      # Piccola penalità per ogni wait
    WAIT_PENALTY_LONG = -0.3      # Penalità maggiore se aspetta troppo

    @classmethod
    def calculate_transmission_reward(cls, outcome: TransmissionOutcome) -> float:
        """Reward quando si completa una trasmissione"""
        if outcome == TransmissionOutcome.SUCCESS:
            return cls.REWARD_SUCCESS
        elif outcome == TransmissionOutcome.TIMEOUT:
            return cls.REWARD_TIMEOUT
        else:
            return cls.REWARD_COLLISION

    @classmethod
    def calculate_wait_reward(cls, ticks_waited: int) -> float:
        """
        Piccola penalità per WAIT, crescente col tempo.
        Incentiva a non aspettare troppo a lungo.
        """
        if ticks_waited > 64:
            return cls.WAIT_PENALTY_LONG
        return cls.WAIT_PENALTY_BASE


class QTable:
    """Gestisce la Q-table per stati e azioni WAIT/SEND"""

    def __init__(self):
        n_states = QLState.total_states()  # 48 stati
        n_actions = Action.count()          # 2 azioni
        self._table = np.zeros((n_states, n_actions))

    def get_value(self, state: QLState, action: Action) -> float:
        return self._table[state.to_index(), action.value]

    def set_value(self, state: QLState, action: Action, value: float):
        self._table[state.to_index(), action.value] = value

    def get_best_action(self, state: QLState) -> Action:
        state_idx = state.to_index()
        best_action_idx = int(np.argmax(self._table[state_idx]))
        return Action(best_action_idx)

    def get_max_value(self, state: QLState) -> float:
        return float(np.max(self._table[state.to_index()]))

    def get_action_values(self, state: QLState) -> dict:
        """Restituisce i Q-values per entrambe le azioni"""
        state_idx = state.to_index()
        return {
            Action.WAIT: self._table[state_idx, Action.WAIT.value],
            Action.SEND: self._table[state_idx, Action.SEND.value]
        }

    def update(self, state: QLState, action: Action, reward: float,
               next_state: QLState, config: QLConfig):
        """Q-Learning update rule"""
        current_q = self.get_value(state, action)
        max_next_q = self.get_max_value(next_state)

        new_q = current_q + config.learning_rate * (
            reward + config.discount_factor * max_next_q - current_q
        )

        self.set_value(state, action, new_q)

    def print_table(self):
        """Stampa la Q-table in formato leggibile"""
        print("\n" + "="*70)
        print("Q-TABLE: State -> [Q(WAIT), Q(SEND)] -> Best Action")
        print("="*70)

        for coll in CollisionLevel:
            print(f"\n--- Collision Level: {coll.name} ---")
            for wait in WaitTimeLevel:
                for traffic in TrafficLevel:
                    state = QLState(coll, wait, traffic)
                    values = self.get_action_values(state)
                    best = self.get_best_action(state)

                    print(f"  Wait={wait.name:9} Traffic={traffic.name:6} | "
                          f"WAIT:{values[Action.WAIT]:7.2f} SEND:{values[Action.SEND]:7.2f} "
                          f"-> {best.name}")


class QLAgent:
    """
    Agente Q-Learning per decisioni WAIT/SEND.

    Ad ogni tick di backoff:
    1. Osserva lo stato (collisioni, tempo attesa, traffico)
    2. Sceglie WAIT o SEND (epsilon-greedy)
    3. Riceve reward e aggiorna Q-table
    """

    def __init__(self, node_id: int, config: Optional[QLConfig] = None):
        self.node_id = node_id
        self.config = config or QLConfig()

        # Componenti
        self.q_table = QTable()
        self.traffic_monitor = TrafficMonitor(self.config.traffic_window_size)
        self.stats = QLStats()

        # Stato interno
        self.epsilon = self.config.epsilon_initial
        self.consecutive_failures = 0
        self.ticks_waited = 0

        # Per tracking della transizione corrente
        self._last_state: Optional[QLState] = None
        self._last_action: Optional[Action] = None
        self._cumulative_wait_reward: float = 0.0

    def observe_channel(self, channel_busy: bool):
        """Chiamato ogni tick per osservare lo stato del canale"""
        self.traffic_monitor.record_observation(channel_busy)

    def get_current_state(self) -> QLState:
        """Costruisce lo stato corrente dai fattori osservabili"""
        return QLState(
            collision_level=CollisionLevel.from_failures(self.consecutive_failures),
            wait_time_level=WaitTimeLevel.from_ticks(self.ticks_waited),
            traffic_level=self.traffic_monitor.get_traffic_level()
        )

    def select_action(self) -> Action:
        """
        Seleziona WAIT o SEND usando epsilon-greedy.
        Chiamato ad ogni tick durante il backoff.
        """
        state = self.get_current_state()

        # Epsilon-greedy
        if random.random() < self.epsilon:
            action = random.choice(list(Action))
            explored = True
        else:
            action = self.q_table.get_best_action(state)
            explored = False

        # Se sceglie WAIT, accumula reward negativo
        if action == Action.WAIT:
            wait_reward = RewardCalculator.calculate_wait_reward(self.ticks_waited)
            self._cumulative_wait_reward += wait_reward
            self.ticks_waited += 1

        # Salva per update
        self._last_state = state
        self._last_action = action

        # Stats
        self.stats.record_action(action, explored)

        _logger.debug(
            f"Node {self.node_id} | {state} | "
            f"Action: {action.name} | Explored: {explored} | ε={self.epsilon:.3f}"
        )

        return action

    def process_outcome(self, outcome: TransmissionOutcome):
        """
        Chiamato quando la trasmissione termina (successo/timeout/collisione).
        Aggiorna la Q-table con il reward finale.
        """
        if self._last_state is None or self._last_action is None:
            return

        # Aggiorna contatore fallimenti
        if outcome == TransmissionOutcome.SUCCESS:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

        # Reward totale = reward trasmissione + penalità attesa accumulata
        tx_reward = RewardCalculator.calculate_transmission_reward(outcome)
        total_reward = tx_reward + self._cumulative_wait_reward

        # Nuovo stato dopo la trasmissione
        self.ticks_waited = 0  # Reset per prossimo backoff
        next_state = self.get_current_state()

        # Update Q-table
        self.q_table.update(
            self._last_state,
            self._last_action,
            total_reward,
            next_state,
            self.config
        )

        # Stats
        self.stats.record_outcome(outcome, total_reward)

        # Decay epsilon
        self._decay_epsilon()

        # Reset per prossima trasmissione
        self._cumulative_wait_reward = 0.0

        _logger.info(
            f"Node {self.node_id} | Outcome: {outcome.name} | "
            f"Reward: {total_reward:.2f} | ε={self.epsilon:.3f}"
        )

    def reset_backoff(self):
        """Chiamato quando inizia un nuovo backoff"""
        self.ticks_waited = 0
        self._cumulative_wait_reward = 0.0
        self._last_state = None
        self._last_action = None

    def _decay_epsilon(self):
        """Riduce epsilon nel tempo"""
        self.epsilon = max(
            self.config.epsilon_min,
            self.epsilon * self.config.epsilon_decay
        )

    def get_stats_summary(self) -> dict:
        """Restituisce riepilogo statistiche"""
        total_actions = self.stats.total_waits + self.stats.total_sends

        return {
            'node_id': self.node_id,
            'epsilon': round(self.epsilon, 4),
            'total_transmissions': self.stats.total_transmissions,
            'successful_transmissions': self.stats.successful_transmissions,
            'success_rate': f"{self.stats.success_rate:.2f}%",
            'total_reward': round(self.stats.total_reward, 2),
            'explorations': self.stats.explorations,
            'exploitations': self.stats.exploitations,
            'total_waits': self.stats.total_waits,
            'total_sends': self.stats.total_sends,
            'wait_send_ratio': f"{self.stats.total_waits}:{self.stats.total_sends}",
            'avg_wait_per_send': round(self.stats.total_waits / max(1, self.stats.total_sends), 2),
            'consecutive_failures': self.consecutive_failures,
            'current_state': str(self.get_current_state()),
            'traffic_level': self.traffic_monitor.get_traffic_level().name,
            'busy_ratio': f"{self.traffic_monitor.get_busy_ratio()*100:.1f}%"
        }

    def print_q_table(self):
        """Stampa la Q-table"""
        print(f"\n{'='*70}")
        print(f"Q-TABLE FOR NODE {self.node_id}")
        self.q_table.print_table()