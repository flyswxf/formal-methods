#!/bin/bash -l
#SBATCH --job-name=cdcl-bench-mn
#SBATCH --nodes=16
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=100G
#SBATCH --time=24:00:00
#SBATCH --exclusive
#SBATCH --output=Logs/cdcl-bench-mn-%j.out

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$PWD}"
mkdir -p Logs shard_results

module load compiler/gnu/10.2.0
export PYTHONUNBUFFERED=1

echo "[INFO] job_id=${SLURM_JOB_ID} nodes=${SLURM_NNODES} tasks=${SLURM_NTASKS}"

# Each SLURM task handles one shard; inside each node we still run 32 local workers.
srun --cpu-bind=cores bash -lc '
  shard="${SLURM_PROCID}"
  total="${SLURM_NTASKS}"
  out_json="shard_results/bench_${SLURM_JOB_ID}_shard${shard}.json"
  out_log="Logs/bench_${SLURM_JOB_ID}_shard${shard}.out"

  echo "[INFO] shard=${shard}/${total} host=$(hostname) log=${out_log}" | tee -a "${out_log}"
  python3 -u benchmark_compare.py \
    --cdcl Checkers/cdcl_solver \
    --minisat Baseline/minisat/build/release/bin/minisat \
    --dataset Datasets/cdcl_dimacs/large/cnfs \
    --timeout 5000 \
    --jobs 32 \
    --shard-index "${shard}" \
    --num-shards "${total}" \
    --output "${out_json}" >> "${out_log}" 2>&1
'

python3 - << 'PY'
import glob
import json
import os

job_id = os.environ.get("SLURM_JOB_ID", "")
paths = sorted(glob.glob(f"shard_results/bench_{job_id}_shard*.json"))
merged = []
for p in paths:
    with open(p, "r", encoding="utf-8") as f:
        merged.extend(json.load(f))

out_path = f"bench_results_{job_id}_merged.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

print(f"[INFO] merged {len(paths)} shard files, total records={len(merged)}")
print(f"[INFO] merged json => {out_path}")
PY
