#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JOBS="${JOBS:-8}"
RESULTS="${RESULTS:-$ROOT/results/paper_reproduction}"

EXE="$ROOT/build/scratch/ns3-dev-olsr_baseline-default"

if [[ ! -x "$EXE" ]]; then
    echo "ERROR: default 실행 파일이 없습니다: $EXE"
    echo "먼저 ./ns3 configure --build-profile=default && ./ns3 build olsr_baseline"
    exit 1
fi

if [[ -e "$RESULTS" ]]; then
    echo "ERROR: 결과 디렉터리가 이미 존재합니다: $RESULTS"
    echo "기존 결과 보호를 위해 실행하지 않습니다."
    echo "RESULTS 환경변수로 새로운 디렉터리를 지정하세요."
    exit 1
fi

mkdir -p "$RESULTS"

run_one() {
    local speed="$1"
    local seed="$2"
    local mode="$3"

    local name="speed${speed}_seed${seed}_mode${mode}"
    local work="$RESULTS/work_${name}"
    local out="$RESULTS/${name}.csv"
    local log="$RESULTS/${name}.log"

    mkdir -p "$work"

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

export ROOT RESULTS EXE
export -f run_one

for speed in 5 10 15 20 25; do
    for seed in $(seq 1 10); do
        for mode in 0 1 3 4; do
            echo "$speed $seed $mode"
        done
    done
done | xargs -P "$JOBS" -n 3 bash -c 'run_one "$0" "$1" "$2"'

echo "=== 논문 재현 실험 완료 ==="

count=$(find "$RESULTS" -maxdepth 1 \
    -name 'speed*_seed*_mode*.csv' | wc -l)

echo "생성된 실험 CSV: $count / 200"

if [[ "$count" -ne 200 ]]; then
    echo "ERROR: 예상한 200개 CSV가 생성되지 않았습니다."
    exit 1
fi
