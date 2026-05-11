import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

OUT = os.path.dirname(os.path.abspath(__file__)) + "/images"

# ---------- SATLIB Uniform Random-3-SAT (medium) ----------
satlib = [
    ("uf20-91", 20, 91, 1000, 0),
    ("uf50-218", 50, 218, 1000, 1000),
    ("uf75-325", 75, 325, 100, 100),
    ("uf100-430", 100, 430, 1000, 1000),
    ("uf125-538", 125, 538, 100, 100),
    ("uf150-645", 150, 645, 100, 100),
    ("uf175-753", 175, 753, 100, 100),
    ("uf200-860", 200, 860, 100, 100),
    ("uf225-960", 225, 960, 100, 100),
    ("uf250-1065", 250, 1065, 100, 100),
]

# ---------- SAT Competition 2021-2023 (large) ----------
satcomp = [
    ("2021", 352),
    ("2022", 303),
    ("2023", 296),
]

plt.rcParams.update({"font.size": 10, "axes.titlesize": 13, "axes.labelsize": 11})

os.makedirs(OUT, exist_ok=True)

# ============================================================
# Chart 1: SATLIB bar – instance counts by SAT/UNSAT
# ============================================================
fig, ax = plt.subplots(figsize=(10, 4.5))
names = [s[0] for s in satlib]
sat_n = [s[3] for s in satlib]
unsat_n = [s[4] for s in satlib]
x = np.arange(len(names))
w = 0.35
b1 = ax.bar(x - w / 2, sat_n, width=w, label="SAT", color="#4CAF50", edgecolor="white")
b2 = ax.bar(
    x + w / 2, unsat_n, width=w, label="UNSAT", color="#F44336", edgecolor="white"
)
ax.set_xticks(x)
ax.set_xticklabels(names, rotation=30, ha="right")
ax.set_ylabel("Instance Count")
ax.set_title("SATLIB Uniform Random-3-SAT Dataset")
ax.legend()
for bar in b1:
    if bar.get_height() > 0:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 15,
            str(int(bar.get_height())),
            ha="center",
            fontsize=8,
        )
for bar in b2:
    if bar.get_height() > 0:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 15,
            str(int(bar.get_height())),
            ha="center",
            fontsize=8,
        )
plt.tight_layout()
fig.savefig(f"{OUT}/dataset_satlib_counts.png", dpi=150)
fig.savefig(f"{OUT}/dataset_satlib_counts.svg")
plt.close()

# ============================================================
# Chart 2: SATLIB scatter – Vars vs Clauses
# ============================================================
fig, ax = plt.subplots(figsize=(8, 5))
vars_arr = [s[1] for s in satlib]
clses_arr = [s[2] for s in satlib]
sizes = [max(s[3] + s[4], 1) * 0.6 for s in satlib]
ax.scatter(vars_arr, clses_arr, s=sizes, c="#2196F3", alpha=0.7, edgecolors="black")
for i, s in enumerate(satlib):
    ax.annotate(
        s[0],
        (vars_arr[i], clses_arr[i]),
        textcoords="offset points",
        xytext=(5, 8),
        fontsize=8,
    )
ax.set_xlabel("Variables")
ax.set_ylabel("Clauses")
ax.set_title("SATLIB Dataset: Variables vs Clauses")
ratio = np.mean(np.array(clses_arr) / np.array(vars_arr))
ax.plot(
    [0, 260],
    [0, 260 * 4.26],
    "k--",
    alpha=0.3,
    label=f"Clause/Var Ratio ~ {ratio:.1f} (phase transition)",
)
ax.legend(fontsize=9)
plt.tight_layout()
fig.savefig(f"{OUT}/dataset_satlib_scatter.png", dpi=150)
fig.savefig(f"{OUT}/dataset_satlib_scatter.svg")
plt.close()

# ============================================================
# Chart 3: Overview – total instances
# ============================================================
fig, ax = plt.subplots(figsize=(7, 5))
satlib_total = sum(s[3] + s[4] for s in satlib)
satcomp_total = sum(s[1] for s in satcomp)
labels = ["SATLIB\nUniform Random-3-SAT", "SAT Competition\n2021-2023"]
totals = [satlib_total, satcomp_total]
bars = ax.bar(
    labels, totals, color=["#FF9800", "#2196F3"], edgecolor="white", width=0.45
)
for bar, v in zip(bars, totals):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 50,
        str(v),
        ha="center",
        fontweight="bold",
        fontsize=13,
    )
ax.set_ylabel("Total Instances")
ax.set_title("Benchmark Dataset Overview")
ax.set_ylim(0, max(totals) * 1.15)
plt.tight_layout()
fig.savefig(f"{OUT}/dataset_overview.png", dpi=150)
fig.savefig(f"{OUT}/dataset_overview.svg")
plt.close()

# ============================================================
# Chart 4: Breakdown by SATLIB set & SATCOMP year
# ============================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

cats = [s[0] for s in satlib]
y_sat = [s[3] for s in satlib]
y_unsat = [s[4] for s in satlib]
x = np.arange(len(cats))
ax1.bar(x, y_sat, label="SAT", color="#4CAF50", edgecolor="white")
ax1.bar(x, y_unsat, bottom=y_sat, label="UNSAT", color="#F44336", edgecolor="white")
ax1.set_xticks(x)
ax1.set_xticklabels(cats, rotation=45, ha="right", fontsize=7)
ax1.set_ylabel("Instances")
ax1.set_title("SATLIB SAT/UNSAT Breakdown")
ax1.legend(fontsize=8)

comp_names = [s[0] for s in satcomp]
comp_counts = [s[1] for s in satcomp]
ax2.bar(comp_names, comp_counts, color=["#2196F3"] * 3, edgecolor="white", width=0.35)
for i, v in enumerate(comp_counts):
    ax2.text(i, v + 8, str(v), ha="center", fontweight="bold")
ax2.set_ylabel("Instances")
ax2.set_title("SAT Competition by Year")
ax2.set_ylim(0, max(comp_counts) * 1.18)

plt.tight_layout()
fig.savefig(f"{OUT}/dataset_breakdown.png", dpi=150)
fig.savefig(f"{OUT}/dataset_breakdown.svg")
plt.close()

print(f"Charts saved to {OUT}/")
print(f"  dataset_satlib_counts.png/svg")
print(f"  dataset_satlib_scatter.png/svg")
print(f"  dataset_overview.png/svg")
print(f"  dataset_breakdown.png/svg")
print(
    f"\nSATLIB:  {satlib_total} instances (SAT={sum(s[3] for s in satlib)}, UNSAT={sum(s[4] for s in satlib)})"
)
print(f"SATCOMP: ~{satcomp_total} instances")
print(f"Total:   ~{satlib_total + satcomp_total}")
