#!/bin/bash
set -euo pipefail

usage() {
    echo "Usage: $0 [--serial] [--max-nodes N]"
    echo ""
    echo "  --serial       Submit jobs with SLURM dependency chain (one at a time)."
    echo "                 Without this flag, all jobs are submitted at once."
    echo "  --max-nodes N  Override max nodes per job (default: 16)"
    echo ""
}

SERIAL=false
MAX_NODES=16

while [[ $# -gt 0 ]]; do
    case "$1" in
        --serial)
            SERIAL=true
            shift
            ;;
        --max-nodes)
            MAX_NODES="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$PROJECT_DIR/run_cdcl_bench_multinode.sbatch"
TMP_DIR="$PROJECT_DIR/Logs/batch_sbatch"
mkdir -p "$PROJECT_DIR/Logs" "$TMP_DIR"

CORES_PER_NODE=32

# ============================================================
# Task definitions: "task_name|cnf_relative_path"
# Add or remove tasks here as needed.
# ============================================================
TASKS=(
    "large-2023|Datasets/cdcl_dimacs/large/cnfs/2023"
    "large-2022|Datasets/cdcl_dimacs/large/cnfs/2022"
    "large-2021|Datasets/cdcl_dimacs/large/cnfs/2021"
    "medium-uf20-91-SAT|Datasets/cdcl_dimacs/medium/uf20-91/SAT"
    "medium-uf50-218-SAT|Datasets/cdcl_dimacs/medium/uf50-218/SAT"
    "medium-uf50-218-UNSAT|Datasets/cdcl_dimacs/medium/uf50-218/UNSAT"
    "medium-uf75-325-SAT|Datasets/cdcl_dimacs/medium/uf75-325/SAT"
    "medium-uf75-325-UNSAT|Datasets/cdcl_dimacs/medium/uf75-325/UNSAT"
    "medium-uf100-430-SAT|Datasets/cdcl_dimacs/medium/uf100-430/SAT"
    "medium-uf100-430-UNSAT|Datasets/cdcl_dimacs/medium/uf100-430/UNSAT"
    "medium-uf125-538-SAT|Datasets/cdcl_dimacs/medium/uf125-538/SAT"
    "medium-uf125-538-UNSAT|Datasets/cdcl_dimacs/medium/uf125-538/UNSAT"
    "medium-uf150-645-SAT|Datasets/cdcl_dimacs/medium/uf150-645/SAT"
    "medium-uf150-645-UNSAT|Datasets/cdcl_dimacs/medium/uf150-645/UNSAT"
    "medium-uf175-753-SAT|Datasets/cdcl_dimacs/medium/uf175-753/SAT"
    "medium-uf175-753-UNSAT|Datasets/cdcl_dimacs/medium/uf175-753/UNSAT"
    "medium-uf200-860-SAT|Datasets/cdcl_dimacs/medium/uf200-860/SAT"
    "medium-uf200-860-UNSAT|Datasets/cdcl_dimacs/medium/uf200-860/UNSAT"
    "medium-uf225-960-SAT|Datasets/cdcl_dimacs/medium/uf225-960/SAT"
    "medium-uf225-960-UNSAT|Datasets/cdcl_dimacs/medium/uf225-960/UNSAT"
    "medium-uf250-1065-SAT|Datasets/cdcl_dimacs/medium/uf250-1065/SAT"
    "medium-uf250-1065-UNSAT|Datasets/cdcl_dimacs/medium/uf250-1065/UNSAT"
)

if [ ! -f "$TEMPLATE" ]; then
    echo "Error: sbatch template not found: $TEMPLATE" >&2
    exit 1
fi

echo "=== Batch Benchmark Submission ==="
echo "Template : $TEMPLATE"
echo "Project  : $PROJECT_DIR"
echo "Serial   : $SERIAL"
echo "Max nodes: $MAX_NODES"
echo ""

submitted=0
skipped=0
prev_jobid=""

for task in "${TASKS[@]}"; do
    IFS='|' read -r name cnf_rel <<< "$task"
    cnf_dir="$PROJECT_DIR/$cnf_rel"

    if [ ! -d "$cnf_dir" ]; then
        echo "[SKIP] $name -> directory not found: $cnf_rel"
        skipped=$((skipped + 1))
        continue
    fi

    num_files=$(find "$cnf_dir" -maxdepth 1 -name "*.cnf" -type f 2>/dev/null | wc -l)
    if [ "$num_files" -eq 0 ]; then
        echo "[SKIP] $name -> no .cnf files in $cnf_rel"
        skipped=$((skipped + 1))
        continue
    fi

    nodes=$(( (num_files + CORES_PER_NODE - 1) / CORES_PER_NODE ))
    if [ "$nodes" -gt "$MAX_NODES" ]; then
        nodes=$MAX_NODES
    fi
    total_shards=$(( nodes * CORES_PER_NODE ))

    echo "[$submitted] $name"
    echo "    cnf_dir    : $cnf_rel"
    echo "    .cnf files : $num_files"
    echo "    nodes      : $nodes  (shards: $total_shards)"

    tmp_sbatch="$TMP_DIR/batch_${name}.sbatch"

    sed \
        -e "s|^#SBATCH --job-name=cdcl-bench-mn$|#SBATCH --job-name=${name}|" \
        -e "s|^#SBATCH --nodes=16$|#SBATCH --nodes=${nodes}|" \
        -e "s|^TASK_NAME=\"cdcl-bench-mn\"$|TASK_NAME=\"${name}\"|" \
        -e "s|^DATASET=\"Datasets/cdcl_dimacs/large/cnfs\"$|DATASET=\"${cnf_rel}\"|" \
        -e "s|--dataset Datasets/cdcl_dimacs/large/cnfs|--dataset ${cnf_rel}|" \
        "$TEMPLATE" > "$tmp_sbatch"

    if [ "$SERIAL" = true ] && [ -n "$prev_jobid" ]; then
        echo "    dependency : afterany:$prev_jobid"
        output=$(sbatch --dependency="afterany:$prev_jobid" "$tmp_sbatch")
    else
        output=$(sbatch "$tmp_sbatch")
    fi

    jobid=$(echo "$output" | grep -oP '\d+$')
    echo "    submitted  : jobid=$jobid"
    prev_jobid="$jobid"
    submitted=$((submitted + 1))
    echo ""
done

echo "=== Summary ==="
echo "Submitted : $submitted"
echo "Skipped   : $skipped"
echo "Mode      : $( [ "$SERIAL" = true ] && echo "serial (dependency chain)" || echo "parallel" )"
echo "Done."
