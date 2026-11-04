# Mode 5 V3 Validation

## Purpose
Validate the strict paper-based Mode 5 MPR selection implementation
after removing temporary diagnostic instrumentation.

## Simulation configuration
- Simulator: ns-3
- MPR mode: 5
- Mobility: Gauss-Markov 3D
- Nodes: 30
- Speed: 10
- Communication/LET range parameter: 500
- Area: 1000
- Altitude: 1000
- gmAlpha: 0.85
- gmStep: 1
- Wi-Fi standard: 80211b
- Packet size: 512 bytes
- Packet interval: 0.1 s
- Simulation time: 60 s
- Seed: 1

## Results
- MPR computations: 8421
- Computations with uncovered 2-hop nodes: 1
- Coverage failure rate: 0.0119%
- Reproduction: PASS

## Remaining failure
- Node: 10.1.1.23
- Audit timestamp identifier: 58060800204
- Target 2-hop nodes: 12
- Uncovered 2-hop nodes: 1
- Selected MPR nodes: 5
- Uncovered target: 10.1.1.4

Prior targeted diagnostics identified two candidate relays:
- 10.1.1.13: distance 524.673 m
- 10.1.1.20: distance 503.868 m

Both exceeded the configured LET range of 500 m.
Their computed LET was zero, resulting in IETX = 1
when fr = rr = 1, so they failed the strict IETX < 1 criterion.

## Interpretation
The failure rate is measured per MPR computation.
It is not a packet delivery ratio or end-to-end reliability metric.

This is a single-seed validation, not a statistical performance
comparison. Further experiments across multiple seeds are required.
