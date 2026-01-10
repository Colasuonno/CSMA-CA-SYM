"""
Simulation Runner for CSMA/CA Network Comparison
Compares adaptive RL-based protocol with static CSMA/CA baseline
Supports parameter sweeps for: number of nodes, packet probability, epsilon
"""

import random
import csv
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import logging

# Import your existing modules
from models.v2.node2 import Node2
from models.v2.karmedbandit_rl_node import RLKArmedBanditNode
from models.v2.channel2 import Channel2
from config_params import (
    NodeStatType, ChannelStatType, NodeStatus,
    SIMULATION_TICKS, PROBABILITY_OF_SENDING_PACKET
)

_logger = logging.getLogger(__name__)


@dataclass
class SimulationConfig:
    """Configuration for a single simulation run"""
    n_nodes: int
    simulation_ticks: int
    packet_probability: float
    epsilon: float  # For RL nodes, 0 = greedy, 1 = random
    node_type: str  # "baseline" or "rl"
    run_id: int = 0


@dataclass
class SimulationResult:
    """Results from a single simulation run"""
    # Config info
    n_nodes: int
    simulation_ticks: int
    packet_probability: float
    epsilon: float
    node_type: str
    run_id: int

    # Key metrics
    total_packets_generated: int
    total_packets_sent: int
    total_packets_lost: int
    total_data_packets_sent: int
    total_timeouts: int

    # Derived metrics
    packet_delivery_ratio: float  # successfully delivered / generated
    packet_loss_ratio: float
    throughput: float  # data packets sent / simulation ticks
    avg_packet_loss_per_node: float
    avg_near_nodes: float

    # Timing
    timestamp: str


def run_single_simulation(config: SimulationConfig, verbose: bool = False) -> SimulationResult:
    """Run a single simulation with the given configuration"""

    # Temporarily override config params
    import config_params
    original_prob = config_params.PROBABILITY_OF_SENDING_PACKET
    config_params.PROBABILITY_OF_SENDING_PACKET = config.packet_probability

    channel = Channel2()

    # Create nodes based on type
    for n in range(config.n_nodes):
        if config.node_type == "rl":
            node = RLKArmedBanditNode(config.epsilon, n, channel)
        else:
            node = Node2(n, channel)  # baseline
        channel.nodes.append(node)

    if verbose:
        _logger.info(f"Running simulation: {config.node_type}, n={config.n_nodes}, "
                     f"prob={config.packet_probability}, eps={config.epsilon}")

    # Run simulation
    for t in range(config.simulation_ticks):
        starting_node = random.randint(0, config.n_nodes - 1)
        for n in range(config.n_nodes):
            channel.nodes[(n + starting_node) % config.n_nodes].tick(t)
        channel.tick(t)

    # Collect results
    total_generated = channel.stats.evaluate_stat(ChannelStatType.TOTAL_GENERATED_PACKETS)
    total_sent = channel.stats.evaluate_stat(ChannelStatType.TOTAL_SENT_PACKETS)
    total_lost = channel.stats.evaluate_stat(ChannelStatType.TOTAL_LOSS_PACKETS)
    total_data_sent = channel.stats.evaluate_stat(ChannelStatType.TOTAL_DATA_PACKET_SENT)
    total_timeouts = channel.stats.evaluate_stat(ChannelStatType.TOTAL_TIMEOUT_NODES)
    avg_near = channel.stats.evaluate_stat(ChannelStatType.AVG_NEAR_NODES)

    # Calculate derived metrics
    pdr = total_data_sent / total_generated if total_generated > 0 else 0
    plr = total_lost / total_sent if total_sent > 0 else 0
    throughput = total_data_sent / config.simulation_ticks
    avg_loss_per_node = total_lost / config.n_nodes

    # Restore original config
    config_params.PROBABILITY_OF_SENDING_PACKET = original_prob

    return SimulationResult(
        n_nodes=config.n_nodes,
        simulation_ticks=config.simulation_ticks,
        packet_probability=config.packet_probability,
        epsilon=config.epsilon,
        node_type=config.node_type,
        run_id=config.run_id,
        total_packets_generated=int(total_generated),
        total_packets_sent=int(total_sent),
        total_packets_lost=int(total_lost),
        total_data_packets_sent=int(total_data_sent),
        total_timeouts=int(total_timeouts),
        packet_delivery_ratio=pdr,
        packet_loss_ratio=plr,
        throughput=throughput,
        avg_packet_loss_per_node=avg_loss_per_node,
        avg_near_nodes=avg_near,
        timestamp=datetime.now().isoformat()
    )


def run_experiment_sweep(
        node_counts: List[int],
        packet_probabilities: List[float],
        epsilons: List[float],
        simulation_ticks: int = 10000,
        runs_per_config: int = 3,
        output_dir: str = "results"
) -> List[SimulationResult]:
    """
    Run a full parameter sweep experiment

    Args:
        node_counts: List of node counts to test (e.g., [50, 100, 500, 1000])
        packet_probabilities: List of packet generation probabilities (e.g., [0.001, 0.01, 0.05])
        epsilons: List of epsilon values for RL (e.g., [0.0, 0.1, 0.3, 0.5])
        simulation_ticks: Number of ticks per simulation
        runs_per_config: Number of runs per configuration (for averaging)
        output_dir: Directory to save results
    """
    os.makedirs(output_dir, exist_ok=True)

    all_results = []
    total_runs = len(node_counts) * len(packet_probabilities) * (1 + len(epsilons)) * runs_per_config
    current_run = 0

    # Run baseline (static CSMA/CA) - epsilon doesn't matter for baseline
    for n_nodes in node_counts:
        for prob in packet_probabilities:
            for run_id in range(runs_per_config):
                current_run += 1
                _logger.info(f"Progress: {current_run}/{total_runs}")

                config = SimulationConfig(
                    n_nodes=n_nodes,
                    simulation_ticks=simulation_ticks,
                    packet_probability=prob,
                    epsilon=0.0,
                    node_type="baseline",
                    run_id=run_id
                )
                result = run_single_simulation(config, verbose=True)
                all_results.append(result)

    # Run RL variants with different epsilons
    for n_nodes in node_counts:
        for prob in packet_probabilities:
            for eps in epsilons:
                for run_id in range(runs_per_config):
                    current_run += 1
                    _logger.info(f"Progress: {current_run}/{total_runs}")

                    config = SimulationConfig(
                        n_nodes=n_nodes,
                        simulation_ticks=simulation_ticks,
                        packet_probability=prob,
                        epsilon=eps,
                        node_type="rl",
                        run_id=run_id
                    )
                    result = run_single_simulation(config, verbose=True)
                    all_results.append(result)

    # Save results
    save_results(all_results, output_dir)

    return all_results


def save_results(results: List[SimulationResult], output_dir: str):
    """Save results to CSV and JSON files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save as CSV
    csv_path = os.path.join(output_dir, f"results_{timestamp}.csv")
    with open(csv_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=asdict(results[0]).keys())
            writer.writeheader()
            for r in results:
                writer.writerow(asdict(r))
    _logger.info(f"Saved CSV results to {csv_path}")

    # Save as JSON
    json_path = os.path.join(output_dir, f"results_{timestamp}.json")
    with open(json_path, 'w') as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    _logger.info(f"Saved JSON results to {json_path}")

    # Generate summary statistics
    summary_path = os.path.join(output_dir, f"summary_{timestamp}.txt")
    with open(summary_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("SIMULATION RESULTS SUMMARY\n")
        f.write(f"Generated: {timestamp}\n")
        f.write("=" * 60 + "\n\n")

        # Group results by configuration
        from collections import defaultdict
        grouped = defaultdict(list)
        for r in results:
            key = (r.node_type, r.n_nodes, r.packet_probability, r.epsilon)
            grouped[key].append(r)

        # Calculate averages for each configuration
        f.write(f"{'Type':<10} {'Nodes':<8} {'Prob':<8} {'Eps':<6} "
                f"{'PDR':<8} {'PLR':<8} {'Throughput':<12}\n")
        f.write("-" * 70 + "\n")

        for key, runs in sorted(grouped.items()):
            node_type, n_nodes, prob, eps = key
            avg_pdr = sum(r.packet_delivery_ratio for r in runs) / len(runs)
            avg_plr = sum(r.packet_loss_ratio for r in runs) / len(runs)
            avg_throughput = sum(r.throughput for r in runs) / len(runs)

            f.write(f"{node_type:<10} {n_nodes:<8} {prob:<8.3f} {eps:<6.2f} "
                    f"{avg_pdr:<8.4f} {avg_plr:<8.4f} {avg_throughput:<12.6f}\n")

    _logger.info(f"Saved summary to {summary_path}")


def quick_test():
    """Quick test with minimal parameters"""
    logging.basicConfig(level=logging.INFO)

    results = run_experiment_sweep(
        node_counts=[50, 100],
        packet_probabilities=[0.01],
        epsilons=[0.1, 0.3],
        simulation_ticks=1000,
        runs_per_config=1,
        output_dir="results_quick_test"
    )

    print(f"\nCompleted {len(results)} simulations")
    return results


def full_experiment():
    """Full experiment as specified in project requirements"""
    logging.basicConfig(level=logging.INFO)

    results = run_experiment_sweep(
        # Vary number of nodes
        node_counts=[50, 100, 250, 500, 1000],
        # Vary packet generation probability
        packet_probabilities=[0.001, 0.005, 0.01, 0.02, 0.05],
        # Vary exploration rate (epsilon) for RL
        epsilons=[0.0, 0.05, 0.1, 0.2, 0.3, 0.5],
        simulation_ticks=10000,
        runs_per_config=5,  # Multiple runs for statistical significance
        output_dir="results_full_experiment_2"
    )

    print(f"\nCompleted {len(results)} simulations")
    return results


if __name__ == '__main__':
    # Run quick test by default, change to full_experiment() for complete analysis
    full_experiment()