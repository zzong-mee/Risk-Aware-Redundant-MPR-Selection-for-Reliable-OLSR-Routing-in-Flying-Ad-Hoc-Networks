# CVaR-MPR research prototype

This package contains two distinct experiments:
1. `mpr_selection_benchmark.py`: executable topology-level comparison of greedy, fixed redundancy, LET-aware, and CVaR-adaptive MPR selection. It evaluates coverage, redundancy, relay count, and simulated link-failure resilience. It does NOT modify ns-3 OLSR or measure packet delivery.
2. `olsr_baseline.cc`: stock ns-3 OLSR UDP packet-delivery baseline with mobility and FlowMonitor. All modes in this file use stock OLSR; do not label its results as CVaR-MPR.

Run topology benchmark: `python3 mpr_selection_benchmark.py --runs 100 --output mpr_results.csv`

Copy baseline to `<ns-3-root>/scratch/olsr_baseline.cc`, then run from ns-3 root:
`./ns3 run 'scratch/olsr_baseline --seed=1 --speed=12 --out=baseline.csv'`

For a valid ns-3 end-to-end comparison, the selector must be integrated inside `src/olsr/model/olsr-routing-protocol.cc` in `MprComputation()` (exact API depends on ns-3 version), and relay-set decisions must affect OLSR control-plane state. This is not implemented in this prototype. Keep same seeds, mobility, traffic, radio settings across all variants; measure PDR, delay, control traffic, MPR count, topology convergence and confidence intervals.
