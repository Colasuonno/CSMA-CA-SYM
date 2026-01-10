"""
Visualization and Analysis for CSMA/CA Simulation Results
Generates plots comparing baseline vs RL performance across different parameters
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from pathlib import Path
import numpy as np


def load_results(results_dir: str) -> pd.DataFrame:
    """Load results from the most recent CSV file in the directory"""
    csv_files = list(Path(results_dir).glob("results_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No results CSV files found in {results_dir}")

    latest_file = max(csv_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading results from: {latest_file}")
    return pd.read_csv(latest_file)


def aggregate_results(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate results by configuration (averaging across runs)"""
    group_cols = ['node_type', 'n_nodes', 'packet_probability', 'epsilon']
    metric_cols = ['packet_delivery_ratio', 'packet_loss_ratio', 'throughput',
                   'total_packets_generated', 'total_packets_sent', 'total_packets_lost',
                   'total_data_packets_sent', 'total_timeouts', 'avg_near_nodes']

    agg_dict = {col: ['mean', 'std'] for col in metric_cols}

    aggregated = df.groupby(group_cols).agg(agg_dict).reset_index()
    # Flatten column names
    aggregated.columns = ['_'.join(col).strip('_') for col in aggregated.columns.values]

    return aggregated


def plot_pdr_vs_nodes(df: pd.DataFrame, output_dir: str):
    """Plot Packet Delivery Ratio vs Number of Nodes"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    agg = aggregate_results(df)

    # Filter for a specific packet probability (most common)
    prob = df['packet_probability'].mode()[0]
    subset = agg[agg['packet_probability'] == prob]

    # Plot baseline
    baseline = subset[subset['node_type'] == 'baseline']
    ax = axes[0]
    ax.errorbar(baseline['n_nodes'], baseline['packet_delivery_ratio_mean'],
                yerr=baseline['packet_delivery_ratio_std'], marker='o',
                label='Baseline CSMA/CA', capsize=3)

    # Plot RL variants
    for eps in subset['epsilon'].unique():
        rl = subset[(subset['node_type'] == 'rl') & (subset['epsilon'] == eps)]
        if not rl.empty:
            ax.errorbar(rl['n_nodes'], rl['packet_delivery_ratio_mean'],
                        yerr=rl['packet_delivery_ratio_std'], marker='s',
                        label=f'RL (ε={eps})', capsize=3)

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Packet Delivery Ratio')
    ax.set_title(f'PDR vs Node Count (Packet Prob={prob})')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot throughput
    ax = axes[1]
    ax.errorbar(baseline['n_nodes'], baseline['throughput_mean'],
                yerr=baseline['throughput_std'], marker='o',
                label='Baseline CSMA/CA', capsize=3)

    for eps in subset['epsilon'].unique():
        rl = subset[(subset['node_type'] == 'rl') & (subset['epsilon'] == eps)]
        if not rl.empty:
            ax.errorbar(rl['n_nodes'], rl['throughput_mean'],
                        yerr=rl['throughput_std'], marker='s',
                        label=f'RL (ε={eps})', capsize=3)

    ax.set_xlabel('Number of Nodes')
    ax.set_ylabel('Throughput (data packets/tick)')
    ax.set_title(f'Throughput vs Node Count (Packet Prob={prob})')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'pdr_throughput_vs_nodes.png'), dpi=150)
    plt.close()
    print(f"Saved: pdr_throughput_vs_nodes.png")


def plot_pdr_vs_probability(df: pd.DataFrame, output_dir: str):
    """Plot metrics vs Packet Generation Probability"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    agg = aggregate_results(df)

    # Filter for specific node count
    n_nodes = df['n_nodes'].median()
    n_nodes = df['n_nodes'].unique()[len(df['n_nodes'].unique()) // 2]  # middle value
    subset = agg[agg['n_nodes'] == n_nodes]

    # PDR plot
    ax = axes[0]
    baseline = subset[subset['node_type'] == 'baseline']
    ax.errorbar(baseline['packet_probability'], baseline['packet_delivery_ratio_mean'],
                yerr=baseline['packet_delivery_ratio_std'], marker='o',
                label='Baseline CSMA/CA', capsize=3)

    for eps in sorted(subset['epsilon'].unique()):
        rl = subset[(subset['node_type'] == 'rl') & (subset['epsilon'] == eps)]
        if not rl.empty:
            ax.errorbar(rl['packet_probability'], rl['packet_delivery_ratio_mean'],
                        yerr=rl['packet_delivery_ratio_std'], marker='s',
                        label=f'RL (ε={eps})', capsize=3)

    ax.set_xlabel('Packet Generation Probability')
    ax.set_ylabel('Packet Delivery Ratio')
    ax.set_title(f'PDR vs Packet Probability (N={n_nodes})')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Packet loss plot
    ax = axes[1]
    ax.errorbar(baseline['packet_probability'], baseline['packet_loss_ratio_mean'],
                yerr=baseline['packet_loss_ratio_std'], marker='o',
                label='Baseline CSMA/CA', capsize=3)

    for eps in sorted(subset['epsilon'].unique()):
        rl = subset[(subset['node_type'] == 'rl') & (subset['epsilon'] == eps)]
        if not rl.empty:
            ax.errorbar(rl['packet_probability'], rl['packet_loss_ratio_mean'],
                        yerr=rl['packet_loss_ratio_std'], marker='s',
                        label=f'RL (ε={eps})', capsize=3)

    ax.set_xlabel('Packet Generation Probability')
    ax.set_ylabel('Packet Loss Ratio')
    ax.set_title(f'Packet Loss vs Probability (N={n_nodes})')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'metrics_vs_probability.png'), dpi=150)
    plt.close()
    print(f"Saved: metrics_vs_probability.png")


def plot_epsilon_impact(df: pd.DataFrame, output_dir: str):
    """Analyze impact of exploration rate (epsilon) on RL performance"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    rl_data = df[df['node_type'] == 'rl']
    agg = aggregate_results(rl_data)

    metrics = [
        ('packet_delivery_ratio_mean', 'Packet Delivery Ratio', axes[0, 0]),
        ('throughput_mean', 'Throughput', axes[0, 1]),
        ('packet_loss_ratio_mean', 'Packet Loss Ratio', axes[1, 0]),
        ('total_timeouts_mean', 'Total Timeouts', axes[1, 1])
    ]

    for metric, label, ax in metrics:
        for n_nodes in sorted(agg['n_nodes'].unique()):
            subset = agg[agg['n_nodes'] == n_nodes]
            # Average across packet probabilities
            eps_data = subset.groupby('epsilon')[metric].mean()
            ax.plot(eps_data.index, eps_data.values, marker='o', label=f'N={n_nodes}')

        ax.set_xlabel('Epsilon (Exploration Rate)')
        ax.set_ylabel(label)
        ax.set_title(f'{label} vs Epsilon')
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'epsilon_impact.png'), dpi=150)
    plt.close()
    print(f"Saved: epsilon_impact.png")


def plot_heatmap_comparison(df: pd.DataFrame, output_dir: str):
    """Create heatmaps comparing baseline vs best RL configuration"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    agg = aggregate_results(df)

    # Find best epsilon for each configuration
    rl_data = agg[agg['node_type'] == 'rl']
    baseline_data = agg[agg['node_type'] == 'baseline']

    # Baseline PDR heatmap
    baseline_pivot = baseline_data.pivot_table(
        values='packet_delivery_ratio_mean',
        index='n_nodes',
        columns='packet_probability'
    )
    sns.heatmap(baseline_pivot, annot=True, fmt='.3f', cmap='YlGnBu', ax=axes[0])
    axes[0].set_title('Baseline CSMA/CA - PDR')

    # Best RL PDR heatmap (best epsilon per config)
    best_rl = rl_data.loc[rl_data.groupby(['n_nodes', 'packet_probability'])['packet_delivery_ratio_mean'].idxmax()]
    best_rl_pivot = best_rl.pivot_table(
        values='packet_delivery_ratio_mean',
        index='n_nodes',
        columns='packet_probability'
    )
    sns.heatmap(best_rl_pivot, annot=True, fmt='.3f', cmap='YlGnBu', ax=axes[1])
    axes[1].set_title('Best RL Configuration - PDR')

    # Improvement heatmap
    if baseline_pivot.shape == best_rl_pivot.shape:
        improvement = (best_rl_pivot - baseline_pivot) / baseline_pivot * 100
        sns.heatmap(improvement, annot=True, fmt='.1f', cmap='RdYlGn', center=0, ax=axes[2])
        axes[2].set_title('RL Improvement over Baseline (%)')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'heatmap_comparison.png'), dpi=150)
    plt.close()
    print(f"Saved: heatmap_comparison.png")


def generate_report(df: pd.DataFrame, output_dir: str):
    """Generate a text report with key findings"""
    agg = aggregate_results(df)

    report_path = os.path.join(output_dir, 'analysis_report.txt')
    with open(report_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("CSMA/CA SIMULATION ANALYSIS REPORT\n")
        f.write("=" * 70 + "\n\n")

        # Overall statistics
        f.write("1. OVERALL STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total simulations: {len(df)}\n")
        f.write(f"Node counts tested: {sorted(df['n_nodes'].unique())}\n")
        f.write(f"Packet probabilities: {sorted(df['packet_probability'].unique())}\n")
        f.write(f"Epsilon values: {sorted(df['epsilon'].unique())}\n\n")

        # Baseline vs RL comparison
        f.write("2. BASELINE VS RL COMPARISON\n")
        f.write("-" * 40 + "\n")

        baseline = df[df['node_type'] == 'baseline']
        rl = df[df['node_type'] == 'rl']

        f.write(f"Baseline avg PDR: {baseline['packet_delivery_ratio'].mean():.4f}\n")
        f.write(f"RL avg PDR: {rl['packet_delivery_ratio'].mean():.4f}\n")
        f.write(f"Baseline avg throughput: {baseline['throughput'].mean():.6f}\n")
        f.write(f"RL avg throughput: {rl['throughput'].mean():.6f}\n\n")

        # Best configurations
        f.write("3. BEST CONFIGURATIONS\n")
        f.write("-" * 40 + "\n")

        best_baseline = baseline.loc[baseline['packet_delivery_ratio'].idxmax()]
        f.write(f"Best Baseline PDR: {best_baseline['packet_delivery_ratio']:.4f}\n")
        f.write(f"  Config: N={best_baseline['n_nodes']}, prob={best_baseline['packet_probability']}\n\n")

        best_rl = rl.loc[rl['packet_delivery_ratio'].idxmax()]
        f.write(f"Best RL PDR: {best_rl['packet_delivery_ratio']:.4f}\n")
        f.write(f"  Config: N={best_rl['n_nodes']}, prob={best_rl['packet_probability']}, eps={best_rl['epsilon']}\n\n")

        # Epsilon analysis
        f.write("4. EPSILON IMPACT ANALYSIS\n")
        f.write("-" * 40 + "\n")
        eps_analysis = rl.groupby('epsilon')['packet_delivery_ratio'].mean()
        for eps, pdr in eps_analysis.items():
            f.write(f"  ε={eps}: avg PDR = {pdr:.4f}\n")

        best_eps = eps_analysis.idxmax()
        f.write(f"\nBest epsilon: {best_eps} (PDR = {eps_analysis[best_eps]:.4f})\n")

    print(f"Saved: analysis_report.txt")


def analyze_results(results_dir: str):
    """Main analysis function - generates all plots and reports"""
    df = load_results(results_dir)

    print(f"\nLoaded {len(df)} simulation results")
    print(f"Node types: {df['node_type'].unique()}")
    print(f"Node counts: {sorted(df['n_nodes'].unique())}")

    os.makedirs(results_dir, exist_ok=True)

    # Generate all visualizations
    plot_pdr_vs_nodes(df, results_dir)
    plot_pdr_vs_probability(df, results_dir)
    plot_epsilon_impact(df, results_dir)
    plot_heatmap_comparison(df, results_dir)
    generate_report(df, results_dir)

    print(f"\nAll analysis outputs saved to: {results_dir}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        results_dir = "results_full_experiment_2"

    analyze_results(results_dir)