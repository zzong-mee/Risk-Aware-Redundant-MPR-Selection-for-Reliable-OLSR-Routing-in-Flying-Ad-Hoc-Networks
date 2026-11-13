# FANET Research — KCI Paper Reproduction

This repository provides the ns-3 simulation implementation and experiment scripts for the research paper:

**Risk-Aware Redundant MPR Selection for Reliable OLSR Routing in Flying Ad-Hoc Networks**

The study investigates reliable routing in Flying Ad Hoc Networks (FANETs) through risk-aware redundant Multi-Point Relay (MPR) selection in the Optimized Link State Routing (OLSR) protocol.

The `main` branch contains the implementation used to reproduce the KCI paper experiments. Subsequent research and development code is maintained separately in the `development` branch.

## 1. Research Overview

Flying Ad Hoc Networks (FANETs) experience frequent topology changes due to high node mobility, which can cause unstable links and packet delivery failures.

This research proposes a risk-aware redundant MPR selection approach that uses Link Expiration Time (LET), Conditional Value at Risk (CVaR), and hysteresis-based control to improve routing reliability.

The proposed algorithm is evaluated against standard OLSR and alternative redundant MPR selection methods using ns-3 simulations.

## 2. Implemented Algorithms

| Mode | Algorithm | Description |
|---|---|---|
| 0 | Standard OLSR | Standard MPR selection |
| 1 | Fixed Redundancy | Fixed redundant MPR selection |
| 3 | LET-Based Redundancy | LET-based risk-aware redundant MPR selection |
| 4 | Proposed Method | CVaR-based redundant MPR selection with hysteresis |

Mode 4 is the proposed algorithm evaluated in the paper.

## 3. Experiment Configuration

| Parameter | Value |
|---|---|
| Simulator | ns-3 |
| Number of UAVs | 30 |
| Mobility Model | 3D Gauss-Markov |
| UAV Speeds | 5, 10, 15, 20, 25 m/s |
| Random Seeds | 1–10 |
| Communication Range | 500 m |
| Simulation Area | 1000 × 1000 m |
| Simulation Duration | 60 s |
| Wireless Standard | IEEE 802.11b |
| Packet Size | 512 bytes |
| Packet Interval | 0.1 s |
| Risk Prediction Horizon | 5 s |
| Risk Sigma | 2 m/s |
| CVaR Alpha | 0.9 |
| Risk Scenarios | 100 |
| Hysteresis Add Threshold | 1.5 |
| Hysteresis Remove Threshold | 0.5 |

**Total experiments: 4 modes × 5 speeds × 10 seeds = 200 simulation runs.**

## 4. Build Instructions

The experiments were developed and tested in an Ubuntu (WSL) environment.

Navigate to the ns-3 project directory:

```bash
cd ns-3-dev
```

Configure ns-3 using the default build profile:

```bash
./ns3 configure --build-profile=default --enable-examples
```

Build the simulation program:

```bash
./ns3 build olsr_baseline
```

The expected executable is:

```text
build/scratch/ns3-dev-olsr_baseline-default
```

## 5. Reproduce the Experiments

The reproduction script executes all 200 experiment configurations.

```bash
cd ns-3-dev
JOBS=8 bash scripts/run_paper_reproduction.sh
```

The default results directory is:

```text
results/paper_reproduction/
```

To specify a separate output directory:

```bash
RESULTS=/tmp/fanet-new-run JOBS=8 \
bash scripts/run_paper_reproduction.sh
```

The script is designed to protect existing results by requiring a new output directory.

## 6. Analyze Simulation Results

After completing the simulations, run:

```bash
cd ns-3-dev
python3 scripts/analyze_paper_reproduction.py
```

The analysis generates:

| File | Description |
|---|---|
| `all_runs.csv` | Results from individual simulation runs |
| `summary.csv` | Aggregated performance statistics |
| `paired_comparison.csv` | Paired comparisons between Mode 4 and baseline modes |

The analysis includes Packet Delivery Ratio (PDR), end-to-end delay, control overhead, and confidence intervals.

For a custom experiment directory:

```bash
RESULTS=/tmp/fanet-new-run \
ANALYSIS_OUT=/tmp/fanet-analysis \
python3 scripts/analyze_paper_reproduction.py
```

## 7. Verified Reproduction Results

The following reference experiment was reproduced using the `main` branch implementation.

**Reference configuration:**

- UAV nodes: 30
- Speed: 15 m/s
- Random seed: 1
- Simulation duration: 60 s

| Mode | TX | RX | PDR (%) | Average Delay (ms) |
|---|---:|---:|---:|---:|
| 0 | 390 | 257 | 65.8974 | 2.77044 |
| 1 | 390 | 189 | 48.4615 | 2.59482 |
| 3 | 390 | 224 | 57.4359 | 2.71257 |
| 4 | 390 | 245 | 62.8205 | 2.79472 |

All four reference experiments reproduced the historical results.

### PDR Results Across UAV Speeds

The following values are averages from the original 200-run experiment dataset.

| Speed (m/s) | Mode 0 (%) | Mode 1 (%) | Mode 3 (%) | Mode 4 (%) |
|---|---:|---:|---:|---:|
| 5 | 91.74 | 93.67 | 92.56 | 95.31 |
| 10 | 87.18 | 87.08 | 88.23 | 88.51 |
| 15 | 67.49 | 71.15 | 71.87 | 72.59 |
| 20 | 63.10 | 61.15 | 62.31 | 65.05 |
| 25 | 59.59 | 63.38 | 65.62 | 60.44 |

At 15 m/s, the proposed Mode 4 achieved a mean PDR of 72.59%, compared with 67.49% for standard OLSR, corresponding to an improvement of **5.10 percentage points**.

The paired 95% confidence interval for this difference was −4.42 to +14.63 percentage points. Therefore, the observed mean improvement should not be interpreted as statistically significant at the 5% level.

## 8. Source Code Verification

The restored OLSR implementation is located at:

```text
ns-3-dev/src/olsr/model/olsr-routing-protocol.cc
```

SHA-256 checksum:

```text
c549a62e83b9473f0a957b2ca97057d591d0bee67715898aabd4392864a2ac8f
```

The source was restored from the historical Stage 6 backup and verified against representative simulation outputs.

To verify the source checksum:

```bash
sha256sum src/olsr/model/olsr-routing-protocol.cc
```

## 9. Reproducibility Status

The following verification steps have been completed:

- [x] Restored the historical Stage 6 OLSR implementation.
- [x] Successfully built the simulation using the default profile.
- [x] Reproduced the reference results for Modes 0, 1, 3, and 4.
- [x] Verified the analysis script using the historical 200-run dataset.
- [x] Confirmed that the generated `summary.csv` and `all_runs.csv` match the original analysis outputs.
- [ ] Complete a fresh execution and verification of all 200 simulation runs.

**Important:** The representative simulations and historical data analysis have been verified. A complete fresh reproduction of all 200 simulation runs has not yet been performed.

## 10. Repository Branches

| Branch | Purpose |
|---|---|
| `main` | KCI paper experiment reproduction |
| `development` | Subsequent algorithm development and additional experiments |

The `main` branch is intended to preserve the paper reproduction implementation, while future algorithm improvements are maintained in `development`.

## 11. Research Environment

- Ubuntu / WSL
- ns-3
- C++
- Python 3
- IEEE 802.11b wireless simulation
- OLSR routing protocol

## 12. Research Purpose

This repository is maintained to support reproducibility, algorithm comparison, and further research on reliable routing in highly dynamic FANET environments.
