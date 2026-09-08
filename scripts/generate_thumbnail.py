#!/usr/bin/env python3
"""Generate high-resolution Kaggle dataset thumbnail from real 2024 AtmosSim multi-city data."""

import shutil
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

# Load real 2024 data
master_path = Path("artifacts/multiyear_dataset/multicity_2018_2024_continuous_master.parquet")
if not master_path.exists():
    raise FileNotFoundError(f"Missing master dataset at {master_path}")

df = pd.read_parquet(master_path)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["year"] = df["timestamp"].dt.year
df_2024 = df[df["year"] == 2024].copy()

cities = ["Delhi", "Mumbai", "Pune", "Bengaluru"]
city_colors = {
    "Delhi": "#c0392b",       # Crimson / Brick red
    "Mumbai": "#2980b9",      # Maritime blue
    "Pune": "#8e44ad",        # Leeward purple
    "Bengaluru": "#27ae60",   # Plateau emerald green
}

# Set styling
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
fig, axes = plt.subplots(2, 2, figsize=(14, 7), sharex=True, sharey=True, dpi=200)
fig.patch.set_facecolor("#ffffff")

# Common Y-limit shared across all 4 subplots
y_max = 750

for idx, (city, ax) in enumerate(zip(cities, axes.flatten())):
    c_df = df_2024[df_2024["city"] == city].set_index("timestamp")
    daily_pm25 = c_df["target_pm25"].resample("D").mean()
    mean_val = c_df["target_pm25"].mean()
    color = city_colors[city]

    # Plot daily line + soft area fill
    ax.plot(daily_pm25.index, daily_pm25.values, color=color, linewidth=1.8, label="Daily Mean PM2.5")
    ax.fill_between(daily_pm25.index, 0, daily_pm25.values, color=color, alpha=0.18)

    # Subplot Title & Live Annual Mean Badge
    ax.set_title(f"{city.upper()}  •  Annual Mean: {mean_val:.1f} µg/m³", 
                 fontsize=13, fontweight="bold", pad=8, color="#2c3e50", loc="left")

    # Grid & Spines
    ax.grid(True, linestyle="--", alpha=0.4, color="#bdc3c7")
    ax.set_ylim(0, y_max)
    ax.tick_params(colors="#34495e", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color("#bdc3c7")
        spine.set_linewidth(0.8)

    # Y-axis label only on left column
    if idx % 2 == 0:
        ax.set_ylabel("PM2.5 (µg/m³)", fontsize=11, fontweight="semibold", color="#2c3e50")

# X-axis date formatting
axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
axes[1, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
axes[1, 1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
axes[1, 1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))

fig.suptitle("AtmosSim 2024 — Simulated PM2.5 Across 4 Indian Cities", 
             fontsize=17, fontweight="bold", color="#1a252f", y=0.98)

plt.tight_layout(rect=[0, 0.02, 1, 0.94])

out_file = Path("dataset_thumbnail.png")
plt.savefig(out_file, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()

print(f"Generated thumbnail successfully at: {out_file.resolve()} ({out_file.stat().st_size / 1024:.1f} KB)")

# Copy to artifact directory for embedding/inspection
artifact_dir = Path("/home/suraj/.gemini/antigravity-cli/brain/6a5ae528-95cb-46bf-a2a7-5fc374d709c7")
if artifact_dir.exists():
    shutil.copy(out_file, artifact_dir / "dataset_thumbnail.png")
    print(f"Copied thumbnail to artifact directory: {artifact_dir / 'dataset_thumbnail.png'}")
