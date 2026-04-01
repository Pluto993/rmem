# rmem 寄存器变化分析工具

基于 rmem RISC-V 内存模型模拟器的执行路径分析工具集。

## 🚀 快速开始

```bash
# 运行完整路径分析 (推荐)
./final_analysis.sh test_sb_fence_tso.litmus promising 5
```

---

## 📦 工具列表

### 1. **完整路径分析** (推荐使用) ⭐

**命令:**
```bash
./final_analysis.sh <litmus_file> [model] [num_paths]
```

**示例:**
```bash
./final_analysis.sh test_sb_fence_tso.litmus promising 5
```

**输出特点:**
- ✅ 每一步独立表格显示
- ✅ 分支标记 (Step 1a, 2a, 3b...)
- ✅ 完整寄存器变化追踪 (X5: 0 → 1)
- ✅ 内存操作标记 (Store/Load)
- ✅ 最终状态标识 (违例/正常)

**输出格式:**
```
路径 #1
最终状态: ❌ VIOLATION - 0:x7=0; 1:x7=0;

Step 1a: Core0 executes li X5, 1
┌───────────────┬─────────────┬─────────────────────────────────┬──────────────────────┬──────────────────────┐
│ Step          │ Branch      │ Instruction                     │ Register Changes     │ Memory Changes       │
├───────────────┼─────────────┼─────────────────────────────────┼──────────────────────┼──────────────────────┤
│ 1a            │ a           │ li X5, 1                        │ X5: 0 → 1            │ -                    │
└───────────────┴─────────────┴─────────────────────────────────┴──────────────────────┴──────────────────────┘
```

---

### 2. **路径统计分析**

**命令:**
```bash
./rmem -model promising -interactive false -random_traces 100 <litmus_file> | python3 analyze_paths.py
```

**示例:**
```bash
./rmem -model promising -interactive false -random_traces 100 test_sb_fence_tso.litmus | python3 analyze_paths.py
```

**输出特点:**
- 唯一路径统计
- 违例路径识别
- 路径执行树状图 (可选)
- Via 路径标识

---

### 3. **单次执行紧凑表格**

**命令:**
```bash
./rmem -model promising -interactive false -debug -random_traces 1 <litmus_file> 2>&1 | python3 filter_register_changes.py
```

**示例:**
```bash
./rmem -model promising -interactive false -debug -random_traces 1 test_sb_fence_tso.litmus 2>&1 | python3 filter_register_changes.py
```

**输出特点:**
- 紧凑的单表格格式
- 快速查看单次执行
- 按步骤编号显示

---

## 📊 输出说明

### 表格列说明

| 列名 | 说明 |
|------|------|
| **Step** | 执行步骤编号 (带分支标记,如 1a, 2b) |
| **Branch** | 分支标识 (a/b/c 或 - 表示无分支) |
| **Instruction** | 规范化的 RISC-V 指令 |
| **Register Changes** | 寄存器变化 (格式: X5: 0 → 1) |
| **Memory Changes** | 内存操作类型 (Store/Load/-) |

### 分支标记

- **`-`**: 无分支,所有路径在此步骤执行相同指令
- **`a`, `b`, `c`...**: 分支标识,表示不同路径在相同位置执行了不同指令或顺序

### 最终状态

- **`✅ OK`**: 正常执行,满足内存一致性
- **`❌ VIOLATION`**: 违例,发现弱内存可见性问题

---

## 🔧 工具文件

| 文件名 | 功能 | 类型 |
|--------|------|------|
| `final_analysis.sh` | 主入口脚本 | Shell |
| `path_with_branches.py` | 分支检测和详细步骤追踪 | Python |
| `filter_register_changes.py` | 单次执行紧凑表格 | Python |
| `analyze_paths.py` | 路径统计和树状图 | Python |
| `show_paths.py` | 简单路径列表 | Python |

---

## 📝 测试文件

仓库包含以下 litmus 测试文件:
- `test_sb_fence_tso.litmus` - Store Buffering with fence.tso
- `test_sb_tso.litmus` - 基础 TSO 模型测试
- `test_sb_rvwmo.litmus` - RISC-V 弱内存模型测试
- `test_sb_tso_v2.litmus` - TSO 变体测试

---

## 💡 使用技巧

### 1. 收集更多路径
```bash
./final_analysis.sh test.litmus promising 10  # 收集 10 条路径
```

### 2. 只查看违例路径
```bash
./rmem -model promising -interactive false -random_traces 100 test.litmus | \
  python3 analyze_paths.py | grep -A 5 "VIOLATION"
```

### 3. 导出结果
```bash
./final_analysis.sh test.litmus promising 5 > result.txt
```

### 4. 比较不同内存模型
```bash
./final_analysis.sh test.litmus tso 5        # TSO 模型
./final_analysis.sh test.litmus promising 5  # Promising 模型
```

---

## 🐛 故障排除

### 问题 1: opam 环境未激活

**错误信息:**
```
rmem: command not found
```

**解决方法:**
```bash
eval $(opam env --switch=opam-4.11.2-for-rmem)
```

### 问题 2: 寄存器变化不完整

**原因:** 某些中间步骤的寄存器状态未更新

**解决:** `path_with_branches.py` 已优化寄存器追踪逻辑

### 问题 3: 没有分支标记

**原因:** 收集的路径重复或数量不足

**解决:** 增加路径数量参数

---

## ⚙️ 环境要求

- **操作系统:** Linux (TencentOS Server 4.4 或兼容)
- **Python:** 3.7+
- **rmem:** 通过 opam 安装的 rmem 工具
- **opam switch:** opam-4.11.2-for-rmem

---

## 📚 参考资料

- [rmem 官方仓库](https://github.com/rems-project/rmem)
- [RISC-V 内存模型规范](https://github.com/riscv/riscv-isa-manual)
- [Promising Semantics 论文](https://sf.snu.ac.kr/promise-concurrency/)

---

## 🤝 贡献

本工具集由 AI 辅助开发,用于简化 rmem 输出的分析。

**主要功能:**
- 自动解析 rmem `-debug` 输出
- 识别不同执行路径的分支点
- 追踪寄存器和内存状态变化
- 生成易读的表格格式

---

## 📄 许可

本工具集遵循 rmem 原项目的许可协议。

---

## 📧 联系

如有问题或建议,请通过 git issue 反馈。
