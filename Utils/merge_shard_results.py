import argparse
import glob
import json
import os


def format_time(t):
    if t >= 60:
        return f"{t:.1f}s"
    elif t >= 1:
        return f"{t:.3f}s"
    elif t >= 0.001:
        return f"{t*1000:.1f}ms"
    else:
        return f"{t*1000000:.0f}us"


def main():
    parser = argparse.ArgumentParser(
        description="Merge shard benchmark JSON files and log files."
    )
    parser.add_argument(
        "--job-id",
        default=os.environ.get("SLURM_JOB_ID", ""),
        help="SLURM job id (default: $SLURM_JOB_ID)",
    )
    parser.add_argument(
        "--job-dir",
        default=None,
        help="Directory containing shard JSON and log files (default: Logs/<job-id>)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output merged JSON path (default: <job-dir>/detail.json)",
    )
    parser.add_argument(
        "--result",
        default=None,
        help="Output result report path (default: <job-dir>/result.out)",
    )
    args = parser.parse_args()

    if not args.job_id:
        raise SystemExit("Error: missing --job-id and $SLURM_JOB_ID is empty")

    job_dir = args.job_dir or os.path.join("Logs", str(args.job_id))
    os.makedirs(job_dir, exist_ok=True)

    detail_path = args.output or os.path.join(job_dir, "detail.json")
    result_path = args.result or os.path.join(job_dir, "result.out")

    # 1. Merge shard JSON files
    pattern = os.path.join(job_dir, "shard*.json")
    paths = sorted(glob.glob(pattern))
    merged = []
    skipped = []
    for path in paths:
        size = os.path.getsize(path)
        if size == 0:
            print(f"[WARN] Skipping empty shard file: {os.path.basename(path)}")
            skipped.append(path)
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged.extend(data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[WARN] Skipping corrupted shard file {os.path.basename(path)}: {e}")
            skipped.append(path)

    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(
        f"[INFO] merged {len(paths) - len(skipped)} shard files, total records={len(merged)}"
    )
    if skipped:
        print(
            f"[WARN] skipped {len(skipped)} shard file(s): {', '.join(os.path.basename(s) for s in skipped)}"
        )
    print(f"[INFO] detail.json => {detail_path}")

    for path in paths:
        if path in skipped:
            continue
        try:
            os.remove(path)
        except OSError as e:
            print(f"[WARN] Failed to remove {path}: {e}")
    deleted_count = len(paths) - len(skipped)
    if deleted_count:
        print(f"[INFO] Deleted {deleted_count} shard JSON files.")

    # 2. Read meta.json if available
    meta_path = os.path.join(job_dir, "meta.json")
    meta = {}
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass

    # 3. Merge shard log files into result.out
    agree = 0
    disagree = 0
    cdcl_wins = 0
    minisat_wins = 0
    both_timeout = 0
    cdcl_total_time = 0.0
    minisat_total_time = 0.0

    total = len(merged)

    with open(result_path, "w", encoding="utf-8") as out_f:
        out_f.write("=" * 90 + "\n")
        out_f.write("  SAT Solver Benchmark: Merged Results\n")
        out_f.write("=" * 90 + "\n")
        out_f.write(f"  Job ID      : {args.job_id}\n")
        if meta.get("task_name"):
            out_f.write(f"  Task Name   : {meta['task_name']}\n")
        if meta.get("dataset"):
            out_f.write(f"  Dataset     : {meta['dataset']}\n")
        if meta.get("cdcl"):
            out_f.write(f"  CDCL Solver : {meta['cdcl']}\n")
        if meta.get("minisat"):
            out_f.write(f"  MiniSat     : {meta['minisat']}\n")
        if meta.get("timeout"):
            out_f.write(f"  Timeout     : {meta['timeout']}s\n")
        if meta.get("nodes"):
            out_f.write(
                f"  Nodes       : {meta['nodes']}  ({meta.get('cpus_per_node', 32)} cpus/node)\n"
            )
        out_f.write(f"  Total Files : {total}\n")
        out_f.write("=" * 90 + "\n\n")

        header = f"{'#':>3} {'File':<45} {'Vars':>6} {'Cls':>7} {'CDCL':>7} {'MiniSat':>7} {'Time CDCL':>12} {'Time MS':>12} {'Match':>6}"
        out_f.write(header + "\n")
        out_f.write("-" * len(header) + "\n")

        for idx, r in enumerate(merged, 1):
            cdcl_result = r.get("cdcl_result", "ERROR")
            ms_result = r.get("minisat_result", "ERROR")
            cdcl_time = r.get("cdcl_time", 0.0)
            ms_time = r.get("minisat_time", 0.0)
            match_str = r.get("match", "N/A")
            fname = r.get("file", "unknown")

            if len(fname) > 45:
                fname_show = fname[:42] + "..."
            else:
                fname_show = fname

            if cdcl_result not in ("TIMEOUT", "ERROR"):
                cdcl_total_time += cdcl_time
            if ms_result not in ("TIMEOUT", "ERROR"):
                minisat_total_time += ms_time

            if match_str == "OK":
                agree += 1
            elif match_str == "DIFF":
                disagree += 1

            if cdcl_result not in ("TIMEOUT", "ERROR") and ms_result not in (
                "TIMEOUT",
                "ERROR",
            ):
                if cdcl_time < ms_time:
                    cdcl_wins += 1
                elif ms_time < cdcl_time:
                    minisat_wins += 1

            if cdcl_result == "TIMEOUT" and ms_result == "TIMEOUT":
                both_timeout += 1

            out_f.write(
                f"{idx:>3} {fname_show:<45} {r.get('vars', 0):>6} {r.get('clauses', 0):>7} "
                f"{cdcl_result:>7} {ms_result:>7} {format_time(cdcl_time):>12} "
                f"{format_time(ms_time):>12} {match_str:>6}\n"
            )

        solved_both = sum(
            1
            for r in merged
            if r.get("cdcl_result") not in ("TIMEOUT", "ERROR")
            and r.get("minisat_result") not in ("TIMEOUT", "ERROR")
        )

        out_f.write(f"\n{'='*90}\n")
        out_f.write(f"  Summary\n")
        out_f.write(f"{'='*90}\n")
        out_f.write(f"  Total instances       : {total}\n")
        out_f.write(f"  Both agree            : {agree}\n")
        out_f.write(f"  Disagreements         : {disagree}\n")
        out_f.write(f"  Both timeout          : {both_timeout}\n")
        out_f.write(f"  CDCL faster           : {cdcl_wins} / {solved_both}\n")
        out_f.write(f"  MiniSat faster        : {minisat_wins} / {solved_both}\n")
        out_f.write(f"  CDCL total time       : {format_time(cdcl_total_time)}\n")
        out_f.write(f"  MiniSat total time    : {format_time(minisat_total_time)}\n")
        if minisat_total_time > 0:
            speedup = (
                minisat_total_time / cdcl_total_time
                if cdcl_total_time > 0
                else float("inf")
            )
            out_f.write(f"  Speedup (MS/CDCL)     : {speedup:.2f}x\n")
        out_f.write(f"{'='*90}\n")

        if disagree > 0:
            out_f.write(f"\n  !! DISAGREEMENTS (need investigation):\n")
            for r in merged:
                if r.get("match") == "DIFF":
                    out_f.write(
                        f"     {r.get('file')}: CDCL={r.get('cdcl_result')} vs MiniSat={r.get('minisat_result')}\n"
                    )

    print(f"[INFO] result.out => {result_path}")

    # 3. Delete shard log files
    log_pattern = os.path.join(job_dir, "shard*.log")
    log_paths = sorted(glob.glob(log_pattern))
    for path in log_paths:
        try:
            os.remove(path)
        except OSError as e:
            print(f"[WARN] Failed to remove {path}: {e}")
    if log_paths:
        print(f"[INFO] Deleted {len(log_paths)} shard log files.")


if __name__ == "__main__":
    main()
