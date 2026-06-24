import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


HISTORY_PATH = Path(__file__).resolve().parent / "history.json"
OUT_DIR = Path(__file__).resolve().parent / "plots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(HISTORY_PATH, "r", encoding="utf-8") as f:
    history = json.load(f)


def plot_series(x, y, labels, title, ylabel, filename, y_lims=None):
    plt.figure(figsize=(10, 6))
    for series_y, label in zip(y, labels):
        plt.plot(x, series_y, label=label, linewidth=2)
    plt.title(title)
    plt.xlabel("Epoch")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend()
    if y_lims is not None:
        plt.ylim(*y_lims)
    plt.tight_layout()
    plt.savefig(OUT_DIR / filename, dpi=200)
    plt.close()


# Epoch index
n = len(history.get("train_loss", []))
epochs = list(range(1, n + 1))

# 1) train_loss vs val_loss
if "train_loss" in history and "val_loss" in history:
    plot_series(
        epochs,
        [history["train_loss"], history["val_loss"]],
        ["train_loss", "val_loss"],
        "GREG Retina - Loss",
        "Loss",
        "01_train_vs_val_loss.png",
    )

# 2) train_acc vs val_acc
if "train_acc" in history and "val_acc" in history:
    plot_series(
        epochs,
        [history["train_acc"], history["val_acc"]],
        ["train_acc", "val_acc"],
        "GREG Retina - Accuracy",
        "Accuracy",
        "02_train_vs_val_acc.png",
    )

# 3) val_ece
if "val_ece" in history:
    plot_series(
        epochs,
        [history["val_ece"]],
        ["val_ece"],
        "GREG Retina - Val ECE",
        "ECE",
        "03_val_ece.png",
    )

# 4) val_temperature
if "val_temperature" in history:
    plot_series(
        epochs,
        [history["val_temperature"]],
        ["val_temperature"],
        "GREG Retina - Val Temperature (Temperature Scaling)",
        "Temperature",
        "04_val_temperature.png",
    )

# 5) lr
if "lr" in history:
    plot_series(
        epochs,
        [history["lr"]],
        ["lr"],
        "GREG Retina - Learning Rate",
        "LR",
        "05_lr.png",
        y_lims=None,
    )

# 6) delta
if "delta" in history:
    plot_series(
        epochs,
        [history["delta"]],
        ["delta"],
        "GREG Retina - Delta (internal signal)",
        "Delta",
        "06_delta.png",
    )

print(f"OK - plots saved to: {OUT_DIR}")

