#!/bin/bash -l
#SBATCH --job-name=medium-uf20-91-SAT
#SBATCH --nodes=16
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=100G
#SBATCH --time=24:00:00
#SBATCH --output=Logs/info-%j.out

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$PWD}"

JOB_DIR="Logs/${SLURM_JOB_ID}"
mkdir -p "$JOB_DIR"

TASK_NAME="medium-uf20-91-SAT"
DATASET="Datasets/cdcl_dimacs/medium/uf20-91/SAT"

python3 -c "
import json
meta = {
    'job_id': int('${SLURM_JOB_ID}'),
    'task_name': '${TASK_NAME}',
    'dataset': '${DATASET}',
    'cdcl': 'Checkers/cdcl_solver',
    'minisat': 'Baseline/minisat/build/release/bin/minisat',
    'timeout': 5000,
    'nodes': int('${SLURM_NNODES}'),
    'cpus_per_node': 32,
}
with open('${JOB_DIR}/meta.json', 'w') as f:
    json.dump(meta, f, indent=2)
"

module load compiler/gnu/10.2.0

echo "[INFO] job_id=${SLURM_JOB_ID} task=${TASK_NAME} nodes=${SLURM_NNODES} tasks=${SLURM_NTASKS}"
echo "[INFO] dataset=${DATASET}"
echo "[INFO] job_dir=${JOB_DIR}"

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
    --dataset '"$DATASET"' \
    --timeout 5000 \
    --jobs 32 \
    --shard-index "${shard}" \
    --num-shards "${total}" \
    --output "${out_json}" >> "${out_log}" 2>&1
'

mv "Logs/info-${SLURM_JOB_ID}.out" "${JOB_DIR}/info.out"
python3 Utils/merge_shard_results.py --job-id "${SLURM_JOB_ID}" --job-dir "$JOB_DIR"
