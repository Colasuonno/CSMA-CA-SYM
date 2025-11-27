from config_params import NodeStatType, DEFAULT_NODE_STATS, ChannelStatType, DEFAULT_CHANNEL_STATS
import logging


_logger = logging.getLogger(__name__)

class ChannelStat:


    def __init__(self, channel):
        self.channel = channel
        self.stats = DEFAULT_CHANNEL_STATS.copy()

    def evaluate_stat(self, stat_type: ChannelStatType):
        match stat_type:
            case ChannelStatType.TOTAL_GENERATED_PACKETS:
                return sum([node.stats.evaluate_stat(NodeStatType.GENERATED_PACKETS) for node in self.channel.nodes])
            case ChannelStatType.TOTAL_RETRANSMITTED_PACKET_AFTER_ACK_LOST:
                return sum([node.stats.evaluate_stat(NodeStatType.RETRANSMITTED_PACKET_AFTER_ACK_LOST) for node in self.channel.nodes])
            case ChannelStatType.SENT_PACKETS:
                return sum([node.stats.evaluate_stat(NodeStatType.SENT_PACKET) for node in self.channel.nodes])
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