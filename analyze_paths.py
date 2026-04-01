#!/usr/bin/env python3
"""
rmem 执行路径分析工具
显示所有可能的执行路径,标注违例和正常情况
"""

import sys
import re

def main():
    print("=" * 120)
    print("📊 rmem Execution Paths Analysis")
    print("=" * 120)
    print()
    
    paths = []
    
    for line in sys.stdin:
        line = line.strip()
        
        # 解析路径行
        # 格式: "31    *>0:x7=0; 1:x7=0;  via "0;2;1;0;1;0;0;1""
        match = re.match(r'(\d+)\s+([*:])>(.+?)\s+via\s+"(.+)"', line)
        if match:
            count = int(match.group(1))
            marker = match.group(2)
            state = match.group(3).strip()
            via = match.group(4).strip()
            
            is_violation = (marker == '*')
            
            paths.append({
                'id': len(paths) + 1,
                'count': count,
                'violation': is_violation,
                'state': state,
                'via': via
            })
    
    if not paths:
        print("❌ No paths found. Make sure to run:")
        print("   ./rmem -model promising -interactive false -random_traces N test.litmus")
        return
    
    # 统计
    violations = [p for p in paths if p['violation']]
    normal = [p for p in paths if not p['violation']]
    
    print(f"Total unique paths:  {len(paths)}")
    print(f"❌ Violations:        {len(violations)}")
    print(f"✅ Normal:            {len(normal)}")
    print()
    
    # 打印所有路径
    print("=" * 120)
    print("All Execution Paths")
    print("=" * 120)
    print()
    
    for path in paths:
        status = "❌ VIOLATION" if path['violation'] else "✅ OK"
        
        print(f"Path #{path['id']} {status} (出现 {path['count']} 次)")
        print(f"  Final State: {path['state']}")
        print(f"  Via Path:    {path['via']}")
        print()
    
    print("=" * 120)
    print()
    
    # 打印路径图
    print("=" * 120)
    print("📈 Execution Path Tree (简化视图)")
    print("=" * 120)
    print()
    
    # 按 via 路径前缀分组
    via_tree = {}
    
    for path in paths:
        via_steps = path['via'].split(';')
        
        # 构建树
        current = via_tree
        for i, step in enumerate(via_steps):
            step = step.strip()
            if step not in current:
                current[step] = {'children': {}, 'paths': []}
            
            # 最后一步,记录完整路径
            if i == len(via_steps) - 1:
                current[step]['paths'].append(path)
            
            current = current[step]['children']
    
    # 打印树
    def print_tree(node_dict, prefix="", is_last=True, depth=0, max_depth=8):
        if depth > max_depth:
            return
        
        items = list(node_dict.items())
        for i, (step, data) in enumerate(items):
            is_last_item = (i == len(items) - 1)
            
            # 连接符
            if depth == 0:
                connector = ""
                new_prefix = ""
            else:
                connector = "└─ " if is_last_item else "├─ "
                extension = "   " if is_last_item else "│  "
                new_prefix = prefix + extension
            
            # 打印步骤
            step_info = f"Step {step}"
            
            # 如果是叶子节点,显示路径信息
            if data['paths']:
                path_info = ", ".join([
                    f"#{p['id']}{'❌' if p['violation'] else '✅'}"
                    for p in data['paths']
                ])
                step_info += f" → {path_info}"
            
            print(f"{prefix}{connector}{step_info}")
            
            # 递归打印子节点
            if data['children']:
                print_tree(data['children'], new_prefix, is_last_item, depth + 1, max_depth)
    
    print_tree(via_tree)
    
    print()
    print("=" * 120)
    print("💡 Tip: 使用 filter_register_changes.py 查看每个路径的详细指令")
    print("=" * 120)

if __name__ == "__main__":
    main()
