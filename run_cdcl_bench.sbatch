#!/bin/bash -l
#SBATCH --job-name=cdcl-bench
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=100G
#SBATCH --time=4:00:00
#SBATCH --exclusive
#SBATCH --output=Logs/cdcl-bench-%j.out

# set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$PWD}"
mkdir -p Logs

# module load compiler/gnu/10.2.0

python3 benchmark_compare.py \
  --cdcl Checkers/cdcl_solver \
  --minisat Baseline/minisat/build/release/bin/minisat \
  --dataset Datasets/cdcl_dimacs/large/cnfs \
  --timeout 5000 \
  --jobs 32 \
  --output bench_results_5000.json
