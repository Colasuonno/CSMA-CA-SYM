"""
Definizioni degli Enum per il sistema Q-Learning della Contention Window

L'agente decide ad ogni tick se WAIT o SEND, basandosi su:
- Numero di collisioni/timeout recenti
- Tempo già trascorso in attesa
- Traffico percepito (canale occupato di recente)
"""

from enum import Enum, auto
from dataclasses import dataclass


class TransmissionOutcome(Enum):
    """Possibili esiti di una trasmissione"""
    SUCCESS = auto()      # ACK ricevuto correttamente
    TIMEOUT = auto()      # Nessuna risposta nel tempo previsto
    COLLISION = auto()    # Collisione rilevata sul canale


class Action(Enum):
    """
    Azioni disponibili per l'agente.
    Ad ogni tick decide se aspettare ancora o trasmettere.
    """
    WAIT = 0    # Aspetta un altro tick
    SEND = 1    # Trasmetti ora

    @classmethod
    def count(cls) -> int:
        return len(cls)


class CollisionLevel(Enum):
    """
    Livello di collisioni/timeout recenti per questo nodo.
    Basato sul numero di fallimenti consecutivi.
    """
    NONE = 0        # 0 fallimenti consecutivi
    LOW = 1         # 1 fallimento
    MEDIUM = 2      # 2 fallimenti
    HIGH = 3        # 3+ fallimenti

    @classmethod
    def from_failures(cls, consecutive_failures: int) -> 'CollisionLevel':
        if consecutive_failures == 0:
            return cls.NONE
        elif consecutive_failures == 1:
            return cls.LOW
        elif consecutive_failures == 2:
            return cls.MEDIUM
        else:
            return cls.HIGH


class WaitTimeLevel(Enum):
    """
    Quanto tempo ha già aspettato il nodo in backoff.
    Più aspetta, più dovrebbe essere incentivato a trasmettere.
    """
    SHORT = 0       # 0-8 ticks
    MEDIUM = 1      # 9-32 ticks
    LONG = 2        # 33-64 ticks
    VERY_LONG = 3   # 65+ ticks

    @classmethod
    def from_ticks(cls, ticks_waited: int) -> 'WaitTimeLevel':
        if ticks_waited <= 8:
            return cls.SHORT
        elif ticks_waited <= 32:
            return cls.MEDIUM
        elif ticks_waited <= 64:
            return cls.LONG
        else:
            return cls.VERY_LONG


class TrafficLevel(Enum):
    """
    Traffico percepito dal nodo.
    Basato su quante volte ha visto il canale occupato di recente.
    """
    LOW = 0         # Canale quasi sempre libero
    MEDIUM = 1      # Canale occupato a volte
    HIGH = 2        # Canale spesso occupato

    @classmethod
    def from_busy_ratio(cls, busy_ratio: float) -> 'TrafficLevel':
        """
        busy_ratio: percentuale di tick recenti in cui il canale era occupato
        """
        if busy_ratio < 0.3:
            return cls.LOW
        elif busy_ratio < 0.6:
            return cls.MEDIUM
        else:
            return cls.HIGH


@dataclass
class QLState:
    """
    Stato osservabile dal nodo per prendere decisioni.

    Combina tre fattori:
    - collision_level: storia recente di fallimenti di questo nodo
    - wait_time_level: quanto ha già aspettato
    - traffic_level: quanto traffico percepisce sul canale
    """
    collision_level: CollisionLevel
    wait_time_level: WaitTimeLevel
    traffic_level: TrafficLevel

    def to_index(self) -> int:
        """
        Converte lo stato in un indice unico per la Q-table.
        Totale stati: 4 * 4 * 3 = 48
        """
        n_wait = len(WaitTimeLevel)
        n_traffic = len(TrafficLevel)

        return (self.collision_level.value * n_wait * n_traffic +
                self.wait_time_level.value * n_traffic +
                self.traffic_level.value)

    @classmethod
    def from_index(cls, index: int) -> 'QLState':
        """Ricostruisce lo stato dall'indice"""
        n_wait = len(WaitTimeLevel)
        n_traffic = len(TrafficLevel)

        collision_val = index // (n_wait * n_traffic)
        remainder = index % (n_wait * n_traffic)
        wait_val = remainder // n_traffic
        traffic_val = remainder % n_traffic

        return cls(
            CollisionLevel(collision_val),
            WaitTimeLevel(wait_val),
            TrafficLevel(traffic_val)
        )

    @classmethod
    def total_states(cls) -> int:
        """Numero totale di stati possibili: 4 * 4 * 3 = 48"""
        return len(CollisionLevel) * len(WaitTimeLevel) * len(TrafficLevel)

    def __repr__(self) -> str:
        return (f"State(coll={self.collision_level.name}, "
                f"wait={self.wait_time_level.name}, "
                f"traffic={self.traffic_level.name})")

    def __eq__(self, other) -> bool:
        if not isinstance(other, QLState):
            return False
        return (self.collision_level == other.collision_level and
                self.wait_time_level == other.wait_time_level and
                self.traffic_level == other.traffic_level)

    def __hash__(self) -> int:
        return hash((self.collision_level, self.wait_time_level, self.traffic_level))