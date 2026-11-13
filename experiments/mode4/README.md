# CVaR-RAMPR: Risk-Aware Redundant MPR Selection for FANETs

## Overview
This repository contains ns-3 experiments for OLSR-based Flying Ad Hoc Networks (FANETs), including a research implementation of risk-aware redundant MultiPoint Relay (MPR) selection.

The Mode 4 implementation uses a link-lifetime risk estimate based on Conditional Value-at-Risk (CVaR) and separate add/remove thresholds for backup relay selection. The codebase also contains exploratory Mode 5 changes; these must not be confused with the Mode 4 evaluation.

## Repository layout
- `ns-3-dev/src/olsr/`: modified OLSR implementation and tests.
- `ns-3-dev/scratch/olsr_baseline.cc`: simulation entry point.
- `ns-3-dev/scripts/`: experiment-related scripts.
- `experiments/mode4/results/`: aggregate CSV results from the Mode 4 comparison.
- `experiments/mode5/`: separate exploratory experiments.

## Compared modes
| Mode | Description |
|---|---|
| 0 | Standard OLSR MPR selection |
| 1 | Fixed redundant MPR selection (k=2) |
| 3 | LET-based greedy MPR selection |
| 4 | Hysteresis-CVaR-RAMPR (proposed) |

## Evaluation setup
The recorded comparison used 30 nodes, a 60 s simulation, 3D Gauss–Markov mobility, and speeds of 5, 10, 15, 20, and 25 m/s. Each mode/speed combination was repeated with 10 seeds (4 × 5 × 10 = 200 runs). Additional recorded settings: communication range 500 m, area parameter 1000, altitude parameter 1000, Gauss–Markov alpha 0.85 and step 1, Wi-Fi 802.11b, 512-byte packets, and 0.1 s packet interval.

Recorded Mode 4 parameters: `--riskHorizon=5 --riskSigma=2 --riskAlpha=0.9 --riskScenarios=100 --riskAddThreshold=1.5 --riskRemoveThreshold=0.5`.

**Reproduction caveat:** This repository includes ongoing code changes. Do not assume that the latest source tree is byte-identical to the version used for all 200 recorded runs. Preserve and identify the exact experiment commit before claiming bit-for-bit reproduction. Verify the command-line parameters supported by the checked-out revision before rerunning.

## Mean packet delivery ratio (PDR, %)
| Speed (m/s) | Mode 0 | Mode 1 | Mode 3 | Mode 4 |
|---:|---:|---:|---:|---:|
| 5 | 91.74 | 93.67 | 92.56 | 95.31 |
| 10 | 87.18 | 87.08 | 88.23 | 88.51 |
| 15 | 67.49 | 71.15 | 71.87 | 72.59 |
| 20 | 63.10 | 61.15 | 62.31 | 65.05 |
| 25 | 59.59 | 63.38 | 65.62 | 60.44 |

Mode 4 has the highest observed mean PDR at 5–20 m/s, but not at 25 m/s. Paired 95% confidence intervals for Mode 4 minus Mode 0 PDR include zero at all five speeds; a statistically significant improvement has **not** been demonstrated by these experiments.

## Building and running
From the `ns-3-dev/` directory, first check the local ns-3 version and supported command-line arguments:

```bash
./ns3 configure
./ns3 build
./ns3 run 'scratch/olsr_baseline --help'
```

Then reproduce the desired mode, speed and seed using the options supported by that revision. Example Mode 4 parameters are documented above; confirm that they apply to the checked-out simulation before execution. For a faithful reproduction, record the Git commit SHA, build configuration, run command, output path, and random seed.

## Interpretation and limitations
- MPR redundancy increases the number of relay candidates and can increase OLSR control overhead.
- The simulation implementation may access mobility state directly; this is not equivalent to demonstrating a fully distributed real-world deployment.
- No universal reduction in MPR-set changes or end-to-end delay is established by the recorded results.
- Mode 5 is exploratory and should be reported separately from the 200-run Mode 4 comparison.

## License
The repository includes ns-3-derived source code. Preserve upstream license and copyright notices. Check the licenses of all included files before redistribution.
