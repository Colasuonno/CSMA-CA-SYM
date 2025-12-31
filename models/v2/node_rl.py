"""
NodeQL: Estensione di Node2 con Q-Learning per decisioni WAIT/SEND

Invece di usare un timer di backoff fisso, ad ogni tick l'agente
decide se aspettare ancora (WAIT) o trasmettere (SEND).
"""

from config_params import NodeStatus, NodeStatType, SIFS, CW_MIN
from models.v2.node2 import Node2
from models.packet import Packet, PacketType
from utils.timers import NodeTimer, NodeTimerType

from models.rl_agent import QLAgent, QLConfig
from models.ql_types import TransmissionOutcome, Action

import logging

_logger = logging.getLogger(__name__)


class NodeQL(Node2):
    """
    Nodo con Contention Window gestita tramite Q-Learning.
    
    Differenze da Node2:
    - Non usa timer di backoff con countdown fisso
    - Ad ogni tick chiede all'agente: WAIT o SEND?
    - L'agente impara quando è meglio trasmettere
    """
    
    def __init__(self, node_id: int, channel, ql_config: QLConfig = None):
        super().__init__(node_id, channel)
        
        # Agente Q-Learning
        self.ql_agent = QLAgent(node_id, ql_config)
        
        # Flag per indicare che siamo in modalità Q-Learning backoff
        self._in_ql_backoff = False
        
        # Contatore minimo di wait (per evitare trasmissioni immediate)
        self._min_wait_ticks = 1
        self._current_wait_ticks = 0
    
    # === Override: enter_cw ===
    
    def enter_cw(self):
        """
        OVERRIDE: Invece di creare un timer con countdown fisso,
        entra in modalità Q-Learning backoff.
        """
        self._in_ql_backoff = True
        self._current_wait_ticks = 0
        self.ql_agent.reset_backoff()
        
        _logger.info(f"Node {self.node_id} - Entering Q-Learning backoff")
        
        # Stats compatibilità
        if self.ql_agent.consecutive_failures == 0:
            self.stats.append_stat(NodeStatType.CW_ENTERS, 1)
        else:
            self.stats.append_stat(NodeStatType.CW_INCREASE, 1)
    
    # === Override: timer_tick ===
    
    def timer_tick(self, t):
        """
        OVERRIDE: Gestisce il backoff con Q-Learning.
        """
        # Decrementa NAV
        if self.nav_seconds > 0:
            self.nav_seconds -= 1
        
        # Gestione timeout (invariato)
        if self.timeout_seconds is not None and self.timeout_seconds > 0:
            self.timeout_seconds -= 1
        
        if self.timeout_seconds is not None and self.timeout_seconds == 0:
            _logger.info(f"@ {t} Node {self.node_id} - Timeout")
            self.stats.append_stat(NodeStatType.TIMEOUT_RETRY, 1)
            
            # Notifica timeout all'agente
            self.ql_agent.process_outcome(TransmissionOutcome.TIMEOUT)
            
            self.status = NodeStatus.TIMEOUT
            self.enter_cw()
            self.timeout_seconds = None
            return
        
        # === Q-Learning Backoff ===
        if self._in_ql_backoff:
            self._handle_ql_backoff(t)
            return
        
        # Timer normale (per CTS, DATA, ACK - non modificato)
        if not self.timer:
            return
        
        # Se in backoff normale e canale busy, freeze
        if self.timer.timer_type == NodeTimerType.BACKOFF and self.channel_busy():
            return
        
        self.timer.waiting_ticks -= 1
        
        if self.timer.waiting_ticks == 0:
            self._handle_timer_expired(t)
    
    def _handle_ql_backoff(self, t):
        """Gestisce un tick di backoff con Q-Learning"""
        
        # Osserva il canale per l'agente
        self.ql_agent.observe_channel(self.channel_busy())
        
        # Se canale occupato, aspetta sempre (freeze come in 802.11)
        if self.channel_busy():
            return
        
        # Incrementa wait e chiedi all'agente cosa fare
        self._current_wait_ticks += 1
        
        # Minimo 1 tick di attesa prima di poter trasmettere
        if self._current_wait_ticks < self._min_wait_ticks:
            self.ql_agent.select_action()  # Registra comunque per stats
            return
        
        # Chiedi all'agente: WAIT o SEND?
        action = self.ql_agent.select_action()
        
        if action == Action.SEND:
            self._execute_send(t)
    
    def _execute_send(self, t):
        """Esegue la trasmissione quando l'agente decide SEND"""
        self._in_ql_backoff = False
        
        # Cambia stato in base a dove eravamo
        match self.status:
            case NodeStatus.SENDING_RTS:
                self.status = NodeStatus.WAITING_CTS
            case NodeStatus.TIMEOUT:
                self.status = NodeStatus.END_BACKOFF_TIMEOUT
                self.reset_timer()
                self.reset_timeout()
                return
            case _:
                _logger.warning(f"Node {self.node_id} - Unexpected status in backoff: {self.status}")
                return
        
        # Invia il pacchetto
        if self.current_packet_buff:
            self.timeout_seconds = self.current_packet_buff.timeout
            self.channel.send_packet(t, self.current_packet_buff)
            
            match self.current_packet_buff.packet_type:
                case PacketType.DATA:
                    self.stats.append_stat(NodeStatType.DATA_PACKET_GENERATED, 1)
                case _:
                    self.stats.append_stat(NodeStatType.CONTROL_PACKET_GENERATED, 1)
        
        _logger.info(f"@ {t} Node {self.node_id} - Q-Learning decided SEND after {self._current_wait_ticks} ticks")
    
    def _handle_timer_expired(self, t):
        """Gestisce scadenza timer normale (non Q-Learning)"""
        match self.timer.timer_type:
            case NodeTimerType.BACKOFF:
                # Non dovrebbe arrivare qui con Q-Learning, ma per sicurezza
                match self.status:
                    case NodeStatus.SENDING_RTS:
                        self.status = NodeStatus.WAITING_CTS
                    case NodeStatus.TIMEOUT:
                        self.status = NodeStatus.END_BACKOFF_TIMEOUT
                        self.reset_timer()
                        self.reset_timeout()
                        return
                    case _:
                        raise Exception(f"Invalid status: {self.status}")
                
                self.send_packet_from_timer(t)
                self.reset_timer()
            
            case NodeTimerType.NORMAL_WAIT:
                match self.status:
                    case NodeStatus.SENDING_RTS:
                        self.current_packet_buff = self.build_rts_packet()
                        self.enter_cw()  # Entra in Q-Learning backoff
                    case NodeStatus.SENDING_CTS:
                        self.status = NodeStatus.WAITING_DATA
                        self.send_packet_from_timer(t)
                        self.reset_timer()
                    case NodeStatus.SENDING_DATA:
                        self.status = NodeStatus.WAITING_ACK
                        self.send_packet_from_timer(t)
                        self.reset_timer()
                    case NodeStatus.SENDING_ACK:
                        self.status = NodeStatus.IDLE
                        self.send_packet_from_timer(t)
                        self.reset_timer()
                        self.reset_timeout()
                    case _:
                        raise Exception(f"Invalid status: {self.status}")
    
    # === Override: receive_packet ===
    
    def receive_packet(self, t, packet: Packet):
        """OVERRIDE: Intercetta ACK per notificare successo"""
        
        if self.should_skip_packet(packet):
            return
        
        sender = self.channel.nodes[packet.sender_address]
        
        match packet.packet_type:
            case PacketType.DATA:
                sender.stats.append_stat(NodeStatType.DATA_PACKET_SENT, 1)
            case _:
                sender.stats.append_stat(NodeStatType.CONTROL_PACKET_SENT, 1)
        
        match packet.packet_type:
            case PacketType.RTS:
                if not self.status.can_start_new_connections():
                    _logger.error(f"@ {t} Node {self.node_id} - RTS while busy")
                else:
                    self.status = NodeStatus.SENDING_CTS
                    self.current_packet_buff = self.build_cts_packet(packet)
                    self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, SIFS, self.current_packet_buff)

            case PacketType.CTS:
                # Accetta CTS anche se siamo ancora in SENDING_RTS
                # (può succedere per timing del canale)
                if self.status not in [NodeStatus.WAITING_CTS, NodeStatus.SENDING_RTS]:
                    raise Exception(f"Invalid status for CTS: {self.status}")

                self.reset_timeout()
                self.status = NodeStatus.SENDING_DATA
                self.current_packet_buff = self.data_packet_buff
                self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, SIFS, self.current_packet_buff)
            
            case PacketType.DATA:
                if self.status != NodeStatus.WAITING_DATA:
                    raise Exception(f"Invalid status for DATA: {self.status}")
                
                self.reset_timeout()
                self.status = NodeStatus.SENDING_ACK
                self.current_packet_buff = self.build_ack_packet(packet)
                self.timer = NodeTimer(NodeTimerType.NORMAL_WAIT, SIFS, self.current_packet_buff)
            
            case PacketType.ACK:
                if self.status != NodeStatus.WAITING_ACK:
                    raise Exception(f"Invalid status for ACK: {self.status}")
                
                # === Q-Learning: notifica successo ===
                self.ql_agent.process_outcome(TransmissionOutcome.SUCCESS)
                
                self.reset_timeout()
                self.reset_timer()
                self.status = NodeStatus.IDLE
                self.current_packet_buff = None
                self.data_packet_buff = None
                
                _logger.info(f"@ {t} Node {self.node_id} - ACK received, SUCCESS!")
        
        _logger.debug(f"@ {t} Node {self.node_id} - Received {packet.packet_type.name}")
    
    # === Metodi utilità Q-Learning ===
    
    def get_ql_stats(self) -> dict:
        """Restituisce statistiche Q-Learning"""
        return self.ql_agent.get_stats_summary()
    
    def print_ql_stats(self):
        """Stampa le statistiche Q-Learning in formato leggibile"""
        stats = self.ql_agent.get_stats_summary()
        
        _logger.info(f"\n{'='*60}")
        _logger.info(f"  Q-Learning Stats - Node {stats['node_id']}")
        _logger.info(f"{'='*60}")
        
        _logger.info(f"\n📊 Trasmissioni:")
        _logger.info(f"   Totali:       {stats['total_transmissions']}")
        _logger.info(f"   Successi:     {stats['successful_transmissions']}")
        _logger.info(f"   Success Rate: {stats['success_rate']}")
        _logger.info(f"   Fallimenti consecutivi: {stats['consecutive_failures']}")
        
        _logger.info(f"\n🎰 Exploration vs Exploitation:")
        _logger.info(f"   Explorazioni:  {stats['explorations']}")
        _logger.info(f"   Exploitations: {stats['exploitations']}")
        _logger.info(f"   Epsilon:       {stats['epsilon']}")
        
        _logger.info(f"\n⏱️  Azioni WAIT/SEND:")
        _logger.info(f"   Total WAITs:   {stats['total_waits']}")
        _logger.info(f"   Total SENDs:   {stats['total_sends']}")
        _logger.info(f"   Ratio:         {stats['wait_send_ratio']}")
        _logger.info(f"   Avg wait/send: {stats['avg_wait_per_send']} ticks")
        
        _logger.info(f"\n💰 Reward totale: {stats['total_reward']}")
        
        _logger.info(f"\n📡 Traffico percepito:")
        _logger.info(f"   Livello:    {stats['traffic_level']}")
        _logger.info(f"   Busy ratio: {stats['busy_ratio']}")
        
        _logger.info(f"\n🔄 Stato corrente: {stats['current_state']}")
        _logger.info(f"{'='*60}\n")
    
    def print_q_table(self):
        """Stampa la Q-table"""
        self.ql_agent.print_q_table()
    
    @property
    def epsilon(self) -> float:
        return self.ql_agent.epsilon
    
    @property
    def current_ql_state(self):
        return self.ql_agent.get_current_state()