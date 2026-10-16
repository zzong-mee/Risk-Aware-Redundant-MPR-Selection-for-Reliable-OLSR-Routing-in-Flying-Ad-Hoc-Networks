
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path.home() / "jm/ns-3-dev"
RESEARCH = ROOT / "research"
VAULT = Path.home() / "jm/obsidian"

EXPERIMENTS = {
    "EXP-001": "Basic OLSR",
    "EXP-002": "LET Switch",
}


def latest_result(exp_id):
    result_dir = RESEARCH / "experiments" / exp_id / "results"

    if not result_dir.exists():
        return None

    files = sorted(result_dir.glob("*.json"), reverse=True)

    for file in files:
        try:
            with file.open(encoding="utf-8") as f:
                data = json.load(f)

            if data.get("pdr") is not None:
                return data

        except (OSError, ValueError, TypeError):
            continue

    return None


def main():
    labels = []
    values = []
    run_ids = []

    for exp_id, name in EXPERIMENTS.items():
        data = latest_result(exp_id)

        if data is None:
            print(f"[SKIP] {exp_id}: 유효한 결과 없음")
            continue

        labels.append(f"{exp_id}\n{name}")
        values.append(float(data["pdr"]))
        run_ids.append(data.get("run_id", "unknown"))

    if not values:
        print("그래프를 생성할 실험 결과가 없습니다.")
        return 1

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(labels, values, width=0.55)

    ax.set_title("FANET Routing - PDR Comparison")
    ax.set_ylabel("Packet Delivery Ratio (%)")
    ax.set_ylim(0, 110)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=0.25)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 2,
            f"{value:.2f}%",
            ha="center",
            fontsize=11,
        )

    fig.tight_layout()

    plot_dir = RESEARCH / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    output = plot_dir / "pdr_comparison.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)

    print(f"그래프 생성: {output}")

    # Obsidian으로 복사
    if VAULT.is_dir():
        import shutil

        obsidian_plot_dir = VAULT / "04_Experiments" / "plots"
        obsidian_plot_dir.mkdir(parents=True, exist_ok=True)

        destination = obsidian_plot_dir / "pdr_comparison.png"
        shutil.copy2(output, destination)

        print(f"Obsidian 그래프: {destination}")

    # 비교에 사용한 실행 ID 기록
    metadata = {
        "experiments": [
            {"label": label, "pdr": value, "run_id": run_id}
            for label, value, run_id
            in zip(labels, values, run_ids)
        ]
    }

    metadata_file = plot_dir / "pdr_comparison.json"
    metadata_file.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
