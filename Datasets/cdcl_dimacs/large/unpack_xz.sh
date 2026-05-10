#!/bin/bash

# ================= 配置区域 =================
# 基础工作目录
BASE_DIR="/public/home/yhhao/wyf/formal-methods/Datasets/cdcl_dimacs/large"
# 源文件目录（存放 .xz 文件）
DOWNLOADS_DIR="${BASE_DIR}/downloads/2021"
# 目标目录（存放解压后的文件）
CNFS_DIR="${BASE_DIR}/cnfs/2021"
# ===========================================

# 1. 检查源目录是否存在
if [ ! -d "${DOWNLOADS_DIR}" ]; then
    echo "错误：源目录不存在: ${DOWNLOADS_DIR}"
    exit 1
fi

# 2. 创建目标目录（如果不存在）
mkdir -p "${CNFS_DIR}"

# 3. 统计文件数量
xz_count=$(ls -1 "${DOWNLOADS_DIR}"/*.xz 2>/dev/null | wc -l)
if [ "${xz_count}" -eq 0 ]; then
    echo "提示：在 ${DOWNLOADS_DIR} 中未找到 .xz 文件"
    exit 0
fi

echo "找到 ${xz_count} 个 .xz 文件，开始解压..."

# 4. 开启 nullglob 防止无文件时 *.xz 变成字面量
shopt -s nullglob

# 5. 循环解压所有 .xz 文件
for xz_file in "${DOWNLOADS_DIR}"/*.xz; do
    # 获取不带路径和后缀的文件名
    filename=$(basename "${xz_file}" .xz)
    # 目标文件路径
    target_file="${CNFS_DIR}/${filename}"

    # 使用 xz -d -c 解压到标准输出并重定向到目标文件
    # 这样可以直接指定输出路径，且保留原 .xz 文件
    if xz -d -c "${xz_file}" > "${target_file}"; then
        echo "[成功] ${filename}"
    else
        echo "[失败] 解压 ${filename} 时出错"
    fi
done

echo "解压完成。"