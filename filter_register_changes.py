#!/usr/bin/env python3
"""
rmem Debug Output Parser - 表格格式显示完整指令和寄存器变化
从 rmem -debug 输出中提取完整的用户指令执行流程
"""

import sys
import re
from collections import defaultdict

def parse_registers(line):
    """从 reg: 行中提取所有寄存器"""
    regs = {}
    pattern = r'(x\d+):\s+0x_\w+\'([0-9a-fA-F]+)(?:\s+\((\w+)\))?'
    
    for match in re.finditer(pattern, line):
        reg_name = match.group(1)
        hex_value = match.group(2)
        value = int(hex_value, 16)
        
        if value < 0x10000000:
            regs[reg_name] = value
    
    return regs

def compare_registers(old_regs, new_regs):
    """对比两个寄存器状态,返回变化"""
    changes = {}
    all_regs = set(old_regs.keys()) | set(new_regs.keys())
    
    for reg in sorted(all_regs):
        old_val = old_regs.get(reg, 0)
        new_val = new_regs.get(reg, 0)
        
        if old_val != new_val:
            changes[reg] = (old_val, new_val)
    
    return changes

def format_register_name(reg):
    """将 x5 转为 X5 格式"""
    return 'X' + reg[1:]

def normalize_instruction(inst_str):
    """规范化指令: t0→X5, t1→X6, t2→X7, fp→X8, ori→li"""
    reg_map = {
        r'\bt0\b': 'X5',
        r'\bt1\b': 'X6', 
        r'\bt2\b': 'X7',
        r'\bfp\b': 'X8',
        r'\bzero\b': '0'
    }
    
    result = inst_str
    for pattern, replacement in reg_map.items():
        result = re.sub(pattern, replacement, result)
    
    # ori X5, 0, 1 => li X5, 1
    result = re.sub(r'ori\s+(\w+),\s*0,\s*(\d+)', r'li \1, \2', result)
    
    return result.strip()

def main():
    print("=" * 120)
    print("rmem Execution Trace - User Instructions with Register Changes")
    print("=" * 120)
    print()
    
    # 状态追踪
    prev_thread_regs = {0: {}, 1: {}}
    curr_thread_regs = {0: {}, 1: {}}
    
    current_thread = None
    step_num = 0
    user_step_num = 0
    thread_id = None
    action_type = None
    
    in_state_block = False
    pending_ioid_inst = {}  # {thread_id: instruction_str}
    
    steps = []
    
    for line in sys.stdin:
        line = line.rstrip()
        
        # 新状态块
        if '***** new state *****' in line:
            in_state_block = True
            if step_num > 0:
                prev_thread_regs = {tid: dict(curr_thread_regs[tid]) for tid in curr_thread_regs}
            curr_thread_regs = {0: {}, 1: {}}
            continue
        
        # 提取 transition
        if 'Taking ###' in line and 'transition:' in line:
            match = re.search(r'transition:\s+\[(\d+)\]\s+(\d+):(\d+)\s+(.+)', line)
            if match:
                thread_id = int(match.group(2))
                action_desc = match.group(4)
                
                # 分类
                if 'finish instruction:' in action_desc:
                    action_type = 'finish'
                elif 'read:' in action_desc:
                    action_type = 'read'
                elif 'write:' in action_desc or 'fulfill promise' in action_desc:
                    action_type = 'write'
                else:
                    action_type = None
            continue
        
        # 提取 ioid 指令
        if ', ioid:' in line or line.startswith('[ioid:'):
            ioid_match = re.search(r'ioid:\s+(\d+):(\d+)\s+loc:\s+0x[0-9a-fA-F]+\s+([a-z][a-z0-9.]+\s+[^=\n]+?)(?:\s+(?:reg writes|mem writes|read from):|\s*$)', line)
            if ioid_match:
                tid = int(ioid_match.group(1))
                inst_raw = ioid_match.group(3).strip()
                pending_ioid_inst[tid] = inst_raw
        
        # 解析线程状态
        thread_match = re.match(r'Thread (\d+) state:', line)
        if thread_match:
            current_thread = int(thread_match.group(1))
            continue
        
        # 解析寄存器
        if in_state_block and current_thread is not None and line.startswith('reg:'):
            regs = parse_registers(line)
            if regs:
                curr_thread_regs[current_thread] = regs
            continue
        
        # via 行 - 状态块结束
        if 'via "' in line:
            in_state_block = False
            step_num += 1
            
            if thread_id is not None and action_type:
                # 获取对应的指令
                instruction = pending_ioid_inst.get(thread_id, '')
                
                if instruction and action_type in ['finish', 'read', 'write']:
                    user_step_num += 1
                    
                    # 规范化指令
                    normalized_inst = normalize_instruction(instruction)
                    
                    # 对比寄存器 (跳过前几步初始化)
                    if step_num > 2:
                        changes = compare_registers(
                            prev_thread_regs.get(thread_id, {}), 
                            curr_thread_regs[thread_id]
                        )
                    else:
                        changes = {}
                    
                    # 格式化
                    if changes:
                        change_str = ", ".join([
                            f"{format_register_name(reg)}: {old} → {new}"
                            for reg, (old, new) in sorted(changes.items())
                        ])
                    else:
                        change_str = '-'
                    
                    steps.append({
                        'step': user_step_num,
                        'core': f'Core{thread_id}',
                        'instruction': normalized_inst,
                        'changes': change_str
                    })
            
            # 重置
            thread_id = None
            action_type = None
            current_thread = None
    
    # 打印表格
    if steps:
        print(f"{'Step':<6} {'Core':<8} {'Instruction':<35} {'Register Changes'}")
        print("-" * 120)
        
        for step in steps:
            print(f"{step['step']:<6} {step['core']:<8} {step['instruction']:<35} {step['changes']}")
    
    print()
    print("=" * 120)
    print(f"Total steps: {user_step_num}")
    print("=" * 120)

if __name__ == "__main__":
    main()
