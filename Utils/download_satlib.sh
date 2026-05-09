#!/bin/bash
set -e

BASE_URL="https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT"
OUT_DIR="$(cd "$(dirname "$0")/../Datasets/cdcl_dimacs/medium" && pwd)"

NAMES=(   "uf20-91"   "uf50-218"   "uf75-325"   "uf100-430"   "uf125-538"   "uf150-645"   "uf175-753"   "uf200-860"   "uf225-960"   "uf250-1065")
SAT=(     "uf20-91"   "uf50-218"   "uf75-325"   "uf100-430"   "uf125-538"   "uf150-645"   "uf175-753"   "uf200-860"   "uf225-960"   "uf250-1065")
UNSAT=(   ""          "uuf50-218"  "uuf75-325"  "uuf100-430"  "uuf125-538"  "uuf150-645"  "uuf175-753"  "uuf200-860"  "uuf225-960"  "uuf250-1065")
DESCS=(
    "20 vars, 91 clauses, 1000 instances"
    "50 vars, 218 clauses, 1000 instances"
    "75 vars, 325 clauses, 100 instances"
    "100 vars, 430 clauses, 1000 instances"
    "125 vars, 538 clauses, 100 instances"
    "150 vars, 645 clauses, 100 instances"
    "175 vars, 753 clauses, 100 instances"
    "200 vars, 860 clauses, 100 instances"
    "225 vars, 960 clauses, 100 instances"
    "250 vars, 1065 clauses, 100 instances"
)

echo "=== SATLIB Uniform Random-3-SAT Downloader ==="
echo "Output dir: $OUT_DIR"
echo ""

TOTAL=${#NAMES[@]}
downloaded=0
skipped=0
extracted=0

for ((i = 0; i < TOTAL; i++)); do
    name="${NAMES[$i]}"
    idx=$((i + 1))
    echo "--- [$idx/$TOTAL] ${name} : ${DESCS[$i]} ---"

    bench_dir="$OUT_DIR/$name"
    mkdir -p "$bench_dir"

    # SAT archives
    archives_sat="${SAT[$i]}"
    archives_unsat="${UNSAT[$i]}"

    for slot in 1 2; do
        if [ "$slot" -eq 1 ]; then
            arch="$archives_sat"
            subdir="SAT"
        else
            arch="$archives_unsat"
            subdir="UNSAT"
        fi

        if [ -z "$arch" ]; then
            continue
        fi

        archive="${arch}.tar.gz"
        url="$BASE_URL/$archive"
        local_file="$bench_dir/$archive"
        target_dir="$bench_dir/$subdir"

        mkdir -p "$target_dir"

        marker_file="$target_dir/.extracted"

        if [ -f "$marker_file" ] && [ "$(cat "$marker_file")" = "done" ]; then
            echo "  [$subdir] Already extracted, skipping."
            skipped=$((skipped + 1))
            continue
        fi

        if [ -f "$local_file" ]; then
            echo "  [$subdir] Archive already exists: $local_file, skipping download."
        else
            echo "  [$subdir] Downloading: $url"
            wget -c -O "$local_file" "$url"
            if [ $? -ne 0 ]; then
                echo "  [$subdir] WARNING: wget failed for $url" >&2
                continue
            fi
            downloaded=$((downloaded + 1))
        fi

        echo "  [$subdir] Extracting to: $target_dir"
        tar -xzf "$local_file" -C "$target_dir"
        if [ $? -ne 0 ]; then
            echo "  [$subdir] WARNING: tar extraction failed for $local_file" >&2
            continue
        fi

        echo "done" > "$marker_file"
        extracted=$((extracted + 1))
        echo "  [$subdir] Done."
    done

    echo ""
done

echo "=== Summary ==="
echo "Benchmarks processed: $TOTAL"
echo "Archives downloaded: $downloaded"
echo "Archives extracted: $extracted"
echo "Skipped (already extracted): $skipped"
echo ""
echo "Done!"
