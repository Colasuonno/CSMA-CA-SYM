from config_params import NodeStatType, DEFAULT_NODE_STATS, SIMULATION_TICKS
import logging
from collections import deque

_logger = logging.getLogger(__name__)

class NodeStat:


    def __init__(self, node_id: int):
        self.node_id = node_id
        self.stats = DEFAULT_NODE_STATS.copy()

        # 10k steps for stats window
        self.window_size = 10_000
        self.recent_sent = deque(maxlen=self.window_size)
        self.recent_loss = deque(maxlen=self.window_size)

    def evaluate_stat(self, stat_type: NodeStatType):
        match stat_type:
            case NodeStatType.TOTAL_PACKET_SENT:
                return self.evaluate_stat(NodeStatType.DATA_PACKET_SENT) + self.evaluate_stat(NodeStatType.CONTROL_PACKET_SENT)
            case NodeStatType.TOTAL_PACKET_LOSS:
                return self.evaluate_stat(NodeStatType.DATA_PACKET_LOSS) + self.evaluate_stat(NodeStatType.CONTROL_PACKET_LOSS)
            case NodeStatType.TOTAL_PACKET_GENERATED:
                return self.evaluate_stat(NodeStatType.DATA_PACKET_GENERATED) + self.evaluate_stat(NodeStatType.CONTROL_PACKET_GENERATED)
            case NodeStatType.PACKET_LOSS_PERCENTAGE:
                return self.evaluate_stat(NodeStatType.TOTAL_PACKET_LOSS) / self.evaluate_stat(NodeStatType.TOTAL_PACKET_SENT) if self.evaluate_stat(NodeStatType.TOTAL_PACKET_SENT) > 0 else 0
            case NodeStatType.SUCCESS_BITS_OVER_SIM_TICKS:
                return self.evaluate_stat(NodeStatType.TOTAL_SUCCESS_SENT_BITS) / SIMULATION_TICKS
            case _:
                return self.stats[stat_type]

    def get_recent_packet_loss_percentage(self) -> float:
        recent_sent_count = len(self.recent_sent)
        recent_loss_count = len(self.recent_loss)

        total = recent_sent_count + recent_loss_count
        if total == 0:
            return 0.0

        return recent_loss_count / total

    def append_stat(self, stat_type: NodeStatType, value, tick: int):
        self.stats[stat_type] += value

        match stat_type:
            case NodeStatType.DATA_PACKET_SENT | NodeStatType.CONTROL_PACKET_SENT:
                self.recent_sent.append((tick, value))
            case NodeStatType.DATA_PACKET_LOSS | NodeStatType.CONTROL_PACKET_LOSS:
                self.recent_loss.append((tick, value))

    def print_stats(self):
        _logger.info(f"=== Node {self.node_id} Statistics ===")
        for stat_type, value in self.stats.items():
            _logger.info(f"{stat_type.name}: {self.evaluate_stat(stat_type):.2f}")
        _logger.info("=" * 40)