import argparse
import subprocess
import sys
import os
import time
import glob
import tempfile
import json
from concurrent.futures import ProcessPoolExecutor, as_completed


def run_cdcl_solver(exe_path, cnf_path, timeout):
    cmd = [exe_path, cnf_path]
    try:
        start = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        elapsed = time.perf_counter() - start
        output = proc.stdout.decode("utf-8", errors="replace").strip()
        if output.startswith("SAT"):
            result = "SAT"
        elif output.startswith("UNSAT"):
            result = "UNSAT"
        else:
            result = f"ERROR({output[:80]})"
        return result, elapsed, None
    except subprocess.TimeoutExpired:
        return "TIMEOUT", timeout, None
    except Exception as e:
        return "ERROR", 0.0, str(e)


def run_minisat(exe_path, cnf_path, timeout):
    tmp_out = tempfile.mktemp(suffix=".txt")
    env = os.environ.copy()
    strawberry_bin = r"D:\strawberry\c\bin"
    if strawberry_bin not in env.get("PATH", ""):
        env["PATH"] = strawberry_bin + ";" + env.get("PATH", "")
    cmd = [exe_path, cnf_path, tmp_out]
    try:
        start = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env)
        elapsed = time.perf_counter() - start
        exit_code = proc.returncode
        if exit_code == 10:
            result = "SAT"
        elif exit_code == 20:
            result = "UNSAT"
        else:
            stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()[:80]
            result = f"ERROR(exit={exit_code},{stderr_text})"
        return result, elapsed, None
    except subprocess.TimeoutExpired:
        return "TIMEOUT", timeout, None
    except Exception as e:
        return "ERROR", 0.0, str(e)
    finally:
        if os.path.exists(tmp_out):
            try:
                os.remove(tmp_out)
            except OSError:
                pass


def parse_dimacs_header(cnf_path):
    try:
        with open(cnf_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("p cnf"):
                    parts = line.split()
                    return int(parts[2]), int(parts[3])
    except Exception:
        pass
    return -1, -1


def format_time(t):
    if t >= 60:
        return f"{t:.1f}s"
    elif t >= 1:
        return f"{t:.3f}s"
    elif t >= 0.001:
        return f"{t*1000:.1f}ms"
    else:
        return f"{t*1000000:.0f}us"


def run_benchmark(cdcl_exe, minisat_exe, cnf_dir, timeout, output_json=None):
    cnf_files = sorted(glob.glob(os.path.join(cnf_dir, "*.cnf")))
    if not cnf_files:
        print(f"Error: No .cnf files found in {cnf_dir}")
        sys.exit(1)

    print(f"{'='*90}")
    print(f"  SAT Solver Benchmark: CDCLSolver vs MiniSat")
    print(f"{'='*90}")
    print(f"  CDCL Solver : {cdcl_exe}")
    print(f"  MiniSat     : {minisat_exe}")
    print(f"  Dataset     : {cnf_dir} ({len(cnf_files)} files)")
    print(f"  Timeout     : {timeout}s")
    print(f"{'='*90}\n")

    results = []
    agree = 0
    disagree = 0
    cdcl_wins = 0
    minisat_wins = 0
    both_timeout = 0
    cdcl_total_time = 0.0
    minisat_total_time = 0.0

    header = f"{'#':>3} {'File':<45} {'Vars':>6} {'Cls':>7} {'CDCL':>7} {'MiniSat':>7} {'Time CDCL':>12} {'Time MS':>12} {'Match':>6}"
    print(header)
    print("-" * len(header))

    for idx, cnf_path in enumerate(cnf_files, 1):
        fname = os.path.basename(cnf_path)
        if len(fname) > 45:
            fname = fname[:42] + "..."
        n_vars, n_cls = parse_dimacs_header(cnf_path)

        cdcl_result, cdcl_time, cdcl_err = run_cdcl_solver(cdcl_exe, cnf_path, timeout)
        ms_result, ms_time, ms_err = run_minisat(minisat_exe, cnf_path, timeout)

        if cdcl_result not in ("TIMEOUT", "ERROR"):
            cdcl_total_time += cdcl_time
        if ms_result not in ("TIMEOUT", "ERROR"):
            minisat_total_time += ms_time

        if cdcl_result == ms_result:
            match_str = "OK"
            agree += 1
        elif cdcl_result in ("TIMEOUT", "ERROR") or ms_result in ("TIMEOUT", "ERROR"):
            match_str = "N/A"
        else:
            match_str = "DIFF"
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

        print(
            f"{idx:>3} {fname:<45} {n_vars:>6} {n_cls:>7} {cdcl_result:>7} {ms_result:>7} {format_time(cdcl_time):>12} {format_time(ms_time):>12} {match_str:>6}"
        )

        results.append(
            {
                "file": os.path.basename(cnf_path),
                "vars": n_vars,
                "clauses": n_cls,
                "cdcl_result": cdcl_result,
                "cdcl_time": round(cdcl_time, 4),
                "cdcl_error": cdcl_err,
                "minisat_result": ms_result,
                "minisat_time": round(ms_time, 4),
                "minisat_error": ms_err,
                "match": match_str,
            }
        )

    total = len(results)
    solved_both = sum(
        1
        for r in results
        if r["cdcl_result"] not in ("TIMEOUT", "ERROR")
        and r["minisat_result"] not in ("TIMEOUT", "ERROR")
    )

    print(f"\n{'='*90}")
    print(f"  Summary")
    print(f"{'='*90}")
    print(f"  Total instances       : {total}")
    print(f"  Both agree            : {agree}")
    print(f"  Disagreements         : {disagree}")
    print(f"  Both timeout          : {both_timeout}")
    print(f"  CDCL faster           : {cdcl_wins} / {solved_both}")
    print(f"  MiniSat faster        : {minisat_wins} / {solved_both}")
    print(f"  CDCL total time       : {format_time(cdcl_total_time)}")
    print(f"  MiniSat total time    : {format_time(minisat_total_time)}")
    if minisat_total_time > 0:
        speedup = (
            minisat_total_time / cdcl_total_time
            if cdcl_total_time > 0
            else float("inf")
        )
        print(f"  Speedup (MS/CDCL)     : {speedup:.2f}x")
    print(f"{'='*90}")

    if disagree > 0:
        print(f"\n  !! DISAGREEMENTS (need investigation):")
        for r in results:
            if r["match"] == "DIFF":
                print(
                    f"     {r['file']}: CDCL={r['cdcl_result']} vs MiniSat={r['minisat_result']}"
                )

    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n  Results saved to: {output_json}")

    return results


def run_one_instance(idx, cnf_path, cdcl_exe, minisat_exe, timeout):
    fname = os.path.basename(cnf_path)
    n_vars, n_cls = parse_dimacs_header(cnf_path)
    cdcl_result, cdcl_time, cdcl_err = run_cdcl_solver(cdcl_exe, cnf_path, timeout)
    ms_result, ms_time, ms_err = run_minisat(minisat_exe, cnf_path, timeout)

    if len(fname) > 45:
        fname_show = fname[:42] + "..."
    else:
        fname_show = fname

    if cdcl_result in ("TIMEOUT", "ERROR") or ms_result in ("TIMEOUT", "ERROR"):
        match_str = "N/A"
    elif cdcl_result == ms_result:
        match_str = "OK"
    else:
        match_str = "DIFF"

    return {
        "idx": idx,
        "file": fname,
        "file_show": fname_show,
        "vars": n_vars,
        "clauses": n_cls,
        "cdcl_result": cdcl_result,
        "cdcl_time": cdcl_time,
        "cdcl_error": cdcl_err,
        "minisat_result": ms_result,
        "minisat_time": ms_time,
        "minisat_error": ms_err,
        "match": match_str,
    }


def run_benchmark_parallel(
    cdcl_exe, minisat_exe, cnf_dir, timeout, jobs, output_json=None
):
    cnf_files = sorted(glob.glob(os.path.join(cnf_dir, "*.cnf")))
    if not cnf_files:
        print(f"Error: No .cnf files found in {cnf_dir}")
        sys.exit(1)

    if jobs <= 0:
        jobs = os.cpu_count() or 1
    jobs = min(jobs, len(cnf_files))

    print(f"{'='*90}")
    print(f"  SAT Solver Benchmark: CDCLSolver vs MiniSat (Parallel)")
    print(f"{'='*90}")
    print(f"  CDCL Solver : {cdcl_exe}")
    print(f"  MiniSat     : {minisat_exe}")
    print(f"  Dataset     : {cnf_dir} ({len(cnf_files)} files)")
    print(f"  Timeout     : {timeout}s")
    print(f"  Workers     : {jobs}")
    print(f"{'='*90}\n")

    print(f"[INFO] Submitting {len(cnf_files)} instances ...")
    agree = 0
    disagree = 0
    cdcl_wins = 0
    minisat_wins = 0
    both_timeout = 0
    cdcl_total_time = 0.0
    minisat_total_time = 0.0

    header = f"{'#':>3} {'File':<45} {'Vars':>6} {'Cls':>7} {'CDCL':>7} {'MiniSat':>7} {'Time CDCL':>12} {'Time MS':>12} {'Match':>6}"
    print(header)
    print("-" * len(header))

    final_results = []
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futures = [
            ex.submit(run_one_instance, idx, path, cdcl_exe, minisat_exe, timeout)
            for idx, path in enumerate(cnf_files, 1)
        ]
        done_count = 0
        for fut in as_completed(futures):
            r = fut.result()
            done_count += 1
            cdcl_result = r["cdcl_result"]
            ms_result = r["minisat_result"]
            cdcl_time = r["cdcl_time"]
            ms_time = r["minisat_time"]
            match_str = r["match"]

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

            print(
                f"{r['idx']:>3} {r['file_show']:<45} {r['vars']:>6} {r['clauses']:>7} "
                f"{cdcl_result:>7} {ms_result:>7} {format_time(cdcl_time):>12} "
                f"{format_time(ms_time):>12} {match_str:>6}"
            )
            if done_count % 10 == 0 or done_count == len(futures):
                print(f"[INFO] Completed {done_count}/{len(futures)}")

            final_results.append(
                {
                    "file": r["file"],
                    "vars": r["vars"],
                    "clauses": r["clauses"],
                    "cdcl_result": cdcl_result,
                    "cdcl_time": round(cdcl_time, 4),
                    "cdcl_error": r["cdcl_error"],
                    "minisat_result": ms_result,
                    "minisat_time": round(ms_time, 4),
                    "minisat_error": r["minisat_error"],
                    "match": match_str,
                }
            )

    total = len(final_results)
    solved_both = sum(
        1
        for r in final_results
        if r["cdcl_result"] not in ("TIMEOUT", "ERROR")
        and r["minisat_result"] not in ("TIMEOUT", "ERROR")
    )

    print(f"\n{'='*90}")
    print(f"  Summary")
    print(f"{'='*90}")
    print(f"  Total instances       : {total}")
    print(f"  Both agree            : {agree}")
    print(f"  Disagreements         : {disagree}")
    print(f"  Both timeout          : {both_timeout}")
    print(f"  CDCL faster           : {cdcl_wins} / {solved_both}")
    print(f"  MiniSat faster        : {minisat_wins} / {solved_both}")
    print(f"  CDCL total time       : {format_time(cdcl_total_time)}")
    print(f"  MiniSat total time    : {format_time(minisat_total_time)}")
    if minisat_total_time > 0:
        speedup = (
            minisat_total_time / cdcl_total_time
            if cdcl_total_time > 0
            else float("inf")
        )
        print(f"  Speedup (MS/CDCL)     : {speedup:.2f}x")
    print(f"{'='*90}")

    if disagree > 0:
        print(f"\n  !! DISAGREEMENTS (need investigation):")
        for r in final_results:
            if r["match"] == "DIFF":
                print(
                    f"     {r['file']}: CDCL={r['cdcl_result']} vs MiniSat={r['minisat_result']}"
                )

    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        print(f"\n  Results saved to: {output_json}")

    return final_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SAT Solver Benchmark: CDCLSolver vs MiniSat"
    )
    parser.add_argument("--cdcl", required=True, help="Path to cdcl_solver.exe")
    parser.add_argument("--minisat", required=True, help="Path to minisat.exe")
    parser.add_argument(
        "--dataset", required=True, help="Directory containing .cnf files"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per instance in seconds (default: 300)",
    )
    parser.add_argument("--output", help="Save results to JSON file")
    parser.add_argument(
        "--jobs",
        type=int,
        default=0,
        help="Parallel workers. Use 0 for all available CPU cores (default: 0)",
    )
    args = parser.parse_args()
    if args.jobs == 1:
        run_benchmark(args.cdcl, args.minisat, args.dataset, args.timeout, args.output)
    else:
        run_benchmark_parallel(
            args.cdcl,
            args.minisat,
            args.dataset,
            args.timeout,
            args.jobs,
            args.output,
        )
