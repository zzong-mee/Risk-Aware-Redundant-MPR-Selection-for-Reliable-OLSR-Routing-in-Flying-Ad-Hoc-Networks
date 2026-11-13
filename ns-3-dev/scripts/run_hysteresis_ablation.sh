#!/usr/bin/env bash
set -euo pipefail

mkdir -p results/hysteresis_ablation

for speed in 5 10 15 20 25; do
    for seed in $(seq 1 10); do
        out="results/hysteresis_ablation/mode4_equal_speed${speed}_seed${seed}.csv"

        if [[ -s "$out" && -s "${out}.mpr.csv" ]]; then
            echo "SKIP speed=$speed seed=$seed"
            continue
        fi

        echo "RUN speed=$speed seed=$seed"

        ./ns3 run "scratch/olsr_baseline \
          --mprMode=4 \
          --nodes=30 \
          --mobility=gaussmarkov3d \
          --speed=$speed \
          --range=500 \
          --area=1000 \
          --altitude=1000 \
          --gmAlpha=0.85 \
          --gmStep=1 \
          --wifiStandard=80211b \
          --packetSize=512 \
          --packetInterval=0.1 \
          --simTime=60 \
          --seed=$seed \
          --riskHorizon=5 \
          --riskSigma=2 \
          --riskAlpha=0.9 \
          --riskScenarios=100 \
          --riskAddThreshold=1.0 \
          --riskRemoveThreshold=1.0 \
          --out=$out"
    done
done

echo "All hysteresis ablation runs completed."
