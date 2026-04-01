#!/bin/bash
# 最终完整工具 - 正确的寄存器追踪和分支标记

LITMUS_FILE="${1:-test_sb_fence_tso.litmus}"
MODEL="${2:-promising}"
NUM_PATHS="${3:-5}"

if [ ! -f "$LITMUS_FILE" ]; then
    echo "错误: 文件 $LITMUS_FILE 不存在"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================================================"
echo "🎯 rmem Complete Path Analysis - Final Version"
echo "======================================================================================================"
echo ""

python3 path_with_branches.py "$LITMUS_FILE" "$MODEL" "$NUM_PATHS"

echo ""
echo "======================================================================================================"
echo "✅ 分析完成"
echo "======================================================================================================"
echo ""
echo "说明:"
echo "  • Branch 列显示分支标记 (a, b, c...)，相同位置不同执行显示不同分支"
echo "  • Register Changes 显示该步骤的寄存器变化"
echo "  • Memory Changes 显示内存操作 (Store/Load)"
echo ""
