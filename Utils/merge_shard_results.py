import argparse
import glob
import json
import os


def main():
    parser = argparse.ArgumentParser(
        description="Merge shard benchmark JSON files into one JSON file."
    )
    parser.add_argument(
        "--job-id",
        default=os.environ.get("SLURM_JOB_ID", ""),
        help="SLURM job id used in shard file names (default: $SLURM_JOB_ID)",
    )
    parser.add_argument(
        "--input-dir",
        default="shard_results",
        help="Directory containing shard JSON files (default: shard_results)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output merged JSON path (default: bench_results_<jobid>_merged.json)",
    )
    args = parser.parse_args()

    if not args.job_id:
        raise SystemExit("Error: missing --job-id and $SLURM_JOB_ID is empty")

    pattern = os.path.join(args.input_dir, f"bench_{args.job_id}_shard*.json")
    paths = sorted(glob.glob(pattern))
    merged = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            merged.extend(json.load(f))

    out_path = args.output or f"bench_results_{args.job_id}_merged.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"[INFO] merged {len(paths)} shard files, total records={len(merged)}")
    print(f"[INFO] merged json => {out_path}")


if __name__ == "__main__":
    main()
