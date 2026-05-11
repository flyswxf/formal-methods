import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import numpy as np
import re
import os
import sys
import json

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Logs"))
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({"font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10})


# =====================================================================
# 1. Parse all result.out files
# =====================================================================
def parse_result_out(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    meta = {}
    for key in ["Task Name", "Dataset", "Nodes", "Total Files", "Job ID"]:
        m = re.search(rf"^\s*{key}\s*:\s*(.+)$", text, re.MULTILINE)
        if m:
            val = m.group(1).strip()
            if key in ("Nodes", "Total Files"):
                val = int(val.split()[0]) if val else 0
            meta[key.lower().replace(" ", "_")] = val

    duration = None
    m_time = re.search(r"Timeout\s*:\s*(\d+)", text)
    if m_time:
        meta["timeout"] = int(m_time.group(1))

    # Parse summary stats
    summary = {}
    for k in [
        "Total instances",
        "Both agree",
        "Disagreements",
        "Both timeout",
        "CDCL faster",
        "MiniSat faster",
    ]:
        pat = (
            rf"^\s*{k}\s*:\s*(\d[\d/]*)"
            if "/" not in k
            else rf"^\s*{k}\s*:\s*(\d+)\s*/\s*(\d+)"
        )
        m = re.search(rf"^\s*{re.escape(k)}\s*:\s*(\d[\d/]*)", text, re.MULTILINE)
        if m:
            raw = m.group(1).strip()
            if "/" in raw:
                parts = raw.split("/")
                summary[k.lower().replace(" ", "_")] = (int(parts[0]), int(parts[1]))
            else:
                summary[k.lower().replace(" ", "_")] = int(raw)

    # Parse total times
    for k in ["CDCL total time", "MiniSat total time"]:
        m = re.search(rf"^\s*{re.escape(k)}\s*:\s*([\d.]+)", text, re.MULTILINE)
        if m:
            summary[k.lower().replace(" ", "_")] = float(m.group(1))

    m_sp = re.search(r"Speedup\s*\(MS/CDCL\)\s*:\s*([\d.]+)", text)
    if m_sp:
        summary["speedup_ms_cdcl"] = float(m_sp.group(1))

    # Parse per-instance rows
    instances = []
    table_start = False
    for line in text.split("\n"):
        if "Time MS" in line and "Match" in line:
            table_start = True
            continue
        if table_start:
            if line.startswith("---") or line.startswith("===") or line.strip() == "":
                if instances and (line.startswith("===") or "Summary" in line):
                    break
                continue
            parts = line.split()
            if len(parts) >= 8:
                try:
                    idx = int(parts[0])
                    instance = {
                        "idx": idx,
                        "file": parts[1],
                        "vars": int(parts[2]),
                        "clauses": int(parts[3]),
                        "cdcl_result": parts[4],
                        "minisat_result": parts[5],
                        "cdcl_time_str": parts[6],
                        "minisat_time_str": parts[7],
                        "match": parts[8] if len(parts) > 8 else "N/A",
                    }
                    # Convert time strings to float
                    for key in ["cdcl_time_str", "minisat_time_str"]:
                        ts = instance[key]
                        ts = (
                            ts.replace("ms", "e-3")
                            .replace("us", "e-6")
                            .replace("s", "")
                        )
                        try:
                            instance[key.replace("_str", "")] = float(ts)
                        except:
                            instance[key.replace("_str", "")] = 0.0
                    instances.append(instance)
                except (ValueError, IndexError):
                    pass

    meta["summary"] = summary
    meta["instance_count_parsed"] = len(instances)
    meta["instances"] = instances
    return meta


results = []
for entry in sorted(os.listdir(LOGS_DIR)):
    rpath = os.path.join(LOGS_DIR, entry, "result.out")
    if os.path.isfile(rpath):
        m = parse_result_out(rpath)
        m["dir_name"] = entry
        results.append(m)
        print(
            f"  [{entry}] total={m.get('total_files','?')} instances_parsed={m['instance_count_parsed']}"
        )

print(f"\nParsed {len(results)} result files.\n")

# =====================================================================
# 2. Categorize: SATLIB-medium vs SATCOMP-large
# =====================================================================
satlib_results = [r for r in results if r["dir_name"].startswith("medium-")]
satcomp_results = [r for r in results if r["dir_name"].startswith("large-")]


# =====================================================================
# 3. Build summary tables
# =====================================================================
def build_aggregate(rs):
    total_instances = sum(r.get("total_files", 0) or 0 for r in rs)
    total_agree = sum(r["summary"].get("both_agree", 0) for r in rs)
    total_disagree = sum(r["summary"].get("disagreements", 0) for r in rs)
    total_timeout_both = sum(r["summary"].get("both_timeout", 0) for r in rs)
    cdcl_timeout = sum(
        1 for r in rs for i in r.get("instances", []) if i["cdcl_result"] == "TIMEOUT"
    )
    minisat_timeout = sum(
        1
        for r in rs
        for i in r.get("instances", [])
        if i["minisat_result"] == "TIMEOUT"
    )
    cdcl_total = sum(r["summary"].get("cdcl_total_time", 0.0) for r in rs)
    minisat_total = sum(r["summary"].get("minisat_total_time", 0.0) for r in rs)
    # cdcl_faster / minisat_faster from summary - parse from fractional format
    cdcl_faster = sum(
        (
            r["summary"]["cdcl_faster"][0]
            if isinstance(r["summary"].get("cdcl_faster"), tuple)
            else r["summary"].get("cdcl_faster", 0)
        )
        for r in rs
    )
    minisat_faster = sum(
        (
            r["summary"]["minisat_faster"][0]
            if isinstance(r["summary"].get("minisat_faster"), tuple)
            else r["summary"].get("minisat_faster", 0)
        )
        for r in rs
    )
    solved_both = cdcl_faster + minisat_faster
    return {
        "total_instances": total_instances,
        "total_agree": total_agree,
        "total_disagree": total_disagree,
        "total_timeout_both": total_timeout_both,
        "cdcl_timeout": cdcl_timeout,
        "minisat_timeout": minisat_timeout,
        "cdcl_total_time": cdcl_total,
        "minisat_total_time": minisat_total,
        "cdcl_faster": cdcl_faster,
        "minisat_faster": minisat_faster,
        "solved_both": solved_both,
    }


agg_satlib = build_aggregate(satlib_results)
agg_satcomp = build_aggregate(satcomp_results)
agg_all = build_aggregate(results)


def fmt_time(t):
    if t >= 3600:
        return f"{t/3600:.1f}h"
    elif t >= 60:
        return f"{t/60:.1f}m"
    elif t >= 1:
        return f"{t:.2f}s"
    else:
        return f"{t*1000:.1f}ms"


# =====================================================================
# Chart 1a: Correctness summary bar (Agree / Disagree / Timeout)
# =====================================================================
fig, ax = plt.subplots(figsize=(8, 4.5))
cats = ["SATLIB\n(medium)", "SAT Competition\n(large)", "Overall"]
agree_vals = [
    agg_satlib["total_agree"],
    agg_satcomp["total_agree"],
    agg_all["total_agree"],
]
timeout_vals = [
    agg_satlib["total_timeout_both"],
    agg_satcomp["total_timeout_both"],
    agg_all["total_timeout_both"],
]
n_a_vals = [
    agg_satlib["total_instances"]
    - agg_satlib["total_agree"]
    - agg_satlib["total_timeout_both"]
    - agg_satlib["total_disagree"],
    agg_satcomp["total_instances"]
    - agg_satcomp["total_agree"]
    - agg_satcomp["total_timeout_both"]
    - agg_satcomp["total_disagree"],
    agg_all["total_instances"]
    - agg_all["total_agree"]
    - agg_all["total_timeout_both"]
    - agg_all["total_disagree"],
]
disagree_vals = [
    agg_satlib["total_disagree"],
    agg_satcomp["total_disagree"],
    agg_all["total_disagree"],
]
x = np.arange(len(cats))
w = 0.55
ax.bar(x, agree_vals, width=w, label="Agree", color="#4CAF50", edgecolor="white")
ax.bar(
    x,
    timeout_vals,
    width=w,
    bottom=agree_vals,
    label="Timeouts (N/A)",
    color="#FFC107",
    edgecolor="white",
)
bottom2 = [a + t for a, t in zip(agree_vals, timeout_vals)]
n_a_present = [v for v in n_a_vals if v > 0]
if n_a_present:
    ax.bar(
        x,
        n_a_vals,
        width=w,
        bottom=bottom2,
        label="One-sided Error",
        color="#9E9E9E",
        edgecolor="white",
    )
bottom3 = [b + n for b, n in zip(bottom2, n_a_vals)]
if any(v > 0 for v in disagree_vals):
    ax.bar(
        x,
        disagree_vals,
        width=w,
        bottom=bottom3,
        label="Disagree",
        color="#F44336",
        edgecolor="white",
    )
ax.set_xticks(x)
ax.set_xticklabels(cats)
ax.set_ylabel("Instance Count")
ax.set_title("Correctness: CDCL vs MiniSat")
ax.legend(loc="upper center", fontsize=9)
# Add count labels
for i, (ag, to, na, di) in enumerate(
    zip(agree_vals, timeout_vals, n_a_vals, disagree_vals)
):
    total = ag + to + na + di
    ax.text(
        i, total + total * 0.01, str(total), ha="center", fontweight="bold", fontsize=10
    )
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/result_correctness.png", dpi=150)
fig.savefig(f"{OUT_DIR}/result_correctness.svg")
plt.close()

# =====================================================================
# Chart 1b: Per-benchmark correctness detail (SATLIB)
# =====================================================================
fig, ax = plt.subplots(figsize=(12, 5))
names = [r["dir_name"].replace("medium-", "") for r in satlib_results]
agree_list = [r["summary"].get("both_agree", 0) or 0 for r in satlib_results]
dis_list = [r["summary"].get("disagreements", 0) or 0 for r in satlib_results]
to_list = [r["summary"].get("both_timeout", 0) or 0 for r in satlib_results]
x = np.arange(len(names))
w = 0.6
ax.bar(x, agree_list, width=w, label="Agree", color="#4CAF50", edgecolor="white")
ax.bar(
    x,
    to_list,
    width=w,
    bottom=agree_list,
    label="Timeouts",
    color="#FFC107",
    edgecolor="white",
)
bottom2 = [a + t for a, t in zip(agree_list, to_list)]
if any(v > 0 for v in dis_list):
    ax.bar(
        x,
        dis_list,
        width=w,
        bottom=bottom2,
        label="Disagree",
        color="#F44336",
        edgecolor="white",
    )
ax.set_xticks(x)
ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
ax.set_ylabel("Instances")
ax.set_title("Correctness: SATLIB Per-Benchmark Detail")
ax.legend(fontsize=8)
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/result_correctness_satlib.png", dpi=150)
fig.savefig(f"{OUT_DIR}/result_correctness_satlib.svg")
plt.close()

# =====================================================================
# Chart 2: Performance – speedup per benchmark (bar, SATLIB)
# =====================================================================
fig, ax = plt.subplots(figsize=(12, 5))
names = [r["dir_name"].replace("medium-", "") for r in satlib_results]
speedups = []
for r in satlib_results:
    sp = r["summary"].get("speedup_ms_cdcl", 1.0)
    if sp == 0.0:
        sp = 0.01
    speedups.append(sp)
colors = ["#4CAF50" if s >= 1.0 else "#F44336" for s in speedups]
bars = ax.bar(names, speedups, color=colors, edgecolor="white")
ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1, label="Break-even")
ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
ax.set_ylabel("Speedup (MiniSat / CDCL)")
ax.set_title("Performance: MiniSat vs CDCL Speedup by Benchmark (SATLIB)")
ax.legend(fontsize=9)
for bar, v in zip(bars, speedups):
    ypos = bar.get_height() + 0.02
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        ypos,
        f"{v:.2f}x",
        ha="center",
        fontsize=7,
        fontweight="bold",
        color="#F44336" if v < 1.0 else "#4CAF50",
    )
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/result_speedup_satlib.png", dpi=150)
fig.savefig(f"{OUT_DIR}/result_speedup_satlib.svg")
plt.close()

# =====================================================================
# Chart 3: Performance – scatter CDCL time vs MiniSat time (SATLIB small)
# =====================================================================
fig, ax = plt.subplots(figsize=(7, 6))
all_cdcl_times = []
all_ms_times = []
all_files = []
for r in satlib_results:
    for inst in r.get("instances", []):
        ct = inst.get("cdcl_time", 0.0)
        mt = inst.get("minisat_time", 0.0)
        if ct > 0 and mt > 0 and ct < 5000 and mt < 5000:
            all_cdcl_times.append(ct)
            all_ms_times.append(mt)
            all_files.append(inst["file"])
cdcl_arr = np.array(all_cdcl_times)
ms_arr = np.array(all_ms_times)
max_val = max(cdcl_arr.max(), ms_arr.max()) * 1.1
ax.scatter(ms_arr, cdcl_arr, s=2, alpha=0.3, c="#2196F3")
ax.plot([0.001, max_val], [0.001, max_val], "k--", linewidth=1, label="Equal time")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("MiniSat Time (s)")
ax.set_ylabel("CDCL Time (s)")
ax.set_title(f"SATLIB: CDCL vs MiniSat Per-Instance Time (n={len(cdcl_arr)})")
ax.legend()
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/result_scatter_time.png", dpi=150)
fig.savefig(f"{OUT_DIR}/result_scatter_time.svg")
plt.close()

# =====================================================================
# Chart 4: CDCL timeout rate by variable count (SATLIB)
# =====================================================================
fig, ax = plt.subplots(figsize=(10, 4.5))
bench_names = [r["dir_name"].replace("medium-", "") for r in satlib_results]
cdcl_timeout_pct = []
minisat_timeout_pct = []
for r in satlib_results:
    total = r.get("instance_count_parsed", 1) or 1
    ct = sum(1 for i in r.get("instances", []) if i["cdcl_result"] == "TIMEOUT")
    mt = sum(1 for i in r.get("instances", []) if i["minisat_result"] == "TIMEOUT")
    cdcl_timeout_pct.append(ct / total * 100)
    minisat_timeout_pct.append(mt / total * 100)
x = np.arange(len(bench_names))
w = 0.35
ax.bar(
    x - w / 2,
    cdcl_timeout_pct,
    width=w,
    label="CDCL Timeout %",
    color="#F44336",
    edgecolor="white",
)
ax.bar(
    x + w / 2,
    minisat_timeout_pct,
    width=w,
    label="MiniSat Timeout %",
    color="#2196F3",
    edgecolor="white",
)
ax.set_xticks(x)
ax.set_xticklabels(bench_names, rotation=45, ha="right", fontsize=7)
ax.set_ylabel("Timeout Rate (%)")
ax.set_title("SATLIB: Timeout Rate by Benchmark (5000s limit)")
ax.legend(fontsize=9)
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/result_timeout_rate.png", dpi=150)
fig.savefig(f"{OUT_DIR}/result_timeout_rate.svg")
plt.close()

# =====================================================================
# Generate console report for LaTeX table
# =====================================================================
print("=" * 80)
print("  5.1 Correctness Verification – Console Report")
print("=" * 80)


# Overall summary
def print_cat(name, agg):
    print(f"\n--- {name} ---")
    print(f"  Total instances:     {agg['total_instances']}")
    print(f"  Agree (OK):          {agg['total_agree']}")
    print(f"  Disagree (DIFF):     {agg['total_disagree']}")
    print(f"  Both timeout (N/A):  {agg['total_timeout_both']}")
    print(f"  CDCL timeout:        {agg['cdcl_timeout']}")
    print(f"  MiniSat timeout:     {agg['minisat_timeout']}")
    print(f"  Solved both:         {agg['solved_both']}")
    print(f"  CDCL faster:         {agg['cdcl_faster']}")
    print(f"  MiniSat faster:      {agg['minisat_faster']}")
    print(f"  CDCL total time:     {fmt_time(agg['cdcl_total_time'])}")
    print(f"  MiniSat total time:  {fmt_time(agg['minisat_total_time'])}")
    if agg["minisat_total_time"] > 0 and agg["cdcl_total_time"] > 0:
        print(
            f"  Speedup (MS/CDCL):   {agg['minisat_total_time']/agg['cdcl_total_time']:.2f}x"
        )


print_cat("SATLIB (medium)", agg_satlib)
print_cat("SAT Competition (large)", agg_satcomp)
print_cat("OVERALL", agg_all)

# Per-benchmark SATLIB table
print(
    f"\n{'Name':<32} {'Total':>6} {'Agree':>6} {'Disagree':>8} {'T/O Both':>9} {'CDCL T/O':>9} {'MS T/O':>7} {'MS/CDCL sp':>11}"
)
print("-" * 95)
for r in satlib_results:
    name = r["dir_name"].replace("medium-", "")
    total = r.get("total_files", 0) or 0
    s = r["summary"]
    agree = s.get("both_agree", 0) or 0
    dis = s.get("disagreements", 0) or 0
    to = s.get("both_timeout", 0) or 0
    ct = sum(1 for i in r.get("instances", []) if i["cdcl_result"] == "TIMEOUT")
    mt = sum(1 for i in r.get("instances", []) if i["minisat_result"] == "TIMEOUT")
    sp = s.get("speedup_ms_cdcl", 0)
    print(
        f"{name:<32} {total:>6} {agree:>6} {dis:>8} {to:>9} {ct:>9} {mt:>7} {sp:>11.2f}x"
    )

# Per-benchmark SATCOMP table
print(
    f"\n{'Name':<32} {'Total':>6} {'Agree':>6} {'Disagree':>8} {'T/O Both':>9} {'CDCL T/O':>9} {'MS T/O':>7} {'MS/CDCL sp':>11}"
)
print("-" * 95)
for r in satcomp_results:
    name = r["dir_name"].replace("large-", "SATCOMP-")
    total = r.get("total_files", 0) or 0
    s = r["summary"]
    agree = s.get("both_agree", 0) or 0
    dis = s.get("disagreements", 0) or 0
    to = s.get("both_timeout", 0) or 0
    ct = sum(1 for i in r.get("instances", []) if i["cdcl_result"] == "TIMEOUT")
    mt = sum(1 for i in r.get("instances", []) if i["minisat_result"] == "TIMEOUT")
    sp = s.get("speedup_ms_cdcl", 0)
    print(
        f"{name:<32} {total:>6} {agree:>6} {dis:>8} {to:>9} {ct:>9} {mt:>7} {sp:>11.2f}x"
    )

print(f"\nCharts saved to {OUT_DIR}/")
