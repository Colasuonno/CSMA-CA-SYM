#!/usr/bin/env python3
"""
Script per generare grafici di confronto da file CSV di simulazione di rete.
Legge tutti i file CSV da una cartella e crea grafici comparativi.
Genera dashboard interattive HTML con Plotly.
"""

import os
import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path


def load_csv_files(folder_path: str) -> dict[str, pd.DataFrame]:
    """Carica tutti i file CSV dalla cartella specificata."""
    csv_files = {}
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Errore: La cartella '{folder_path}' non esiste.")
        sys.exit(1)

    for file_path in folder.glob("*.csv"):
        try:
            df = pd.read_csv(file_path)
            name = file_path.stem
            csv_files[name] = df
            print(f"Caricato: {file_path.name} ({len(df)} righe)")
        except Exception as e:
            print(f"Errore nel caricamento di {file_path.name}: {e}")

    if not csv_files:
        print(f"Nessun file CSV trovato in '{folder_path}'")
        sys.exit(1)

    return csv_files


def get_colors(n: int) -> list[str]:
    """Genera una lista di colori distinti."""
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
    ]
    return colors[:n] if n <= len(colors) else colors * (n // len(colors) + 1)


def create_interactive_dashboard(data: dict[str, pd.DataFrame], output_path: str):
    """Crea una dashboard interattiva HTML con Plotly."""

    colors = get_colors(len(data))

    # Definizione metriche per la dashboard
    # (colonna, titolo, ylabel, scala_log)
    metrics = [
        ('channel_avg_packet_loss_percentage', 'Packet Loss % (Canale)', 'Loss %', False),
        ('channel_avg_recent_packet_loss', 'Recent Packet Loss (Canale)', 'Loss', False),
        ('nodes_avg_packet_loss_percentage', 'Packet Loss % (Nodi)', 'Loss %', False),
        ('nodes_avg_recent_packet_loss_pct', 'Recent Packet Loss % (Nodi)', 'Loss %', False),
        ('throughput_normalized', 'Throughput Normalizzato', 'Throughput (bps)', False),
    ]

    # Calcola throughput normalizzato per ogni dataframe
    TICK_TOTALI = 100000000
    for name, df in data.items():
        if 'channel_total_throughput' in df.columns and 'tick' in df.columns:
            # throughput_norm = valore_totale * tick_totali / tick_corrente
            df['throughput_normalized'] = df['channel_total_throughput'] * TICK_TOTALI / df['tick']
            # Gestisci il primo tick (evita divisione per zero)
            df.loc[df['tick'] == 0, 'throughput_normalized'] = 0

    # Crea subplots 2x3 (ultima cella vuota)
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[m[1] for m in metrics],
        horizontal_spacing=0.06,
        vertical_spacing=0.12
    )

    # Popola ogni subplot
    for idx, (col, title, ylabel, log_scale) in enumerate(metrics):
        row = idx // 3 + 1
        col_idx = idx % 3 + 1

        for i, (name, df) in enumerate(data.items()):
            if col in df.columns and 'tick' in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df['tick'],
                        y=df[col],
                        mode='lines',
                        name=name,
                        line=dict(color=colors[i], width=1.5),
                        legendgroup=name,
                        showlegend=(idx == 0),  # Mostra legenda solo per il primo grafico
                        hovertemplate=f'<b>{name}</b><br>Tick: %{{x}}<br>{ylabel}: %{{y:.4f}}<extra></extra>'
                    ),
                    row=row, col=col_idx
                )

        # Configura assi
        fig.update_xaxes(
            title_text='Tick',
            row=row, col=col_idx,
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            dtick=None,
            tickangle=0
        )
        fig.update_yaxes(
            title_text=ylabel,
            row=row, col=col_idx,
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            type='log' if log_scale else 'linear'
        )

    # Layout generale
    fig.update_layout(
        title=dict(
            text='<b>Dashboard Riepilogativa - Confronto Simulazioni</b>',
            x=0.5,
            font=dict(size=20)
        ),
        height=750,
        width=1400,
        template='plotly_white',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.15,
            xanchor='center',
            x=0.5,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(0,0,0,0.3)',
            borderwidth=1
        ),
        hovermode='x unified',
        margin=dict(t=80, b=120, l=60, r=40)
    )

    # Salva come HTML
    fig.write_html(
        output_path,
        include_plotlyjs=True,
        full_html=True,
        config={
            'displayModeBar': True,
            'scrollZoom': True,
            'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'dashboard_simulazioni',
                'height': 750,
                'width': 1400,
                'scale': 2
            }
        }
    )
    print(f"Salvato: {output_path}")


def main():
    """Funzione principale."""
    if len(sys.argv) < 2:
        print("Uso: python csv_comparison_charts.py <cartella_csv> [cartella_output]")
        print("Esempio: python csv_comparison_charts.py ./dati ./grafici")
        sys.exit(1)

    input_folder = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "./grafici_output"

    os.makedirs(output_folder, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Generazione Dashboard Interattiva")
    print(f"{'=' * 60}")
    print(f"Cartella input: {input_folder}")
    print(f"Cartella output: {output_folder}")
    print(f"{'=' * 60}\n")

    print("Caricamento file CSV...")
    data = load_csv_files(input_folder)
    print(f"\nCaricati {len(data)} file.\n")

    print("Generazione dashboard...")
    print("-" * 40)

    create_interactive_dashboard(
        data,
        os.path.join(output_folder, "01_dashboard_riepilogo.html")
    )

    print("-" * 40)
    print(f"\n{'=' * 60}")
    print(f"Generazione completata!")
    print(f"Dashboard salvata in: {output_folder}")
    print(f"Apri il file HTML nel browser per visualizzarla.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()