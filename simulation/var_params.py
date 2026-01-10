QUICK_TEST_CONFIG = {
    "node_counts": [50, 100],
    "packet_probabilities": [0.01],
    "epsilons": [0.1, 0.3],
    "simulation_ticks": 1000,
    "runs_per_config": 1,
    "description": "Quick validation test"
}

MEDIUM_EXPERIMENT_CONFIG = {
    "node_counts": [100, 500, 1000],
    "packet_probabilities": [0.005, 0.01, 0.02],
    "epsilons": [0.0, 0.1, 0.3],
    "simulation_ticks": 5000,
    "runs_per_config": 3,
    "description": "Medium experiment for initial analysis"
}

FULL_EXPERIMENT_CONFIG = {
    "node_counts": [50, 100, 250, 500, 1000],
    "packet_probabilities": [0.001, 0.005, 0.01, 0.02, 0.05],
    "epsilons": [0.0, 0.05, 0.1, 0.2, 0.3, 0.5],
    "simulation_ticks": 10000,
    "runs_per_config": 5,
    "description": "Full experiment as per project requirements"
}


# ==============================================================================
# EXPECTED BEHAVIORS AND WHAT TO LOOK FOR
# ==============================================================================

"""
EXPECTED PATTERNS:

1. As N_NODES increases:
   - Both baseline and RL should see decreased PDR
   - RL improvement margin should INCREASE (RL handles contention better)
   - Throughput may increase then plateau or decrease

2. As PACKET_PROBABILITY increases:
   - More collisions for both protocols
   - RL should adapt better to high-traffic conditions
   - Watch for saturation point where both fail

3. As EPSILON varies:
   - Very low (0.0): Good if learned policy is optimal
   - Medium (0.1-0.2): Best for adapting to changing conditions
   - High (0.5+): Poor performance, too much exploration

4. METRICS TO REPORT:
   - Packet Delivery Ratio (PDR): key success metric
   - Throughput: useful data transmitted per time
   - Packet Loss Ratio: complement to PDR
   - Timeout count: indicates network stress

5. COMPARISON QUESTIONS TO ANSWER:
   - Does RL outperform baseline? Under what conditions?
   - What epsilon gives best performance?
   - How does performance scale with node count?
   - Is there a "sweet spot" for packet probability?
"""