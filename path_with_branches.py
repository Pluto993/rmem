#!/usr/bin/env python3
"""
rmem 完整路径分析 - 正确的分支标记和寄存器追踪
"""

import sys
import subprocess
import re
from collections import defaultdict

def normalize_instruction(inst_str):
    """规范化指令"""
    reg_map = {
        r'\bt0\b': 'X5', r'\bt1\b': 'X6', 
        r'\bt2\b': 'X7', r'\bfp\b': 'X8',
        r'\bzero\b': '0'
    }
    
    result = inst_str
    for pattern, replacement in reg_map.items():
        result = re.sub(pattern, replacement, result)
    
    result = re.sub(r'ori\s+(\w+),\s*0,\s*(\d+)', r'li \1, \2', result)
    result = re.sub(r'fence\.tso\s+rw,\s*rw', 'fence.tso', result)
    
    return result.strip()

def parse_registers(line):
    """从 reg: 行中提取寄存器"""
    regs = {}
    pattern = r'(x\d+):\s+0x_\w+\'([0-9a-fA-F]+)'
    
    for match in re.finditer(pattern, line):
        reg_name = match.group(1)
        hex_value = match.group(2)
        value = int(hex_value, 16)
        
        if value < 0x10000000:
            regs[reg_name] = value
    
    return regs

def extract_register_changes(old_regs, new_regs, thread_id):
    """提取寄存器变化 - 改进版"""
    changes = []
    
    # 检查所有关键寄存器
    for reg in ['x5', 'x7']:
        old_val = old_regs.get(reg, 0)
        new_val = new_regs.get(reg, 0)
        
        if old_val != new_val:
            reg_name = 'X' + reg[1:]
            changes.append(f"{reg_name}: {old_val} → {new_val}")
    
    return ", ".join(changes) if changes else "-"

def parse_single_trace(output):
    """解析单次 rmem -debug 输出"""
    steps = []
    prev_regs = {0: {}, 1: {}}
    curr_regs = {0: {}, 1: {}}
    current_thread = None
    thread_id = None
    action_type = None
    pending_inst = {}
    step_num = 0
    in_state_block = False
    
    for line in output.split('\n'):
        # 新状态块
        if '***** new state *****' in line:
            in_state_block = True
            continue
        
        # 提取 transition
        if 'Taking ###' in line:
            match = re.search(r'transition:\s+\[(\d+)\]\s+(\d+):(\d+)\s+(.+)', line)
            if match:
                thread_id = int(match.group(2))
                action_desc = match.group(4)
                
                if any(kw in action_desc for kw in ['finish instruction:', 'read:', 'write:', 'fulfill']):
                    action_type = 'user'
                else:
                    action_type = None
        
        # 提取指令
        if 'ioid:' in line:
            match = re.search(r'ioid:\s+(\d+):\d+\s+loc:\s+\S+\s+([a-z][a-z0-9.]+(?:\s+[^=\n]+?)?)(?:\s+(?:reg|mem|read))', line)
            if match:
                tid = int(match.group(1))
                inst = match.group(2).strip()
                pending_inst[tid] = normalize_instruction(inst)
        
        # 解析寄存器状态
        if line.startswith('Thread '):
            match = re.match(r'Thread (\d+) state:', line)
            if match:
                current_thread = int(match.group(1))
        
        if line.startswith('reg:') and current_thread is not None:
            regs = parse_registers(line)
            if regs:
                curr_regs[current_thread] = regs
        
        # via 行标志步骤完成
        if 'via ' in line:
            in_state_block = False
            
            if thread_id is not None and action_type == 'user':
                inst = pending_inst.get(thread_id, '')
                if inst:
                    step_num += 1
                    
                    # 改进的寄存器变化检测
                    reg_changes = extract_register_changes(
                        prev_regs.get(thread_id, {}), 
                        curr_regs.get(thread_id, {}),
                        thread_id
                    )
                    
                    # 内存变化
                    mem_changes = "-"
                    if 'sw' in inst.lower():
                        # 提取存储地址信息
                        mem_changes = "Store to memory"
                    elif 'lw' in inst.lower():
                        mem_changes = "Load from memory"
                    
                    steps.append({
                        'step': step_num,
                        'core': f'Core{thread_id}',
                        'instruction': inst,
                        'reg_changes': reg_changes,
                        'mem_changes': mem_changes
                    })
            
            # 更新寄存器状态
            if thread_id is not None:
                prev_regs[thread_id] = dict(curr_regs.get(thread_id, {}))
            
            thread_id = None
            action_type = None
            current_thread = None
    
    return steps

def analyze_branches(all_paths):
    """
    分析多条路径,识别分支点
    返回: 每个步骤的分支标记
    """
    # 构建步骤树
    step_tree = {}
    
    for path_idx, path in enumerate(all_paths):
        path_id = chr(ord('a') + path_idx)  # a, b, c, ...
        
        for step_idx, step in enumerate(path['steps']):
            key = (step_idx, step['core'], step['instruction'])
            
            if key not in step_tree:
                step_tree[key] = []
            
            step_tree[key].append({
                'path_id': path_id,
                'path_idx': path_idx,
                'step': step
            })
    
    # 为每条路径标记分支
    for path in all_paths:
        for step_idx, step in enumerate(path['steps']):
            key = (step_idx, step['core'], step['instruction'])
            variants = step_tree.get(key, [])
            
            # 如果同一位置有多个不同的步骤,标记为分支
            if len(variants) > 1:
                # 找到当前步骤在分支中的索引
                for var_idx, variant in enumerate(variants):
                    if variant['step'] == step:
                        step['branch'] = chr(ord('a') + var_idx)
                        break
            else:
                step['branch'] = '-'
    
    return all_paths

def print_step_table(step_num, core, instruction, reg_changes, mem_changes, branch="-"):
    """打印单步表格"""
    step_label = f"{step_num}{branch}" if branch != "-" else str(step_num)
    
    print(f"Step {step_label}: {core} executes {instruction}")
    print("┌───────────────┬─────────────┬─────────────────────────────────┬──────────────────────┬──────────────────────┐")
    print(f"│ {'Step':<13} │ {'Branch':<11} │ {'Instruction':<31} │ {'Register Changes':<20} │ {'Memory Changes':<20} │")
    print("├───────────────┼─────────────┼─────────────────────────────────┼──────────────────────┼──────────────────────┤")
    print(f"│ {step_label:<13} │ {branch:<11} │ {instruction:<31} │ {reg_changes:<20} │ {mem_changes:<20} │")
    print("└───────────────┴─────────────┴─────────────────────────────────┴──────────────────────┴──────────────────────┘")
    print()

def main():
    if len(sys.argv) < 2:
        print("用法: python3 path_with_branches.py <litmus_file> [model] [num_paths]")
        print("示例: python3 path_with_branches.py test_sb_fence_tso.litmus promising 10")
        sys.exit(1)
    
    litmus_file = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "promising"
    num_attempts = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    print("=" * 120)
    print("🎯 rmem Path Analysis with Branch Detection")
    print("=" * 120)
    print()
    
    # 收集多条不同的路径
    all_paths = []
    seen_signatures = set()
    
    for i in range(num_attempts):
        sys.stdout.write(f"\r收集路径: {i+1}/{num_attempts}")
        sys.stdout.flush()
        
        cmd = [
            'bash', '-c',
            f'cd /root/.openclaw/workspace/rmem && '
            f'eval $(opam env --switch=opam-4.11.2-for-rmem) && '
            f'timeout 20 ./rmem -model {model} -interactive false -debug -random_traces 1 {litmus_file} 2>&1'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            steps = parse_single_trace(result.stdout)
            
            if steps:
                # 创建路径签名 (基于指令序列)
                signature = tuple((s['core'], s['instruction']) for s in steps)
                
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    
                    # 提取最终状态
                    final_state = ""
                    for line in result.stdout.split('\n'):
                        match = re.match(r'\s*\d+\s+([*:])>(.+)', line.strip())
                        if match:
                            marker = match.group(1)
                            state = match.group(2).strip()
                            is_violation = (marker == '*')
                            final_state = f"{'❌ VIOLATION' if is_violation else '✅ OK'} - {state}"
                            break
                    
                    all_paths.append({
                        'steps': steps,
                        'final_state': final_state
                    })
        except:
            pass
    
    print()
    print(f"\n✅ 收集到 {len(all_paths)} 条不同路径")
    print()
    
    # 分析分支
    all_paths = analyze_branches(all_paths)
    
    # 显示每条路径
    for path_idx, path in enumerate(all_paths, 1):
        print("=" * 120)
        print(f"路径 #{path_idx}")
        if path['final_state']:
            print(f"最终状态: {path['final_state']}")
        print("=" * 120)
        print()
        
        for step in path['steps']:
            print_step_table(
                step['step'],
                step['core'],
                step['instruction'],
                step['reg_changes'],
                step['mem_changes'],
                step.get('branch', '-')
            )
        
        print()

if __name__ == "__main__":
    main()
