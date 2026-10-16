
#!/usr/bin/env python3
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VAULT = Path.home() / "jm/obsidian"

EXPERIMENTS = {
    "EXP-001": {
        "name": "기본 OLSR",
        "program": "scratch/wifi-olsr-4node",
    },
    "EXP-002": {
        "name": "LET 기반 경로 전환",
        "program": "scratch/wifi-olsr-let-switch",
    },
}


def git_output(*args):
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def count_packets(log):
    sent = len(re.findall(r"client sent", log, re.I))
    received = len(re.findall(r"server received", log, re.I))
    pdr = received / sent * 100 if sent else None
    return sent, received, pdr


def parse_switch(log):
    pattern = (
        r"\[LET SWITCH\]\s*Time:\s*([\d.]+)s"
        r".*?Path LET:\s*([\d.]+)s"
        r".*?Old route:\s*([^\r\n]+)"
        r".*?New route:\s*([^\r\n]+)"
    )
    match = re.search(pattern, log, re.S)
    if not match:
        return None
    return {
        "time": float(match.group(1)),
        "let": float(match.group(2)),
        "old_route": match.group(3).strip(),
        "new_route": match.group(4).strip(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", choices=EXPERIMENTS)
    args = parser.parse_args()

    config = EXPERIMENTS[args.experiment]
    exp_dir = ROOT / "research/experiments" / args.experiment

    for folder in ["logs", "results", "plots"]:
        (exp_dir / folder).mkdir(parents=True, exist_ok=True)

    if not VAULT.is_dir():
        sys.exit(f"Obsidian Vault를 찾을 수 없습니다: {VAULT}")

    now = datetime.datetime.now().astimezone()
    run_id = now.strftime("%Y%m%d-%H%M%S-%f")
    command = ["./ns3", "run", config["program"]]

    print(f"실험 시작: {args.experiment}")
    print(f"실행 명령: {' '.join(command)}")

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    log = result.stdout + "\n" + result.stderr
    log_file = exp_dir / "logs" / f"{run_id}.txt"
    log_file.write_text(log, encoding="utf-8")

    if result.returncode != 0:
        sys.exit(
            f"실험 실패 (종료 코드 {result.returncode}). "
            f"로그 확인: {log_file}"
        )

    sent, received, pdr = count_packets(log)
    switch = parse_switch(log)

    commit = git_output("rev-parse", "--short", "HEAD")
    git_status = git_output("status", "--porcelain", "--untracked-files=no")
    dirty = bool(git_status) if git_status != "unknown" else None

    data = {
        "experiment": args.experiment,
        "name": config["name"],
        "run_id": run_id,
        "executed_at": now.isoformat(),
        "command": " ".join(command),
        "git_commit": commit,
        "git_tracked_changes": dirty,
        "sent": sent,
        "received": received,
        "pdr": pdr,
        "switch": switch,
        "log": str(log_file),
    }

    result_file = exp_dir / "results" / f"{run_id}.json"
    result_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pdr_text = f"{pdr:.2f}%" if pdr is not None else "측정 불가"

    switch_text = "경로 전환 로그 없음"
    if switch:
        switch_text = (
            f"- 전환 시점: {switch['time']}초\n"
            f"- 전환 시 LET: {switch['let']}초\n"
            f"- 이전 경로: {switch['old_route']}\n"
            f"- 새로운 경로: {switch['new_route']}"
        )

    note = f"""---
type: experiment-run
experiment: {args.experiment}
run_id: "{run_id}"
tags:
  - ns3
  - FANET
  - experiment
---

# {args.experiment} | {config['name']}

## 실험 정보
- 실행 시각: {now.isoformat()}
- 실행 명령: `{data['command']}`
- Git 커밋: `{commit}`
- 추적 파일 변경 여부: {dirty}
- 실행 ID: `{run_id}`

## 패킷 전달 결과

| 지표 | 값 |
|---|---:|
| 송신 패킷 | {sent} |
| 수신 패킷 | {received} |
| PDR | {pdr_text} |

## LET 경로 전환

{switch_text}

## 원본 데이터
- 로그: `{log_file}`
- JSON: `{result_file}`

## 연구 분석

## PDR 비교 그래프

![[pdr_comparison.png]]

이 그래프는 각 실험의 최신 유효한 실행 결과를 비교한다.
현재 실행과 다른 실험의 실행 시각은 다를 수 있다.

## 연구 분석

<!-- 실험 결과에 대한 해석을 직접 작성 -->

## 후속 실험

<!-- 다음 실험에서 변경할 조건을 기록 -->
"""

    obsidian_dir = VAULT / "04_Experiments" / args.experiment
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    note_file = obsidian_dir / f"RUN-{run_id}.md"
    with note_file.open("x", encoding="utf-8") as f:
        f.write(note)

    print("\n===== 실험 완료 =====")
    print(f"송신: {sent}")
    print(f"수신: {received}")
    print(f"PDR: {pdr_text}")
    print(f"로그: {log_file}")
    print(f"Obsidian: {note_file}")

    if sent == 0:
        print("주의: 송신 로그가 없어 PDR을 계산할 수 없습니다.")

        # 실험 종료 후 PDR 비교 그래프 자동 생성
    plot_script = ROOT / "research/scripts/plot_results.py"

    plot_result = subprocess.run(
        [sys.executable, str(plot_script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    if plot_result.returncode == 0:
        print("PDR 비교 그래프 생성 완료")
        print(plot_result.stdout)
    else:
        print("주의: 그래프 생성 실패")
        print(plot_result.stderr)


if __name__ == "__main__":
    main()
