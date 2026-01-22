#!/usr/bin/env python3

import os
import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

COLORS = {
    'baseline': '#2E86AB',
    'karmed': '#A23B72',
    'qlearning': '#F18F01',
}

CHART_CONFIG = {
    'font_family': 'Arial, sans-serif',
    'title_font_size': 18,
    'axis_font_size': 12,
    'legend_font_size': 11,
    'line_width': 2,
}


# =============================================================================
# HELPERS
# =============================================================================

def load_scenario_data(folder_path: str) -> dict[str, pd.DataFrame]:
    """Load all CSV files from a scenario folder."""
    csv_files = {}
    folder = Path(folder_path)

    if not folder.exists():
        print(f"  ✗ Folder '{folder_path}' does not exist.")
        return {}

    for file_path in sorted(folder.glob("*.csv")):
        try:
            df = pd.read_csv(file_path)
            name = file_path.stem
            csv_files[name] = df
            print(f"    ✓ {file_path.name} ({len(df):,} rows)")
        except Exception as e:
            print(f"    ✗ Error loading {file_path.name}: {e}")

    return csv_files


def get_protocol_display_name(name: str) -> str:
    """Get clean display name for a protocol."""
    name_lower = name.lower()
    if 'baseline' in name_lower or 'static' in name_lower:
        return 'Baseline'
    elif 'karmed' in name_lower or 'bandit' in name_lower or 'mab' in name_lower:
        return 'MAB'
    elif 'qlearning' in name_lower or 'q_learning' in name_lower or 'q-learning' in name_lower:
        return 'Q-Learning'
    return name


def get_protocol_color(name: str) -> str:
    """Get color for a protocol."""
    name_lower = name.lower()
    if 'baseline' in name_lower or 'static' in name_lower:
        return COLORS['baseline']
    elif 'karmed' in name_lower or 'bandit' in name_lower or 'mab' in name_lower:
        return COLORS['karmed']
    elif 'qlearning' in name_lower or 'q_learning' in name_lower or 'q-learning' in name_lower:
        return COLORS['qlearning']
    return '#333333'


def get_final_value(df: pd.DataFrame, metric: str) -> float:
    """Get the final value of a metric from a dataframe."""
    if metric in df.columns:
        return df[metric].iloc[-1]
    return 0


def format_value(v: float) -> str:
    """Smart formatting based on value magnitude."""
    if abs(v) >= 1e9:
        return f'{v / 1e9:.2f}B'
    elif abs(v) >= 1e6:
        return f'{v / 1e6:.2f}M'
    elif abs(v) >= 1e3:
        return f'{v / 1e3:.1f}K'
    elif abs(v) >= 1:
        return f'{v:.2f}'
    else:
        return f'{v:.3f}'


# =============================================================================
# CHART GENERATORS
# =============================================================================

def create_throughput_comparison(all_data: dict[str, dict[str, pd.DataFrame]]) -> go.Figure:
    """Create throughput comparison across all scenarios."""

    fig = go.Figure()

    scenarios = list(all_data.keys())
    protocols = ['baseline', 'karmed', 'qlearning']
    protocol_names = ['Baseline', 'MAB', 'Q-Learning']

    for protocol, protocol_name in zip(protocols, protocol_names):
        values = []
        for scenario in scenarios:
            scenario_data = all_data[scenario]
            for name, df in scenario_data.items():
                if protocol in name.lower() or (protocol == 'karmed' and 'bandit' in name.lower()):
                    values.append(get_final_value(df, 'channel_total_throughput'))
                    break
            else:
                values.append(0)

        fig.add_trace(go.Bar(
            name=protocol_name,
            x=scenarios,
            y=values,
            marker_color=COLORS.get(protocol, '#333'),
            text=[format_value(v) for v in values],
            textposition='outside'
        ))

    fig.update_layout(
        title=dict(text='<b>Total Throughput Comparison</b>', font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        xaxis_title='Scenario',
        yaxis_title='Total Throughput (bits)',
        barmode='group',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=500,
        width=900,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=80, b=60, l=80, r=40)
    )

    return fig


def create_packet_loss_comparison(all_data: dict[str, dict[str, pd.DataFrame]]) -> go.Figure:
    """Create packet loss comparison across all scenarios."""

    fig = go.Figure()

    scenarios = list(all_data.keys())
    protocols = ['baseline', 'karmed', 'qlearning']
    protocol_names = ['Baseline', 'MAB', 'Q-Learning']

    for protocol, protocol_name in zip(protocols, protocol_names):
        values = []
        for scenario in scenarios:
            scenario_data = all_data[scenario]
            for name, df in scenario_data.items():
                if protocol in name.lower() or (protocol == 'karmed' and 'bandit' in name.lower()):
                    values.append(get_final_value(df, 'channel_avg_packet_loss_percentage'))
                    break
            else:
                values.append(0)

        fig.add_trace(go.Bar(
            name=protocol_name,
            x=scenarios,
            y=values,
            marker_color=COLORS.get(protocol, '#333'),
            text=[f'{v:.2f}%' for v in values],
            textposition='outside'
        ))

    fig.update_layout(
        title=dict(text='<b>Packet Loss Comparison</b>', font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        xaxis_title='Scenario',
        yaxis_title='Packet Loss (%)',
        barmode='group',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=500,
        width=900,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=80, b=60, l=80, r=40)
    )

    return fig


def create_timeout_comparison(all_data: dict[str, dict[str, pd.DataFrame]]) -> go.Figure:
    """Create timeout comparison across all scenarios."""

    fig = go.Figure()

    scenarios = list(all_data.keys())
    protocols = ['baseline', 'karmed', 'qlearning']
    protocol_names = ['Baseline', 'MAB', 'Q-Learning']

    for protocol, protocol_name in zip(protocols, protocol_names):
        values = []
        for scenario in scenarios:
            scenario_data = all_data[scenario]
            for name, df in scenario_data.items():
                if protocol in name.lower() or (protocol == 'karmed' and 'bandit' in name.lower()):
                    values.append(get_final_value(df, 'nodes_avg_timeout_retry'))
                    break
            else:
                values.append(0)

        fig.add_trace(go.Bar(
            name=protocol_name,
            x=scenarios,
            y=values,
            marker_color=COLORS.get(protocol, '#333'),
            text=[format_value(v) for v in values],
            textposition='outside'
        ))

    fig.update_layout(
        title=dict(text='<b>Average Timeouts per Node</b>', font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        xaxis_title='Scenario',
        yaxis_title='Avg Timeouts/Node',
        barmode='group',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=500,
        width=900,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=80, b=60, l=80, r=40)
    )

    return fig


def create_data_packets_comparison(all_data: dict[str, dict[str, pd.DataFrame]]) -> go.Figure:
    """Create data packets sent comparison across all scenarios."""

    fig = go.Figure()

    scenarios = list(all_data.keys())
    protocols = ['baseline', 'karmed', 'qlearning']
    protocol_names = ['Baseline', 'MAB', 'Q-Learning']

    for protocol, protocol_name in zip(protocols, protocol_names):
        values = []
        for scenario in scenarios:
            scenario_data = all_data[scenario]
            for name, df in scenario_data.items():
                if protocol in name.lower() or (protocol == 'karmed' and 'bandit' in name.lower()):
                    values.append(get_final_value(df, 'channel_total_data_packet_sent'))
                    break
            else:
                values.append(0)

        fig.add_trace(go.Bar(
            name=protocol_name,
            x=scenarios,
            y=values,
            marker_color=COLORS.get(protocol, '#333'),
            text=[format_value(v) for v in values],
            textposition='outside'
        ))

    fig.update_layout(
        title=dict(text='<b>Data Packets Successfully Sent</b>', font=dict(size=CHART_CONFIG['title_font_size']),
                   x=0.5),
        xaxis_title='Scenario',
        yaxis_title='Data Packets Sent',
        barmode='group',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=500,
        width=900,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=80, b=60, l=80, r=40)
    )

    return fig


def create_improvement_comparison(all_data: dict[str, dict[str, pd.DataFrame]]) -> go.Figure:
    """Create relative improvement comparison (vs baseline) across all scenarios."""

    fig = go.Figure()

    scenarios = list(all_data.keys())
    protocols = ['karmed', 'qlearning']
    protocol_names = ['MAB', 'Q-Learning']
    metrics = ['Throughput', 'Packet Loss Red.', 'Timeout Red.']

    # Calculate improvements for each scenario and protocol
    improvements = {scenario: {} for scenario in scenarios}

    for scenario in scenarios:
        scenario_data = all_data[scenario]

        # Find baseline values
        baseline_throughput = 0
        baseline_loss = 0
        baseline_timeout = 0

        for name, df in scenario_data.items():
            if 'baseline' in name.lower() or 'static' in name.lower():
                baseline_throughput = get_final_value(df, 'channel_total_throughput')
                baseline_loss = get_final_value(df, 'channel_avg_packet_loss_percentage')
                baseline_timeout = get_final_value(df, 'nodes_avg_timeout_retry')
                break

        for protocol in protocols:
            for name, df in scenario_data.items():
                if protocol in name.lower() or (protocol == 'karmed' and 'bandit' in name.lower()):
                    current_throughput = get_final_value(df, 'channel_total_throughput')
                    current_loss = get_final_value(df, 'channel_avg_packet_loss_percentage')
                    current_timeout = get_final_value(df, 'nodes_avg_timeout_retry')

                    throughput_impr = ((
                                                   current_throughput - baseline_throughput) / baseline_throughput * 100) if baseline_throughput else 0
                    loss_reduction = ((baseline_loss - current_loss) / baseline_loss * 100) if baseline_loss else 0
                    timeout_reduction = ((
                                                     baseline_timeout - current_timeout) / baseline_timeout * 100) if baseline_timeout else 0

                    improvements[scenario][protocol] = {
                        'throughput': throughput_impr,
                        'loss': loss_reduction,
                        'timeout': timeout_reduction
                    }
                    break

    # Create grouped bar chart
    x_labels = []
    for scenario in scenarios:
        for metric in metrics:
            x_labels.append(f'{scenario}<br>{metric}')

    for protocol, protocol_name in zip(protocols, protocol_names):
        values = []
        for scenario in scenarios:
            if protocol in improvements[scenario]:
                values.append(improvements[scenario][protocol]['throughput'])
                values.append(improvements[scenario][protocol]['loss'])
                values.append(improvements[scenario][protocol]['timeout'])
            else:
                values.extend([0, 0, 0])

        fig.add_trace(go.Bar(
            name=protocol_name,
            x=x_labels,
            y=values,
            marker_color=COLORS.get(protocol, '#333'),
            text=[f'{v:.1f}%' for v in values],
            textposition='outside'
        ))

    fig.update_layout(
        title=dict(text='<b>Relative Improvement vs Baseline (%)</b>', font=dict(size=CHART_CONFIG['title_font_size']),
                   x=0.5),
        xaxis_title='',
        yaxis_title='Improvement (%)',
        barmode='group',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=550,
        width=1100,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=80, b=80, l=80, r=40)
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    return fig


def create_summary_dashboard(all_data: dict[str, dict[str, pd.DataFrame]]) -> go.Figure:
    """Create a comprehensive summary dashboard."""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Total Throughput',
            'Packet Loss (%)',
            'Data Packets Sent',
            'Avg Timeouts/Node'
        ],
        horizontal_spacing=0.12,
        vertical_spacing=0.15
    )

    scenarios = list(all_data.keys())
    protocols = ['baseline', 'karmed', 'qlearning']
    protocol_names = ['Baseline', 'MAB', 'Q-Learning']

    metrics = [
        ('channel_total_throughput', 1, 1),
        ('channel_avg_packet_loss_percentage', 1, 2),
        ('channel_total_data_packet_sent', 2, 1),
        ('nodes_avg_timeout_retry', 2, 2)
    ]

    for metric, row, col in metrics:
        for protocol, protocol_name in zip(protocols, protocol_names):
            values = []
            for scenario in scenarios:
                scenario_data = all_data[scenario]
                for name, df in scenario_data.items():
                    if protocol in name.lower() or (protocol == 'karmed' and 'bandit' in name.lower()):
                        values.append(get_final_value(df, metric))
                        break
                else:
                    values.append(0)

            show_legend = (row == 1 and col == 1)

            fig.add_trace(
                go.Bar(
                    name=protocol_name,
                    x=scenarios,
                    y=values,
                    marker_color=COLORS.get(protocol, '#333'),
                    text=[format_value(v) for v in values],
                    textposition='outside',
                    showlegend=show_legend,
                    legendgroup=protocol_name
                ),
                row=row, col=col
            )

    fig.update_layout(
        title=dict(text='<b>Cross-Scenario Performance Summary</b>', font=dict(size=CHART_CONFIG['title_font_size']),
                   x=0.5),
        barmode='group',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=700,
        width=1100,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=100, b=60, l=60, r=40)
    )

    return fig


def create_throughput_rate_comparison(all_data: dict[str, dict[str, pd.DataFrame]]) -> go.Figure:
    """Create throughput rate comparison across all scenarios."""

    fig = make_subplots(
        rows=1, cols=len(all_data),
        subplot_titles=list(all_data.keys()),
        horizontal_spacing=0.08
    )

    scenarios = list(all_data.keys())
    protocols = ['baseline', 'karmed', 'qlearning']
    protocol_names = ['Baseline', 'MAB', 'Q-Learning']

    for col_idx, scenario in enumerate(scenarios, 1):
        scenario_data = all_data[scenario]

        for protocol, protocol_name in zip(protocols, protocol_names):
            for name, df in scenario_data.items():
                if protocol in name.lower() or (protocol == 'karmed' and 'bandit' in name.lower()):
                    if 'channel_total_throughput' in df.columns and 'tick' in df.columns and len(df) > 1:
                        # Calculate throughput rate
                        throughput_rate = df['channel_total_throughput'].diff() / df['tick'].diff()
                        throughput_rate_smooth = throughput_rate.rolling(window=50, min_periods=1).mean()

                        fig.add_trace(
                            go.Scatter(
                                x=df['tick'],
                                y=throughput_rate_smooth,
                                mode='lines',
                                name=protocol_name,
                                line=dict(color=COLORS.get(protocol, '#333'), width=2),
                                showlegend=(col_idx == 1),
                                legendgroup=protocol_name
                            ),
                            row=1, col=col_idx
                        )
                    break

        fig.update_xaxes(title_text='Tick', row=1, col=col_idx, tickformat=',.0f')
        fig.update_yaxes(title_text='Bits/Tick' if col_idx == 1 else '', row=1, col=col_idx)

    fig.update_layout(
        title=dict(text='<b>Throughput Rate Comparison (bits/tick)</b>',
                   font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=400,
        width=1200,
        legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5),
        margin=dict(t=100, b=60, l=60, r=40)
    )

    return fig

def create_summary_table(all_data: dict[str, dict[str, pd.DataFrame]]) -> go.Figure:
    """Create a summary table with all metrics."""

    scenarios = list(all_data.keys())

    metrics = [
        ('channel_total_throughput', 'Total Throughput'),
        ('channel_avg_packet_loss_percentage', 'Packet Loss %'),
        ('channel_total_data_packet_sent', 'Data Packets Sent'),
        ('nodes_avg_timeout_retry', 'Avg Timeouts/Node'),
        ('channel_total_loss_packets', 'Packets Lost'),
    ]

    # Build header
    header_vals = ['Metric']
    for scenario in scenarios:
        header_vals.extend([f'{scenario}<br>Baseline', f'{scenario}<br>MAB', f'{scenario}<br>Q-Learn'])

    # Build rows
    cell_vals = [[] for _ in range(len(header_vals))]

    for metric_col, metric_name in metrics:
        cell_vals[0].append(metric_name)
        col_idx = 1

        for scenario in scenarios:
            scenario_data = all_data[scenario]

            for protocol in ['baseline', 'karmed', 'qlearning']:
                value = 0
                for name, df in scenario_data.items():
                    if protocol in name.lower() or (protocol == 'karmed' and 'bandit' in name.lower()):
                        value = get_final_value(df, metric_col)
                        break

                cell_vals[col_idx].append(format_value(value))
                col_idx += 1

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f'<b>{h}</b>' for h in header_vals],
            fill_color='rgb(46, 134, 171)',
            font=dict(color='white', size=11),
            align='center',
            height=40
        ),
        cells=dict(
            values=cell_vals,
            fill_color=[['white', 'rgb(240,240,240)'] * (len(metrics) // 2 + 1)],
            align=['left'] + ['center'] * (len(header_vals) - 1),
            font=dict(size=10),
            height=30
        )
    )])

    fig.update_layout(
        title=dict(text='<b>Complete Results Summary</b>', font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        height=350,
        width=1200,
        margin=dict(t=60, b=20, l=20, r=20)
    )

    return fig


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 4:
        print("Usage: python cross_scenario_comparison.py <folder1> <folder2> <folder3> [output_folder]")
        print("Example: python cross_scenario_comparison.py ./hom100 ./hom500 ./clustered ./comparison")
        sys.exit(1)

    folders = sys.argv[1:4]
    output_folder = sys.argv[4] if len(sys.argv) > 4 else "./cross_comparison_output"

    os.makedirs(output_folder, exist_ok=True)

    print()
    print("=" * 70)
    print("  Cross-Scenario Comparison Chart Generator")
    print("=" * 70)
    print(f"  Scenarios: {', '.join(folders)}")
    print(f"  Output: {output_folder}")
    print("=" * 70)
    print()

    # Load all data
    all_data = {}
    for folder in folders:
        scenario_name = Path(folder).name
        print(f"Loading {scenario_name}...")
        data = load_scenario_data(folder)
        if data:
            all_data[scenario_name] = data
        print()

    if len(all_data) < 2:
        print("Error: Need at least 2 scenarios with valid data.")
        sys.exit(1)

    print("Generating comparison charts...")
    print("-" * 50)

    charts = []

    # 1. Summary dashboard
    print("  → Summary dashboard...")
    fig = create_summary_dashboard(all_data)
    path = os.path.join(output_folder, "01_summary_dashboard.html")
    fig.write_html(path)
    charts.append(path)

    # 2. Summary table
    print("  → Summary table...")
    fig = create_summary_table(all_data)
    path = os.path.join(output_folder, "02_summary_table.html")
    fig.write_html(path)
    charts.append(path)

    # 3. Throughput comparison
    print("  → Throughput comparison...")
    fig = create_throughput_comparison(all_data)
    path = os.path.join(output_folder, "03_throughput_comparison.html")
    fig.write_html(path)
    charts.append(path)

    # 4. Packet loss comparison
    print("  → Packet loss comparison...")
    fig = create_packet_loss_comparison(all_data)
    path = os.path.join(output_folder, "04_packet_loss_comparison.html")
    fig.write_html(path)
    charts.append(path)

    # 5. Timeout comparison
    print("  → Timeout comparison...")
    fig = create_timeout_comparison(all_data)
    path = os.path.join(output_folder, "05_timeout_comparison.html")
    fig.write_html(path)
    charts.append(path)

    # 6. Data packets comparison
    print("  → Data packets comparison...")
    fig = create_data_packets_comparison(all_data)
    path = os.path.join(output_folder, "06_data_packets_comparison.html")
    fig.write_html(path)
    charts.append(path)

    # 7. Relative improvement comparison
    print("  → Improvement comparison...")
    fig = create_improvement_comparison(all_data)
    path = os.path.join(output_folder, "07_improvement_comparison.html")
    fig.write_html(path)
    charts.append(path)

    print("  → Throughput rate comparison...")
    fig = create_throughput_rate_comparison(all_data)
    path = os.path.join(output_folder, "08_throughput_rate_comparison.html")
    fig.write_html(path)
    charts.append(path)

    print("-" * 50)
    print()
    print("=" * 70)
    print("  Generation complete!")
    print("=" * 70)
    print(f"\n  Generated {len(charts)} charts:")
    for path in charts:
        print(f"    • {os.path.basename(path)}")
    print(f"\n  Open HTML files in browser to view.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()