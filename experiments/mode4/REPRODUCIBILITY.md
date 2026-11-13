# Mode 4 Reproducibility Check

## Scope
This document records one independently rebuilt and rerun ns-3 FANET OLSR experiment using the repository source. It does **not** establish reproduction of the full 200-run study.

## Configuration
- Program: `scratch/olsr_baseline.cc`
- MPR mode: 4 (Hysteresis-CVaR)
- Seed: 1; nodes: 30; speed: 15 m/s; duration: 60 s
- Radio range: 500 m; area: 1000 m; 3D Gauss-Markov mobility
- Altitude: 1000 m; gmAlpha: 0.85; gmStep: 1
- Wi-Fi: 80211b; payload: 512 bytes; packet interval: 0.1 s
- Risk: horizon 5 s, sigma 2, alpha 0.9, 100 scenarios, add threshold 1.5 s, remove threshold 0.5 s

## Command
Run from the `ns-3-dev/` directory after configuring and building ns-3:

```bash
./ns3 run "olsr_baseline --mprMode=4 --seed=1 --nodes=30 --speed=15 --simTime=60 --range=500 --area=1000 --mobility=gaussmarkov3d --altitude=1000 --gmAlpha=0.85 --gmStep=1 --wifiStandard=80211b --packetSize=512 --packetInterval=0.1 --riskHorizon=5 --riskSigma=2 --riskAlpha=0.9 --riskScenarios=100 --riskAddThreshold=1.5 --riskRemoveThreshold=0.5 --out=mode4_reproduction.csv"
```

## Observed comparison

| Metric | Original study (`results/analysis/all_runs.csv`) | Independent rerun | Status |
| --- | ---: | ---: | --- |
| TX packets | 390 | 390 | Match |
| RX packets | 245 | 245 | Match |
| PDR | 62.82051282051282% | 62.8205% (rounded display) | Match |
| Mean delay | 2.79472 ms | 2.79472 ms | Match |
| Control TX overhead | 169928 bytes | 169928 bytes | Match |

Original study row: `speed=15,seed=1,mode=4`. Rerun flow CSV records PDR as a fraction (`0.628205`), while the terminal and original analysis CSV report percent.

## Control overhead calculation

The rerun generated `mode4_reproduction.csv.control.csv` with `time,node,event,packet_bytes,hello_count,tc_count,mid_count,hna_count`. Summing `packet_bytes` for TX events only gave 1280 control TX records and 169928 bytes.

```bash
awk -F',' 'NR>1 && $3=="TX" {bytes+=$4; packets++} END {printf "TX packets=%d, overhead=%.0f bytes\n",packets,bytes}' mode4_reproduction.csv.control.csv
```

## Limitations and next steps
- Verified one Mode 4 configuration and seed only; other speeds, seeds, and modes remain unverified.
- Exact toolchain/ns-3 revision, environment details, and code provenance at the time of the original study were not independently audited.
- Build success and matching results on one run do not demonstrate algorithmic superiority or statistical significance.
- Next: rerun selected Mode 0, 1, and 3 configurations and compare against the matching rows in `all_runs.csv`.
