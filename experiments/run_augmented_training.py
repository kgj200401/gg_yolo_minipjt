"""Train, then evaluate and save a baseline comparison automatically."""
import json
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    run = root / "runs/detect/ozm_augmented"
    if run.exists():
        raise SystemExit("ozm_augmented already exists; choose a new experiment name")
    subprocess.run([sys.executable, "experiments/train_model.py", "--data", "dataset_augmented/data.yaml",
                    "--model", "yolov8n.pt", "--device", "0", "--epochs", "150",
                    "--batch", "16", "--lr0", "0.001", "--optimizer", "AdamW",
                    "--patience", "25", "--workers", "2", "--cos-lr",
                    "--degrees", "15", "--shear", "10", "--fliplr", "0.5",
                    "--name", "ozm_augmented"], cwd=root, check=True)
    output = root / "runs/evaluation_augmented"
    subprocess.run([sys.executable, "experiments/evaluate_model.py", "--model", str(run / "weights/best.pt"),
                    "--output", str(output)], cwd=root, check=True)
    old = json.loads((root / "runs/evaluation/report.json").read_text(encoding="utf-8"))
    new = json.loads((output / "report.json").read_text(encoding="utf-8"))
    lines = ["# Baseline vs augmented (test split)", "", "Confidence=0.70, matching IoU=0.50.",
             "AP evaluated separately across confidence thresholds.", "",
             "| Metric | Baseline | Augmented | Delta (pp) |", "|---|---:|---:|---:|"]
    for key in ("precision", "recall", "f1", "map50", "map50_95"):
        a = old['overall'][key] if key in old['overall'] else old[key]
        b = new['overall'][key] if key in new['overall'] else new[key]
        lines.append(f"| {key} | {a*100:.2f}% | {b*100:.2f}% | {(b-a)*100:+.2f} |")
    text = "\n".join(lines) + "\n"
    (output / "comparison.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
