from config_params import NodeStatType, DEFAULT_NODE_STATS
import logging

_logger = logging.getLogger(__name__)

class NodeStat:


    def __init__(self, node_id: int):
        self.node_id = node_id
        self.stats = DEFAULT_NODE_STATS.copy()

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
            case _:
                return self.stats[stat_type]


    def append_stat(self, stat_type: NodeStatType, value):
        self.stats[stat_type] += value

    def print_stats(self):
        _logger.info(f"=== Node {self.node_id} Statistics ===")
        for stat_type, value in self.stats.items():
            _logger.info(f"{stat_type.name}: {self.evaluate_stat(stat_type):.2f}")
        _logger.info("=" * 40)