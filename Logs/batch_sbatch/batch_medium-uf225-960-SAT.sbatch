#!/bin/bash -l
#SBATCH --job-name=medium-uf225-960-SAT
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=100G
#SBATCH --time=24:00:00
#SBATCH --exclusive
#SBATCH --output=Logs/%j/info.out

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$PWD}"

JOB_DIR="Logs/${SLURM_JOB_ID}"
mkdir -p "$JOB_DIR"

module load compiler/gnu/10.2.0

echo "[INFO] job_id=${SLURM_JOB_ID} nodes=${SLURM_NNODES} tasks=${SLURM_NTASKS}"

# Each SLURM task handles one shard; inside each node we still run 32 local workers.
srun --cpu-bind=cores bash -lc '
  shard="${SLURM_PROCID}"
  total="${SLURM_NTASKS}"
  job_dir="'"$JOB_DIR"'"
  out_json="${job_dir}/shard${shard}.json"
  out_log="${job_dir}/shard${shard}.log"

  echo "[INFO] shard=${shard}/${total} host=$(hostname) log=${out_log}" | tee -a "${out_log}"
  python3 benchmark_compare.py \
    --cdcl Checkers/cdcl_solver \
    --minisat Baseline/minisat/build/release/bin/minisat \
    --dataset Datasets/cdcl_dimacs/medium/uf225-960/SAT \
    --timeout 5000 \
    --jobs 32 \
    --shard-index "${shard}" \
    --num-shards "${total}" \
    --output "${out_json}" >> "${out_log}" 2>&1
'

python3 Utils/merge_shard_results.py --job-id "${SLURM_JOB_ID}" --job-dir "$JOB_DIR"
