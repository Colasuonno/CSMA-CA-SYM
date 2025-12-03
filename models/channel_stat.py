from config_params import NodeStatType, DEFAULT_NODE_STATS, ChannelStatType, DEFAULT_CHANNEL_STATS
import logging


_logger = logging.getLogger(__name__)

class ChannelStat:


    def __init__(self, channel):
        self.channel = channel
        self.stats = DEFAULT_CHANNEL_STATS.copy()

    def evaluate_stat(self, stat_type: ChannelStatType):
        match stat_type:
            case ChannelStatType.AVG_NEAR_NODES:
                return sum([len(self.channel.get_nodes_from_pos(node)) for node in self.channel.nodes]) / len(self.channel.nodes)
            case ChannelStatType.TOTAL_GENERATED_PACKETS:
                return sum([node.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_GENERATED) for node in self.channel.nodes])
            case ChannelStatType.TOTAL_DATA_PACKET_SENT:
                return sum([node.stats.evaluate_stat(NodeStatType.DATA_PACKET_SENT) for node in self.channel.nodes])
            case ChannelStatType.TOTAL_SENT_PACKETS:
                return sum([node.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_SENT) for node in self.channel.nodes])
            case ChannelStatType.TOTAL_LOSS_PACKETS:
                return sum([node.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_LOSS) for node in self.channel.nodes])
            case ChannelStatType.TOTAL_TIMEOUT_NODES:
                return sum([node.stats.evaluate_stat(NodeStatType.TIMEOUT_RETRY) for node in self.channel.nodes])
            case ChannelStatType.AVG_PACKET_LOSS_PERCENTAGE:
                return sum([node.stats.evaluate_stat(NodeStatType.PACKET_LOSS_PERCENTAGE) for node in self.channel.nodes]) / (len(self.channel.nodes))
            case _:
                return self.stats[stat_type]


    def append_stat(self, stat_type: ChannelStatType, value):
        self.stats[stat_type] += value

    def print_stats(self):
        _logger.info(f"=== Channel Statistics ===")
        for stat_type, value in self.stats.items():
            _logger.info(f"{stat_type.name}: {self.evaluate_stat(stat_type):.2f}")
        _logger.info("=" * 40)