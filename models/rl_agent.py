from enum import Enum
import random
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)

class RLEvent(Enum):
    """Eventi che arrivano al nodo"""
    NOTHING_HAPPENING = 0
    PACKET_ARRIVED = 1              # Nuovo pacchetto da inviare
    CHANNEL_FREE = 2                # Canale libero
    CHANNEL_BUSY = 3                # Canale occupato
    TRANSMISSION_SUCCESS = 4        # ACK ricevuto
    TRANSMISSION_FAILED = 5         # Collisione/timeout

class RLAction(Enum):
    """Azioni che l'agente può fare"""
    IDLE = 0
    SEND = 1
    WAIT_BACKOFF = 2




RL_ACTIONS = [act for act in RLAction]

class KArmedBanditAgent:

    def __init__(self):
        self.Q = {a: 0.0 for a in RL_ACTIONS}
        self.N = {a: 0.0 for a in RL_ACTIONS}

    def evaluate(self, action: RLAction, reward: float):

        self.N[action] += 1
        n = self.N[action]

        self.Q[action] = self.Q[action] + (1 / n) * (reward - self.Q[action])

    def pick_action(self):
        pass


class EpsGreedyKABAgent(KArmedBanditAgent):

    def __init__(self, epsilon):
        super().__init__()
        self.epsilon = epsilon

    def pick_action(self):
        if random.random() < self.epsilon:
            return RL_ACTIONS[random.randint(0, len(RL_ACTIONS) - 1)]
        return max(RL_ACTIONS, key=lambda a: self.Q[a])


class QLearningAgent:


    def __init__(self, actions, alpha=0.1, gamma=0.9, epsilon=0.1):

        self.actions = actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon

        self.events = [e for e in RLEvent]
        self.actions = [a for a in RLAction]

        self.Q = {e: {a: 0.0 for a in self.actions} for e in self.events}

        # Stato interno
        self.has_packet = False
        self.backoff_counter = 0

    def simulate_environment(self, action: RLAction, has_packet: bool) -> RLEvent:
        """Simula l'ambiente: data un'azione, restituisce il prossimo evento"""

        if action == RLAction.SEND:
            if random.random() < 0.7:  # 70% successo
                return RLEvent.TRANSMISSION_SUCCESS
            else:
                return RLEvent.TRANSMISSION_FAILED

        if action == RLAction.WAIT_BACKOFF:
            if random.random() < 0.6:
                return RLEvent.CHANNEL_FREE
            else:
                return RLEvent.CHANNEL_BUSY

        if action == RLAction.IDLE:
            if random.random() < 0.3:
                return RLEvent.PACKET_ARRIVED
            else:
                return RLEvent.NOTHING_HAPPENING

        return RLEvent.NOTHING_HAPPENING

    def update(self, event: RLEvent, action: RLAction, next_event: RLEvent):
        """Q-learning update"""
        reward = self.evaluate_reward(event, action)

        max_next_q = max(self.Q[next_event].values())
        td_target = reward + self.gamma * max_next_q
        self.Q[event][action] += self.alpha * (td_target - self.Q[event][action])

        return reward

    def evaluate_reward(self, event: RLEvent, action: RLAction) -> float:
        """
        Dato l'evento e l'azione scelta, calcola la reward.
        """

        # === PACKET_ARRIVED: è arrivato un nuovo pacchetto ===
        if event == RLEvent.PACKET_ARRIVED:
            if action == RLAction.SEND:
                return 2.0  # Bene, prova subito a inviare
            if action == RLAction.WAIT_BACKOFF:
                return 0.5  # Ok, aspetta un po' (prudente)
            if action == RLAction.IDLE:
                return -2.0  # Male, ignori il pacchetto

        # === CHANNEL_FREE: canale libero ===
        if event == RLEvent.CHANNEL_FREE:
            if action == RLAction.SEND:
                return 3.0  # Ottimo, trasmetti quando è libero
            if action == RLAction.IDLE:
                return -1.0  # Sprechi l'opportunità
            if action == RLAction.WAIT_BACKOFF:
                return -0.5  # Perdi tempo inutilmente

        # === CHANNEL_BUSY: canale occupato ===
        if event == RLEvent.CHANNEL_BUSY:
            if action == RLAction.IDLE:
                return 1.0  # Corretto, aspetta
            if action == RLAction.WAIT_BACKOFF:
                return 1.5  # Ancora meglio, backoff esplicito
            if action == RLAction.SEND:
                return -5.0  # Male! Causerai collisione

        # === TRANSMISSION_SUCCESS: ACK ricevuto ===
        if event == RLEvent.TRANSMISSION_SUCCESS:
            if action == RLAction.IDLE:
                return 10.0  # Perfetto, hai finito
            if action == RLAction.SEND:
                return -1.0  # Inutile, già inviato
            if action == RLAction.WAIT_BACKOFF:
                return 0.0  # Inutile

        # === TRANSMISSION_FAILED: collisione ===
        if event == RLEvent.TRANSMISSION_FAILED:
            if action == RLAction.WAIT_BACKOFF:
                return 2.0  # Corretto, aspetta prima di riprovare
            if action == RLAction.SEND:
                return -8.0  # Pessimo, ritrasmetti subito = altra collisione
            if action == RLAction.IDLE:
                return -3.0  # Male, devi riprovare

        # === NOTHING_HAPPENING ===
        if event == RLEvent.NOTHING_HAPPENING:
            if action == RLAction.IDLE:
                return 0.5  # Ok, riposa
            if action == RLAction.SEND:
                return -2.0  # Trasmetti a vuoto
            if action == RLAction.WAIT_BACKOFF:
                return 0.0  # Neutro

        return 0.0

    def print_policy(self):
        """Stampa la policy appresa"""
        print("\n=== POLICY APPRESA ===\n")
        for event in self.events:
            best_action = max(self.actions, key=lambda a: self.Q[event][a])
            print(f"Evento: {event.name:25} → Azione: {best_action.name}")
            for action in self.actions:
                print(f"    Q[{action.name:12}] = {self.Q[event][action]:+.2f}")
            print()

    def pick_action(self, state):
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        return max(self.actions, key=lambda a: self.Q[state][a])


if __name__ == "__main__":
    agent = QLearningAgent(RL_ACTIONS)


    busy = False

    event = RLEvent.NOTHING_HAPPENING

    for episode in range(10000000):

        action = agent.pick_action(event)
        next_event = agent.simulate_environment(action, has_packet=True)
        agent.update(event, action, next_event)
        event = next_event

    agent.epsilon = 0.0
    agent.print_policy()




