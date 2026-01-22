import random
import csv
import os
from datetime import datetime

from models.channel_stat import ChannelStat
from models.v2.node2 import Node2
from models.v2.karmedbandit_rl_node import RLKArmedBanditNode
from models.v2.qlearning_rl_node import QLearningNode
from models.v2.channel2 import Channel2
from config_params import N_NODES, SIMULATION_TICKS, NodeStatus, NodeStatType, ChannelStatType
import logging

_logger = logging.getLogger(__name__)
logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


def get_aggregated_node_stats(channel) -> dict:
    """
    Calcola le statistiche aggregate (medie) di tutti i nodi.
    Ritorna un dizionario con tutte le metriche medie.
    """
    nodes = channel.nodes
    n_nodes = len(nodes)

    if n_nodes == 0:
        return {}

    # Statistiche base aggregate
    stats = {
        # Medie delle statistiche base dei nodi
        'avg_data_packet_sent': sum(n.stats.evaluate_stat(NodeStatType.DATA_PACKET_SENT) for n in nodes) / n_nodes,
        'avg_control_packet_sent': sum(
            n.stats.evaluate_stat(NodeStatType.CONTROL_PACKET_SENT) for n in nodes) / n_nodes,
        'avg_total_packet_sent': sum(n.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_SENT) for n in nodes) / n_nodes,
        'avg_data_packet_generated': sum(
            n.stats.evaluate_stat(NodeStatType.DATA_PACKET_GENERATED) for n in nodes) / n_nodes,
        'avg_control_packet_generated': sum(
            n.stats.evaluate_stat(NodeStatType.CONTROL_PACKET_GENERATED) for n in nodes) / n_nodes,
        'avg_total_packet_generated': sum(
            n.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_GENERATED) for n in nodes) / n_nodes,
        'avg_data_packet_loss': sum(n.stats.evaluate_stat(NodeStatType.DATA_PACKET_LOSS) for n in nodes) / n_nodes,
        'avg_control_packet_loss': sum(
            n.stats.evaluate_stat(NodeStatType.CONTROL_PACKET_LOSS) for n in nodes) / n_nodes,
        'avg_total_packet_loss': sum(n.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_LOSS) for n in nodes) / n_nodes,
        'avg_packet_loss_percentage': sum(
            n.stats.evaluate_stat(NodeStatType.PACKET_LOSS_PERCENTAGE) for n in nodes) / n_nodes,
        'avg_success_sent_bits': sum(
            n.stats.evaluate_stat(NodeStatType.TOTAL_SUCCESS_SENT_BITS) for n in nodes) / n_nodes,
        'avg_throughput_per_node': sum(
            n.stats.evaluate_stat(NodeStatType.SUCCESS_BITS_OVER_SIM_TICKS) for n in nodes) / n_nodes,
        'avg_timeout_retry': sum(n.stats.evaluate_stat(NodeStatType.TIMEOUT_RETRY) for n in nodes) / n_nodes,
        'avg_cw_enters': sum(n.stats.evaluate_stat(NodeStatType.CW_ENTERS) for n in nodes) / n_nodes,
        'avg_cw_increase': sum(n.stats.evaluate_stat(NodeStatType.CW_INCREASE) for n in nodes) / n_nodes,
        'avg_recent_packet_loss_pct': sum(n.stats.get_recent_packet_loss_percentage() for n in nodes) / n_nodes,

        # Totali (non medie)
        'total_data_packet_sent': sum(n.stats.evaluate_stat(NodeStatType.DATA_PACKET_SENT) for n in nodes),
        'total_control_packet_sent': sum(n.stats.evaluate_stat(NodeStatType.CONTROL_PACKET_SENT) for n in nodes),
        'total_packet_sent': sum(n.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_SENT) for n in nodes),
        'total_packet_loss': sum(n.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_LOSS) for n in nodes),
        'total_success_bits': sum(n.stats.evaluate_stat(NodeStatType.TOTAL_SUCCESS_SENT_BITS) for n in nodes),
    }

    # Statistiche specifiche per Q-Learning (se i nodi sono QLearningNode)
    if hasattr(nodes[0], 'retry_count'):
        stats['avg_current_retry_count'] = sum(n.retry_count for n in nodes) / n_nodes
        stats['max_retry_count'] = max(n.retry_count for n in nodes)

    if hasattr(nodes[0], 'epsilon'):
        stats['avg_epsilon'] = sum(n.epsilon for n in nodes) / n_nodes
        stats['min_epsilon'] = min(n.epsilon for n in nodes)
        stats['max_epsilon'] = max(n.epsilon for n in nodes)

    if hasattr(nodes[0], 'recent_busy_events'):
        avg_busy_ratio = sum(
            sum(n.recent_busy_events) / len(n.recent_busy_events) if len(n.recent_busy_events) > 0 else 0
            for n in nodes
        ) / n_nodes
        stats['avg_busy_ratio'] = avg_busy_ratio

    if hasattr(nodes[0], 'recent_collision_events'):
        avg_collision_ratio = sum(
            sum(n.recent_collision_events) / len(n.recent_collision_events) if len(n.recent_collision_events) > 0 else 0
            for n in nodes
        ) / n_nodes
        stats['avg_collision_ratio'] = avg_collision_ratio

    # Statistiche sullo stato dei nodi
    status_counts = {}
    for status in NodeStatus:
        count = sum(1 for n in nodes if n.status == status)
        status_counts[f'nodes_in_{status.name}'] = count
    stats.update(status_counts)

    # Statistiche NAV
    stats['avg_nav_seconds'] = sum(n.nav_seconds for n in nodes) / n_nodes
    stats['max_nav_seconds'] = max(n.nav_seconds for n in nodes)
    stats['nodes_with_active_nav'] = sum(1 for n in nodes if n.nav_seconds > 0)

    return stats


def get_cluster_stats(channel) -> dict:
    """
    Calcola statistiche aggregate PER CLUSTER.
    """
    nodes = channel.nodes

    # Raggruppa nodi per cluster
    clusters = {}
    for node in nodes:
        cluster_id = node.cluster_id
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(node)

    stats = {}

    for cluster_id, cluster_nodes in clusters.items():
        n_nodes = len(cluster_nodes)
        prefix = f'cluster_{cluster_id}'

        # Probabilità di invio (dovrebbe essere uguale per tutti nel cluster)
        stats[f'{prefix}_send_probability'] = cluster_nodes[0].send_probability if hasattr(cluster_nodes[0],
                                                                                           'send_probability') else 'N/A'
        stats[f'{prefix}_n_nodes'] = n_nodes

        # Metriche di performance
        stats[f'{prefix}_avg_packet_sent'] = sum(
            n.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_SENT) for n in cluster_nodes
        ) / n_nodes

        stats[f'{prefix}_avg_packet_loss'] = sum(
            n.stats.evaluate_stat(NodeStatType.TOTAL_PACKET_LOSS) for n in cluster_nodes
        ) / n_nodes

        stats[f'{prefix}_avg_packet_loss_pct'] = sum(
            n.stats.evaluate_stat(NodeStatType.PACKET_LOSS_PERCENTAGE) for n in cluster_nodes
        ) / n_nodes

        stats[f'{prefix}_total_throughput'] = sum(
            n.stats.evaluate_stat(NodeStatType.TOTAL_SUCCESS_SENT_BITS) for n in cluster_nodes
        )

        stats[f'{prefix}_avg_throughput_per_node'] = stats[f'{prefix}_total_throughput'] / n_nodes

        stats[f'{prefix}_avg_timeout_retry'] = sum(
            n.stats.evaluate_stat(NodeStatType.TIMEOUT_RETRY) for n in cluster_nodes
        ) / n_nodes

        stats[f'{prefix}_avg_cw_enters'] = sum(
            n.stats.evaluate_stat(NodeStatType.CW_ENTERS) for n in cluster_nodes
        ) / n_nodes

        stats[f'{prefix}_avg_cw_increase'] = sum(
            n.stats.evaluate_stat(NodeStatType.CW_INCREASE) for n in cluster_nodes
        ) / n_nodes

        # Ratio CW increase / CW enters (indica quanto spesso serve raddoppiare)
        total_cw_enters = sum(n.stats.evaluate_stat(NodeStatType.CW_ENTERS) for n in cluster_nodes)
        total_cw_increase = sum(n.stats.evaluate_stat(NodeStatType.CW_INCREASE) for n in cluster_nodes)
        stats[f'{prefix}_cw_increase_ratio'] = (
            total_cw_increase / total_cw_enters if total_cw_enters > 0 else 0
        )

        # Q-Learning specific stats
        if hasattr(cluster_nodes[0], 'epsilon'):
            stats[f'{prefix}_avg_epsilon'] = sum(n.epsilon for n in cluster_nodes) / n_nodes

        if hasattr(cluster_nodes[0], 'retry_count'):
            stats[f'{prefix}_avg_retry_count'] = sum(n.retry_count for n in cluster_nodes) / n_nodes

        if hasattr(cluster_nodes[0], 'recent_busy_events'):
            stats[f'{prefix}_avg_busy_ratio'] = sum(
                sum(n.recent_busy_events) / len(n.recent_busy_events)
                if len(n.recent_busy_events) > 0 else 0
                for n in cluster_nodes
            ) / n_nodes

        if hasattr(cluster_nodes[0], 'recent_collision_events'):
            stats[f'{prefix}_avg_collision_ratio'] = sum(
                sum(n.recent_collision_events) / len(n.recent_collision_events)
                if len(n.recent_collision_events) > 0 else 0
                for n in cluster_nodes
            ) / n_nodes

    # Statistiche comparative tra cluster
    if len(clusters) > 1:
        throughputs = [stats[f'cluster_{cid}_total_throughput'] for cid in clusters.keys()]
        stats['cluster_throughput_variance'] = (
                sum((t - sum(throughputs) / len(throughputs)) ** 2 for t in throughputs) / len(throughputs)
        )
        stats['cluster_throughput_max_min_ratio'] = (
            max(throughputs) / min(throughputs) if min(throughputs) > 0 else float('inf')
        )

        # Fairness index (Jain's fairness index)
        if sum(throughputs) > 0:
            stats['jain_fairness_index'] = (
                    sum(throughputs) ** 2 / (len(throughputs) * sum(t ** 2 for t in throughputs))
            )
        else:
            stats['jain_fairness_index'] = 0

    return stats


def get_channel_stats(channel) -> dict:

    stats = {
        'total_generated_packets': channel.stats.evaluate_stat(ChannelStatType.TOTAL_GENERATED_PACKETS),
        'total_data_packet_sent': channel.stats.evaluate_stat(ChannelStatType.TOTAL_DATA_PACKET_SENT),
        'total_sent_packets': channel.stats.evaluate_stat(ChannelStatType.TOTAL_SENT_PACKETS),
        'total_loss_packets': channel.stats.evaluate_stat(ChannelStatType.TOTAL_LOSS_PACKETS),
        'total_timeout_nodes': channel.stats.evaluate_stat(ChannelStatType.TOTAL_TIMEOUT_NODES),
        'avg_packet_loss_percentage': channel.stats.evaluate_stat(ChannelStatType.AVG_PACKET_LOSS_PERCENTAGE),
        'total_throughput': channel.stats.evaluate_stat(ChannelStatType.TOTAL_THROUGHPUT),
        'avg_recent_packet_loss': channel.stats.get_avg_recent_packet_loss(),
    }
    return stats


def save_stats_to_csv(tick: int, channel, csv_writer, is_first_write: bool):
    """
    Salva le statistiche correnti in un file CSV.
    """
    # Raccogli tutte le statistiche
    channel_stats = get_channel_stats(channel)
    node_stats = get_aggregated_node_stats(channel)
    #cluster_stats = get_cluster_stats(channel)

    # Combina tutto in un unico record
    record = {
        'tick': tick,
        'timestamp': datetime.now().isoformat(),
    }

    # Aggiungi statistiche channel con prefisso
    for key, value in channel_stats.items():
        record[f'channel_{key}'] = value

    # Aggiungi statistiche nodi aggregate con prefisso
    for key, value in node_stats.items():
        record[f'nodes_{key}'] = value


    """
    
    for key, value in cluster_stats.items():
        record[key] = value
    """

    # Scrivi header se è la prima volta
    if is_first_write:
        csv_writer.writerow(record.keys())

    csv_writer.writerow(record.values())


def run_simulation(output_dir: str = "qlearning_res"):


    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = os.path.join(output_dir, f"simulation_stats_{timestamp}.csv")

    _logger.info(f"Saving statistics to: {csv_filename}")

    # Inizializza channel e nodi
    channel = Channel2()

    for n in range(N_NODES):
        channel.nodes.append(QLearningNode(n, channel))

    _logger.info(f"Initialized {N_NODES} nodes")

    # Apri file CSV
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        is_first_write = True

        for t in range(SIMULATION_TICKS):

            # Salva statistiche ogni 10000 tick
            if t % 10000 == 0:
                _logger.info(f"@{t}")
                channel.stats.print_stats()

                # Salva su CSV
                save_stats_to_csv(t, channel, csv_writer, is_first_write)
                is_first_write = False

                # Flush per sicurezza
                csvfile.flush()

            # Tick dei nodi (ordine casuale)
            starting_node = random.randint(0, N_NODES - 1)
            for n in range(N_NODES):
                channel.nodes[(n + starting_node) % N_NODES].tick(t)

            # Tick del channel
            channel.tick(t)

        # Salva statistiche finali
        _logger.info(f"@{SIMULATION_TICKS} (FINAL)")
        save_stats_to_csv(SIMULATION_TICKS, channel, csv_writer, False)

    _logger.info("Simulation ended")
    _logger.info(f"Statistics saved to: {csv_filename}")

    # Stampa policy finali dei nodi
    for n in range(N_NODES):
        channel.nodes[n].print_policy(channel)

    # Stampa statistiche finali del channel
    channel.stats.print_stats()

    return csv_filename


if __name__ == '__main__':
    run_simulation()