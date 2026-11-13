#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/jm/ns-3-dev"
RESULTS="$ROOT/results/main"
JOBS="${JOBS:-8}"

mkdir -p "$RESULTS"

EXE="$ROOT/build/scratch/ns3-dev-olsr_baseline-default"

if [[ ! -x "$EXE" ]]; then
    echo "실행 파일을 찾을 수 없습니다: $EXE"
    exit 1
fi

echo "실행 파일: $EXE"

run_one() {
    local speed="$1"
    local seed="$2"
    local mode="$3"

    local name="speed${speed}_seed${seed}_mode${mode}"
    local work="$RESULTS/work_${name}"
    local out="$RESULTS/${name}.csv"
    local log="$RESULTS/${name}.log"

    if [[ -s "$out" && -s "${out}.control.csv" ]]; then
        echo "SKIP $name"
        return 0
    fi

    mkdir -p "$work"
    rm -f "$out" "${out}.control.csv"

    echo "RUN $name"

    (
        cd "$work"

        "$EXE" \
            --mprMode="$mode" \
            --nodes=30 \
            --mobility=gaussmarkov3d \
            --speed="$speed" \
            --range=500 \
            --area=1000 \
            --altitude=1000 \
            --gmAlpha=0.85 \
            --gmStep=1 \
            --wifiStandard=80211b \
            --packetSize=512 \
            --packetInterval=0.1 \
            --simTime=60 \
            --seed="$seed" \
            --riskHorizon=5 \
            --riskSigma=2 \
            --riskAlpha=0.9 \
            --riskScenarios=100 \
            --riskAddThreshold=1.5 \
            --riskRemoveThreshold=0.5 \
            --out="$out"
    ) > "$log" 2>&1

    echo "DONE $name"
}

export -f run_one
export ROOT RESULTS EXE

for speed in 5 10 15 20 25; do
    for seed in $(seq 1 10); do
        for mode in 0 1 3 4; do
            echo "$speed $seed $mode"
        done
    done
done | xargs -P "$JOBS" -n 3 bash -c 'run_one "$0" "$1" "$2"'

echo "=== 병렬 실험 완료 ==="
