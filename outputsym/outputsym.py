#!/usr/bin/env python3

import os
import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

# Color scheme - professional and colorblind-friendly
COLORS = {
    'baseline': '#2E86AB',  # Blue
    'karmed': '#A23B72',  # Magenta/Purple
    'qlearning': '#F18F01',  # Orange
}

# Fallback colors for unknown protocols
FALLBACK_COLORS = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B']

# Chart styling
CHART_CONFIG = {
    'font_family': 'Arial, sans-serif',
    'title_font_size': 18,
    'axis_font_size': 12,
    'legend_font_size': 11,
    'line_width': 2,
    'grid_color': 'rgba(128, 128, 128, 0.2)',
    'background_color': 'white',
    'plot_bg_color': 'rgba(250, 250, 250, 1)',
}


# =============================================================================
# DATA LOADING
# =============================================================================

def load_csv_files(folder_path: str) -> dict[str, pd.DataFrame]:
    """Load all CSV files from the specified folder."""
    csv_files = {}
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist.")
        sys.exit(1)

    for file_path in sorted(folder.glob("*.csv")):
        try:
            df = pd.read_csv(file_path)
            name = file_path.stem
            csv_files[name] = df
            print(f"  ✓ Loaded: {file_path.name} ({len(df):,} rows)")
        except Exception as e:
            print(f"  ✗ Error loading {file_path.name}: {e}")

    if not csv_files:
        print(f"No CSV files found in '{folder_path}'")
        sys.exit(1)

    return csv_files


def get_protocol_color(name: str, idx: int = 0) -> str:
    """Get color for a protocol based on its name."""
    name_lower = name.lower()

    if 'baseline' in name_lower or 'static' in name_lower:
        return COLORS['baseline']
    elif 'karmed' in name_lower or 'bandit' in name_lower or 'mab' in name_lower:
        return COLORS['karmed']
    elif 'qlearning' in name_lower or 'q_learning' in name_lower or 'q-learning' in name_lower:
        return COLORS['qlearning']
    else:
        return FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]


def get_protocol_display_name(name: str) -> str:
    """Get a clean display name for a protocol."""
    name_lower = name.lower()

    if 'baseline' in name_lower or 'static' in name_lower:
        return 'Baseline (Static CSMA/CA)'
    elif 'karmed' in name_lower or 'bandit' in name_lower or 'mab' in name_lower:
        return 'Multi-Armed Bandit'
    elif 'qlearning' in name_lower or 'q_learning' in name_lower or 'q-learning' in name_lower:
        return 'Q-Learning'
    else:
        return name.replace('_', ' ').title()


# =============================================================================
# CHART GENERATORS
# =============================================================================

def create_time_series_chart(
        data: dict[str, pd.DataFrame],
        metric: str,
        title: str,
        ylabel: str,
        log_scale: bool = False,
        show_moving_avg: bool = True,
        moving_avg_window: int = 100
) -> go.Figure:
    """Create a time series line chart comparing all protocols."""

    fig = go.Figure()

    for idx, (name, df) in enumerate(data.items()):
        if metric not in df.columns or 'tick' not in df.columns:
            continue

        color = get_protocol_color(name, idx)
        display_name = get_protocol_display_name(name)

        # Main line
        fig.add_trace(go.Scatter(
            x=df['tick'],
            y=df[metric],
            mode='lines',
            name=display_name,
            line=dict(color=color, width=CHART_CONFIG['line_width']),
            opacity=0.7 if show_moving_avg else 1.0,
            hovertemplate=f'<b>{display_name}</b><br>Tick: %{{x:,.0f}}<br>{ylabel}: %{{y:.4f}}<extra></extra>'
        ))

        # Moving average overlay
        if show_moving_avg and len(df) > moving_avg_window:
            ma = df[metric].rolling(window=moving_avg_window, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=df['tick'],
                y=ma,
                mode='lines',
                name=f'{display_name} (MA)',
                line=dict(color=color, width=CHART_CONFIG['line_width'] + 1, dash='solid'),
                showlegend=False,
                hoverinfo='skip'
            ))

    fig.update_layout(
        title=dict(text=f'<b>{title}</b>', font=dict(size=CHART_CONFIG['title_font_size'])),
        xaxis_title='Simulation Tick',
        yaxis_title=ylabel,
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(size=CHART_CONFIG['legend_font_size'])
        ),
        hovermode='x unified',
        template='plotly_white',
        plot_bgcolor=CHART_CONFIG['plot_bg_color'],
        xaxis=dict(showgrid=True, gridcolor=CHART_CONFIG['grid_color'], tickformat=',.0f'),
        yaxis=dict(
            showgrid=True,
            gridcolor=CHART_CONFIG['grid_color'],
            type='log' if log_scale else 'linear'
        ),
        height=500,
        width=1000,
        margin=dict(t=80, b=60, l=80, r=40)
    )

    return fig


def create_final_comparison_bar(
        data: dict[str, pd.DataFrame],
        metrics: list[tuple[str, str, str]],  # (column, title, format)
        title: str
) -> go.Figure:
    """Create a grouped bar chart comparing final values."""

    # Extract final values
    final_values = {}
    for name, df in data.items():
        display_name = get_protocol_display_name(name)
        final_values[display_name] = {}
        for col, label, fmt in metrics:
            if col in df.columns:
                final_values[display_name][label] = df[col].iloc[-1]

    # Create subplots for each metric
    n_metrics = len(metrics)
    fig = make_subplots(
        rows=1, cols=n_metrics,
        subplot_titles=[m[1] for m in metrics],
        horizontal_spacing=0.08
    )

    protocols = list(final_values.keys())

    for idx, (col, label, fmt) in enumerate(metrics):
        values = [final_values[p].get(label, 0) for p in protocols]
        colors = [get_protocol_color(name, i) for i, name in enumerate(data.keys())]

        fig.add_trace(
            go.Bar(
                x=protocols,
                y=values,
                marker_color=colors,
                text=[f'{v:{fmt}}' for v in values],
                textposition='outside',
                showlegend=False,
                hovertemplate='<b>%{x}</b><br>' + label + ': %{y:' + fmt + '}<extra></extra>'
            ),
            row=1, col=idx + 1
        )

        fig.update_yaxes(title_text=label, row=1, col=idx + 1)

    fig.update_layout(
        title=dict(text=f'<b>{title}</b>', font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=450,
        width=350 * n_metrics,
        margin=dict(t=100, b=60, l=60, r=40),
        showlegend=False
    )

    return fig


def create_multi_metric_dashboard(
        data: dict[str, pd.DataFrame],
        metrics: list[tuple[str, str, str, bool]],  # (column, title, ylabel, log_scale)
        dashboard_title: str
) -> go.Figure:
    """Create a dashboard with multiple metrics in subplots."""

    n_metrics = len(metrics)
    n_cols = 2
    n_rows = (n_metrics + 1) // 2

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[m[1] for m in metrics],
        horizontal_spacing=0.08,
        vertical_spacing=0.12
    )

    for idx, (col, title, ylabel, log_scale) in enumerate(metrics):
        row = idx // n_cols + 1
        col_idx = idx % n_cols + 1

        for i, (name, df) in enumerate(data.items()):
            if col not in df.columns or 'tick' not in df.columns:
                continue

            color = get_protocol_color(name, i)
            display_name = get_protocol_display_name(name)

            fig.add_trace(
                go.Scatter(
                    x=df['tick'],
                    y=df[col],
                    mode='lines',
                    name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name,
                    showlegend=(idx == 0),
                    hovertemplate=f'<b>{display_name}</b><br>Tick: %{{x:,.0f}}<br>{ylabel}: %{{y:.4f}}<extra></extra>'
                ),
                row=row, col=col_idx
            )

        fig.update_xaxes(
            title_text='Tick',
            row=row, col=col_idx,
            showgrid=True,
            gridcolor=CHART_CONFIG['grid_color'],
            tickformat=',.0f'
        )
        fig.update_yaxes(
            title_text=ylabel,
            row=row, col=col_idx,
            showgrid=True,
            gridcolor=CHART_CONFIG['grid_color'],
            type='log' if log_scale else 'linear'
        )

    fig.update_layout(
        title=dict(
            text=f'<b>{dashboard_title}</b>',
            font=dict(size=CHART_CONFIG['title_font_size']),
            x=0.5
        ),
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.12,
            xanchor='center',
            x=0.5,
            font=dict(size=CHART_CONFIG['legend_font_size'])
        ),
        template='plotly_white',
        height=400 * n_rows,
        width=1200,
        margin=dict(t=80, b=100, l=60, r=40),
        hovermode='x unified'
    )

    return fig


def create_throughput_improvement_chart(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create chart showing throughput improvement over baseline."""

    fig = go.Figure()

    # Find baseline
    baseline_name = None
    baseline_df = None
    for name, df in data.items():
        if 'baseline' in name.lower() or 'static' in name.lower():
            baseline_name = name
            baseline_df = df
            break

    if baseline_df is None:
        baseline_name = list(data.keys())[0]
        baseline_df = list(data.values())[0]

    for i, (name, df) in enumerate(data.items()):
        if name == baseline_name:
            continue

        color = get_protocol_color(name, i)
        display_name = get_protocol_display_name(name)

        if 'channel_total_throughput' in df.columns and 'channel_total_throughput' in baseline_df.columns:
            min_len = min(len(df), len(baseline_df))
            baseline_vals = baseline_df['channel_total_throughput'].iloc[:min_len].replace(0, np.nan)
            current_vals = df['channel_total_throughput'].iloc[:min_len]
            improvement = ((current_vals.values - baseline_vals.values) / baseline_vals.values) * 100

            fig.add_trace(
                go.Scatter(
                    x=df['tick'].iloc[:min_len], y=improvement,
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width'])
                )
            )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=dict(text='<b>Throughput Improvement vs Baseline (%)</b>',
                   font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        xaxis_title='Tick',
        yaxis_title='Improvement %',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=500,
        width=900,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        xaxis=dict(tickformat=',.0f'),
        margin=dict(t=80, b=60, l=60, r=40)
    )

    return fig


def create_packet_loss_reduction_chart(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create chart showing packet loss reduction over baseline."""

    fig = go.Figure()

    # Find baseline
    baseline_name = None
    baseline_df = None
    for name, df in data.items():
        if 'baseline' in name.lower() or 'static' in name.lower():
            baseline_name = name
            baseline_df = df
            break

    if baseline_df is None:
        baseline_name = list(data.keys())[0]
        baseline_df = list(data.values())[0]

    for i, (name, df) in enumerate(data.items()):
        if name == baseline_name:
            continue

        color = get_protocol_color(name, i)
        display_name = get_protocol_display_name(name)

        if 'channel_avg_packet_loss_percentage' in df.columns and 'channel_avg_packet_loss_percentage' in baseline_df.columns:
            min_len = min(len(df), len(baseline_df))
            baseline_vals = baseline_df['channel_avg_packet_loss_percentage'].iloc[:min_len].replace(0, np.nan)
            current_vals = df['channel_avg_packet_loss_percentage'].iloc[:min_len]
            reduction = ((baseline_vals.values - current_vals.values) / baseline_vals.values) * 100

            fig.add_trace(
                go.Scatter(
                    x=df['tick'].iloc[:min_len], y=reduction,
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width'])
                )
            )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=dict(text='<b>Packet Loss Reduction vs Baseline (%)</b>', font=dict(size=CHART_CONFIG['title_font_size']),
                   x=0.5),
        xaxis_title='Tick',
        yaxis_title='Reduction %',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=500,
        width=900,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        xaxis=dict(tickformat=',.0f'),
        margin=dict(t=80, b=60, l=60, r=40)
    )

    return fig


def create_timeout_reduction_chart(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create chart showing timeout reduction over baseline."""

    fig = go.Figure()

    # Find baseline
    baseline_name = None
    baseline_df = None
    for name, df in data.items():
        if 'baseline' in name.lower() or 'static' in name.lower():
            baseline_name = name
            baseline_df = df
            break

    if baseline_df is None:
        baseline_name = list(data.keys())[0]
        baseline_df = list(data.values())[0]

    for i, (name, df) in enumerate(data.items()):
        if name == baseline_name:
            continue

        color = get_protocol_color(name, i)
        display_name = get_protocol_display_name(name)

        if 'nodes_avg_timeout_retry' in df.columns and 'nodes_avg_timeout_retry' in baseline_df.columns:
            min_len = min(len(df), len(baseline_df))
            baseline_vals = baseline_df['nodes_avg_timeout_retry'].iloc[:min_len].replace(0, np.nan)
            current_vals = df['nodes_avg_timeout_retry'].iloc[:min_len]
            reduction = ((baseline_vals.values - current_vals.values) / baseline_vals.values) * 100

            fig.add_trace(
                go.Scatter(
                    x=df['tick'].iloc[:min_len], y=reduction,
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width'])
                )
            )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=dict(text='<b>Timeout Reduction vs Baseline (%)</b>', font=dict(size=CHART_CONFIG['title_font_size']),
                   x=0.5),
        xaxis_title='Tick',
        yaxis_title='Reduction %',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=500,
        width=900,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        xaxis=dict(tickformat=',.0f'),
        margin=dict(t=80, b=60, l=60, r=40)
    )

    return fig


def create_improvement_summary_chart(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create bar chart summarizing final improvements."""

    # Find baseline
    baseline_name = None
    baseline_df = None
    for name, df in data.items():
        if 'baseline' in name.lower() or 'static' in name.lower():
            baseline_name = name
            baseline_df = df
            break

    if baseline_df is None:
        baseline_name = list(data.keys())[0]
        baseline_df = list(data.values())[0]

    final_improvements = {}

    for i, (name, df) in enumerate(data.items()):
        if name == baseline_name:
            continue

        display_name = get_protocol_display_name(name)
        final_improvements[display_name] = {'color': get_protocol_color(name, i)}

        # Throughput improvement
        if 'channel_total_throughput' in df.columns and 'channel_total_throughput' in baseline_df.columns:
            baseline_val = baseline_df['channel_total_throughput'].iloc[-1]
            current_val = df['channel_total_throughput'].iloc[-1]
            if baseline_val != 0:
                final_improvements[display_name]['throughput'] = ((current_val - baseline_val) / baseline_val) * 100

        # Packet loss reduction
        if 'channel_avg_packet_loss_percentage' in df.columns and 'channel_avg_packet_loss_percentage' in baseline_df.columns:
            baseline_val = baseline_df['channel_avg_packet_loss_percentage'].iloc[-1]
            current_val = df['channel_avg_packet_loss_percentage'].iloc[-1]
            if baseline_val != 0:
                final_improvements[display_name]['packet_loss'] = ((baseline_val - current_val) / baseline_val) * 100

        # Timeout reduction
        if 'nodes_avg_timeout_retry' in df.columns and 'nodes_avg_timeout_retry' in baseline_df.columns:
            baseline_val = baseline_df['nodes_avg_timeout_retry'].iloc[-1]
            current_val = df['nodes_avg_timeout_retry'].iloc[-1]
            if baseline_val != 0:
                final_improvements[display_name]['timeout'] = ((baseline_val - current_val) / baseline_val) * 100

    fig = go.Figure()

    metric_labels = ['Throughput +%', 'Packet Loss Reduction %', 'Timeout Reduction %']
    metrics = ['throughput', 'packet_loss', 'timeout']

    for protocol, values in final_improvements.items():
        metric_values = [values.get(m, 0) for m in metrics]
        fig.add_trace(
            go.Bar(
                x=metric_labels,
                y=metric_values,
                name=protocol,
                marker_color=values['color'],
                text=[f'{v:.1f}%' for v in metric_values],
                textposition='outside'
            )
        )

    fig.update_layout(
        title=dict(text='<b>Final Improvement Summary vs Baseline</b>', font=dict(size=CHART_CONFIG['title_font_size']),
                   x=0.5),
        xaxis_title='Metric',
        yaxis_title='Improvement %',
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=500,
        width=900,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        barmode='group',
        margin=dict(t=80, b=60, l=60, r=40)
    )

    return fig

def create_throughput_analysis(data: dict[str, pd.DataFrame], total_ticks: int = None) -> go.Figure:
    """Create detailed throughput analysis chart."""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Total Throughput Over Time',
            'Per-Node Average Throughput',
            'Throughput Rate (bits/tick)',
            'Final Throughput Comparison'
        ],
        specs=[[{"type": "scatter"}, {"type": "scatter"}],
               [{"type": "scatter"}, {"type": "bar"}]],
        horizontal_spacing=0.1,
        vertical_spacing=0.15
    )

    final_throughputs = {}

    for i, (name, df) in enumerate(data.items()):
        color = get_protocol_color(name, i)
        display_name = get_protocol_display_name(name)

        # Total throughput
        if 'channel_total_throughput' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['channel_total_throughput'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=True
                ),
                row=1, col=1
            )
            final_throughputs[display_name] = df['channel_total_throughput'].iloc[-1]

        # Per-node throughput
        if 'nodes_avg_throughput_per_node' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_throughput_per_node'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=1, col=2
            )

        # Throughput rate (derivative)
        if 'channel_total_throughput' in df.columns and len(df) > 1:
            throughput_rate = df['channel_total_throughput'].diff() / df['tick'].diff()
            # Smooth it
            throughput_rate_smooth = throughput_rate.rolling(window=50, min_periods=1).mean()
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=throughput_rate_smooth,
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=2, col=1
            )

    # Bar chart for final comparison
    protocols = list(final_throughputs.keys())
    values = list(final_throughputs.values())
    colors = [get_protocol_color(name, i) for i, name in enumerate(data.keys())]

    def format_value(v):
        if v >= 1e9:
            return f'{v / 1e9:.2f}B'
        elif v >= 1e6:
            return f'{v / 1e6:.2f}M'
        elif v >= 1e3:
            return f'{v / 1e3:.2f}K'
        else:
            return f'{v:.2f}'

    fig.add_trace(
        go.Bar(
            x=protocols, y=values,
            marker_color=colors,
            text=[format_value(v) for v in values],
            textposition='outside',
            showlegend=False
        ),
        row=2, col=2
    )

    # Update axes
    fig.update_xaxes(title_text='Tick', row=1, col=1, tickformat=',.0f')
    fig.update_xaxes(title_text='Tick', row=1, col=2, tickformat=',.0f')
    fig.update_xaxes(title_text='Tick', row=2, col=1, tickformat=',.0f')
    fig.update_xaxes(title_text='Protocol', row=2, col=2)

    fig.update_yaxes(title_text='Total Bits', row=1, col=1, type='log')
    fig.update_yaxes(title_text='Avg Bits/Node', row=1, col=2, type='log')
    fig.update_yaxes(title_text='Bits/Tick', row=2, col=1)
    fig.update_yaxes(title_text='Total Bits', row=2, col=2)

    fig.update_layout(
        title=dict(text='<b>Throughput Analysis</b>', font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=800,
        width=1200,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=100, b=60, l=60, r=40)
    )

    return fig


def create_packet_loss_analysis(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create detailed packet loss analysis."""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Packet Loss % Over Time',
            'Recent Packet Loss % (Rolling)',
            'Timeout Retries per Node',
            'Final Packet Loss Comparison'
        ],
        specs=[[{"type": "scatter"}, {"type": "scatter"}],
               [{"type": "scatter"}, {"type": "bar"}]],
        horizontal_spacing=0.1,
        vertical_spacing=0.15
    )

    final_loss = {}

    for i, (name, df) in enumerate(data.items()):
        color = get_protocol_color(name, i)
        display_name = get_protocol_display_name(name)

        # Packet loss %
        if 'channel_avg_packet_loss_percentage' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['channel_avg_packet_loss_percentage'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=True
                ),
                row=1, col=1
            )
            final_loss[display_name] = df['channel_avg_packet_loss_percentage'].iloc[-1]

        # Recent packet loss
        if 'nodes_avg_recent_packet_loss_pct' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_recent_packet_loss_pct'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=1, col=2
            )

        # Timeout retries
        if 'nodes_avg_timeout_retry' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_timeout_retry'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=2, col=1
            )

    # Bar chart
    protocols = list(final_loss.keys())
    values = list(final_loss.values())
    colors = [get_protocol_color(name, i) for i, name in enumerate(data.keys())]

    fig.add_trace(
        go.Bar(
            x=protocols, y=values,
            marker_color=colors,
            text=[f'{v:.2f}%' for v in values],
            textposition='outside',
            showlegend=False
        ),
        row=2, col=2
    )

    fig.update_layout(
        title=dict(text='<b>Packet Loss Analysis</b>', font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=800,
        width=1200,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=100, b=60, l=60, r=40)
    )

    return fig


def create_contention_analysis(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create contention window and collision analysis."""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'CW Entries Over Time',
            'CW Increases (Collisions)',
            'CW Increase Ratio',
            'Average NAV Duration'
        ],
        horizontal_spacing=0.1,
        vertical_spacing=0.15
    )

    for i, (name, df) in enumerate(data.items()):
        color = get_protocol_color(name, i)
        display_name = get_protocol_display_name(name)

        # CW enters
        if 'nodes_avg_cw_enters' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_cw_enters'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=True
                ),
                row=1, col=1
            )

        # CW increases
        if 'nodes_avg_cw_increase' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_cw_increase'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=1, col=2
            )

        # CW increase ratio
        if 'nodes_avg_cw_enters' in df.columns and 'nodes_avg_cw_increase' in df.columns:
            ratio = df['nodes_avg_cw_increase'] / df['nodes_avg_cw_enters'].replace(0, np.nan)
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=ratio,
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=2, col=1
            )

        # NAV duration
        if 'nodes_avg_nav_seconds' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_nav_seconds'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=2, col=2
            )

    fig.update_layout(
        title=dict(text='<b>Contention Window Analysis</b>', font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=800,
        width=1200,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=100, b=60, l=60, r=40)
    )

    return fig


def create_learning_metrics(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create charts for RL-specific metrics (epsilon, etc.)."""

    # Check if we have RL metrics
    has_rl_metrics = any(
        'nodes_avg_epsilon' in df.columns or 'nodes_avg_busy_ratio' in df.columns
        for df in data.values()
    )

    if not has_rl_metrics:
        return None

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Epsilon Decay (Exploration Rate)',
            'Channel Busy Ratio',
            'Collision Ratio (RL Estimation)',
            'Retry Count'
        ],
        horizontal_spacing=0.1,
        vertical_spacing=0.15
    )

    for i, (name, df) in enumerate(data.items()):
        color = get_protocol_color(name, i)
        display_name = get_protocol_display_name(name)

        # Epsilon
        if 'nodes_avg_epsilon' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_epsilon'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=True
                ),
                row=1, col=1
            )

        # Busy ratio
        if 'nodes_avg_busy_ratio' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_busy_ratio'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=1, col=2
            )

        # Collision ratio
        if 'nodes_avg_collision_ratio' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_collision_ratio'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=2, col=1
            )

        # Retry count
        if 'nodes_avg_current_retry_count' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['nodes_avg_current_retry_count'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=2, col=2
            )

    fig.update_layout(
        title=dict(text='<b>Reinforcement Learning Metrics</b>', font=dict(size=CHART_CONFIG['title_font_size']),
                   x=0.5),
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=800,
        width=1200,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        margin=dict(t=100, b=60, l=60, r=40)
    )

    return fig


def create_cluster_analysis(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create cluster-specific analysis for heterogeneous scenarios."""

    # Check if we have cluster metrics
    has_cluster_metrics = any('cluster_0_avg_throughput_per_node' in df.columns for df in data.values())

    if not has_cluster_metrics:
        return None

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Per-Cluster Throughput',
            'Per-Cluster Packet Loss %',
            'Jain Fairness Index',
            'Cluster Throughput Variance'
        ],
        horizontal_spacing=0.1,
        vertical_spacing=0.15
    )

    for i, (name, df) in enumerate(data.items()):
        color = get_protocol_color(name, i)
        display_name = get_protocol_display_name(name)

        # Per-cluster throughput (plot all 3 clusters)
        for cluster_id in range(3):
            col_name = f'cluster_{cluster_id}_avg_throughput_per_node'
            if col_name in df.columns:
                # Use different line styles for clusters
                dash_styles = ['solid', 'dash', 'dot']
                fig.add_trace(
                    go.Scatter(
                        x=df['tick'], y=df[col_name],
                        mode='lines', name=f'{display_name} - Cluster {cluster_id}',
                        line=dict(color=color, width=CHART_CONFIG['line_width'], dash=dash_styles[cluster_id]),
                        legendgroup=f'{name}_{cluster_id}', showlegend=True
                    ),
                    row=1, col=1
                )

        # Fairness index
        if 'jain_fairness_index' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['jain_fairness_index'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=2, col=1
            )

        # Throughput variance
        if 'cluster_throughput_variance' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['tick'], y=df['cluster_throughput_variance'],
                    mode='lines', name=display_name,
                    line=dict(color=color, width=CHART_CONFIG['line_width']),
                    legendgroup=name, showlegend=False
                ),
                row=2, col=2
            )

    fig.update_layout(
        title=dict(text='<b>Cluster Analysis (Heterogeneous Scenario)</b>',
                   font=dict(size=CHART_CONFIG['title_font_size']), x=0.5),
        font=dict(family=CHART_CONFIG['font_family'], size=CHART_CONFIG['axis_font_size']),
        template='plotly_white',
        height=800,
        width=1200,
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5,
            font=dict(size=9)
        ),
        margin=dict(t=100, b=120, l=60, r=40)
    )

    return fig


def create_summary_table(data: dict[str, pd.DataFrame]) -> go.Figure:
    """Create a summary table with final values."""

    metrics = [
        ('channel_total_throughput', 'Total Throughput', ',.0f'),
        ('channel_avg_packet_loss_percentage', 'Packet Loss %', '.2f'),
        ('nodes_avg_throughput_per_node', 'Avg Throughput/Node', ',.0f'),
        ('nodes_avg_timeout_retry', 'Avg Timeouts/Node', '.2f'),
        ('nodes_avg_cw_increase', 'Avg CW Increases/Node', '.2f'),
        ('channel_total_data_packet_sent', 'Data Packets Sent', ',.0f'),
        ('channel_total_loss_packets', 'Packets Lost', ',.0f'),
    ]

    # Build table data
    headers = ['Metric'] + [get_protocol_display_name(name) for name in data.keys()]
    rows = []

    for col, label, fmt in metrics:
        row = [label]
        for name, df in data.items():
            if col in df.columns:
                val = df[col].iloc[-1]
                row.append(f'{val:{fmt}}')
            else:
                row.append('N/A')
        rows.append(row)

    # Transpose for plotly table format
    cell_values = [[row[i] for row in rows] for i in range(len(headers))]

    # Determine best values for highlighting
    colors = []
    for i, (col, label, fmt) in enumerate(metrics):
        row_colors = ['white']  # Metric name column
        values = []
        for name, df in data.items():
            if col in df.columns:
                values.append(df[col].iloc[-1])
            else:
                values.append(None)

        # Determine if higher or lower is better
        lower_is_better = 'loss' in col.lower() or 'timeout' in col.lower() or 'increase' in col.lower()

        for v in values:
            if v is None:
                row_colors.append('white')
            elif lower_is_better:
                row_colors.append('lightgreen' if v == min(x for x in values if x is not None) else 'white')
            else:
                row_colors.append('lightgreen' if v == max(x for x in values if x is not None) else 'white')

        colors.append(row_colors)

    # Transpose colors
    fill_colors = [[colors[row][col] for row in range(len(metrics))] for col in range(len(headers))]

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f'<b>{h}</b>' for h in headers],
            fill_color='rgb(46, 134, 171)',
            font=dict(color='white', size=12),
            align='center',
            height=35
        ),
        cells=dict(
            values=cell_values,
            fill_color=fill_colors,
            align=['left'] + ['center'] * (len(headers) - 1),
            font=dict(size=11),
            height=30
        )
    )])

    fig.update_layout(
        title=dict(
            text='<b>Summary: Final Simulation Results</b><br><sup>Green = Best performance for metric</sup>',
            font=dict(size=CHART_CONFIG['title_font_size']),
            x=0.5
        ),
        font=dict(family=CHART_CONFIG['font_family']),
        height=400,
        width=900,
        margin=dict(t=80, b=20, l=20, r=20)
    )

    return fig


def create_complete_report(data: dict[str, pd.DataFrame], output_folder: str, scenario_name: str = ""):
    """Generate all charts and save to output folder."""

    prefix = f"{scenario_name}_" if scenario_name else ""

    charts = []

    # 1. Summary table
    print("  → Generating summary table...")
    fig = create_summary_table(data)
    path = os.path.join(output_folder, f"{prefix}01_summary_table.html")
    fig.write_html(path)
    charts.append(('Summary Table', path))

    # 2. Main dashboard
    print("  → Generating main dashboard...")
    metrics = [
        ('channel_avg_packet_loss_percentage', 'Packet Loss %', 'Loss %', False),
        ('channel_total_throughput', 'Total Throughput', 'Bits', False),
        ('nodes_avg_throughput_per_node', 'Avg Throughput per Node', 'Bits/Node', False),
        ('nodes_avg_timeout_retry', 'Timeout Retries', 'Count', False),
        ('nodes_avg_cw_increase', 'CW Increases', 'Count', False),
        ('nodes_avg_recent_packet_loss_pct', 'Recent Packet Loss %', 'Loss %', False),
    ]
    fig = create_multi_metric_dashboard(data, metrics, 'Protocol Comparison Dashboard')
    path = os.path.join(output_folder, f"{prefix}02_main_dashboard.html")
    fig.write_html(path)
    charts.append(('Main Dashboard', path))

    # 3. Throughput analysis
    print("  → Generating throughput analysis...")
    fig = create_throughput_analysis(data)
    path = os.path.join(output_folder, f"{prefix}03_throughput_analysis.html")
    fig.write_html(path)
    charts.append(('Throughput Analysis', path))

    # 4. Packet loss analysis
    print("  → Generating packet loss analysis...")
    fig = create_packet_loss_analysis(data)
    path = os.path.join(output_folder, f"{prefix}04_packet_loss_analysis.html")
    fig.write_html(path)
    charts.append(('Packet Loss Analysis', path))

    # 3b-3e Relative improvement charts (separate files)
    print("  → Generating relative improvement charts...")

    fig = create_throughput_improvement_chart(data)
    path = os.path.join(output_folder, f"{prefix}03b_throughput_improvement.html")
    fig.write_html(path)
    charts.append(('Throughput Improvement', path))

    fig = create_packet_loss_reduction_chart(data)
    path = os.path.join(output_folder, f"{prefix}03c_packet_loss_reduction.html")
    fig.write_html(path)
    charts.append(('Packet Loss Reduction', path))

    fig = create_timeout_reduction_chart(data)
    path = os.path.join(output_folder, f"{prefix}03d_timeout_reduction.html")
    fig.write_html(path)
    charts.append(('Timeout Reduction', path))

    fig = create_improvement_summary_chart(data)
    path = os.path.join(output_folder, f"{prefix}03e_improvement_summary.html")
    fig.write_html(path)
    charts.append(('Improvement Summary', path))

    # 5. Contention analysis
    print("  → Generating contention analysis...")
    fig = create_contention_analysis(data)
    path = os.path.join(output_folder, f"{prefix}05_contention_analysis.html")
    fig.write_html(path)
    charts.append(('Contention Analysis', path))

    # 6. RL metrics (if available)
    print("  → Generating RL metrics...")
    fig = create_learning_metrics(data)
    if fig:
        path = os.path.join(output_folder, f"{prefix}06_rl_metrics.html")
        fig.write_html(path)
        charts.append(('RL Metrics', path))
    else:
        print("    (No RL metrics found, skipping)")

    # 7. Cluster analysis (if available)
    print("  → Generating cluster analysis...")
    fig = create_cluster_analysis(data)
    if fig:
        path = os.path.join(output_folder, f"{prefix}07_cluster_analysis.html")
        fig.write_html(path)
        charts.append(('Cluster Analysis', path))
    else:
        print("    (No cluster metrics found, skipping)")

    # 8. Individual metric charts
    print("  → Generating individual charts...")
    individual_metrics = [
        ('channel_total_throughput', 'Total Throughput Over Time', 'Total Bits'),
        ('channel_avg_packet_loss_percentage', 'Packet Loss Percentage Over Time', 'Loss %'),
        ('nodes_avg_throughput_per_node', 'Average Throughput per Node', 'Bits/Node'),
    ]

    for col, title, ylabel in individual_metrics:
        fig = create_time_series_chart(data, col, title, ylabel, show_moving_avg=False)
        safe_name = col.replace('_', '-')
        path = os.path.join(output_folder, f"{prefix}10_{safe_name}.html")
        fig.write_html(path)

    return charts


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main function."""

    if len(sys.argv) < 2:
        print("Usage: python chart_generator.py <csv_folder> [output_folder] [scenario_name]")
        print("Example: python chart_generator.py ./results ./charts homogeneous_100")
        sys.exit(1)

    input_folder = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "./charts_output"
    scenario_name = sys.argv[3] if len(sys.argv) > 3 else ""

    os.makedirs(output_folder, exist_ok=True)

    print()
    print("=" * 70)
    print("  CSMA/CA Protocol Comparison - Chart Generator")
    print("=" * 70)
    print(f"  Input folder:  {input_folder}")
    print(f"  Output folder: {output_folder}")
    if scenario_name:
        print(f"  Scenario:      {scenario_name}")
    print("=" * 70)
    print()

    print("Loading CSV files...")
    data = load_csv_files(input_folder)
    print(f"\nLoaded {len(data)} files.\n")

    print("Generating charts...")
    print("-" * 50)
    charts = create_complete_report(data, output_folder, scenario_name)
    print("-" * 50)

    print()
    print("=" * 70)
    print("  Generation complete!")
    print("=" * 70)
    print(f"\n  Generated {len(charts)} chart files:")
    for name, path in charts:
        print(f"    • {name}: {os.path.basename(path)}")
    print(f"\n  Open the HTML files in your browser to view.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()