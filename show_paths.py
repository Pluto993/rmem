#!/usr/bin/env python3
"""
rmem 路径可视化 - 简化版
直接从 rmem 非调试输出解析,显示所有执行路径
"""

import sys
import re

def main():
    print("=" * 120)
    print("rmem Execution Paths")
    print("=" * 120)
    print()
    
    paths = []
    current_count = None
    current_marker = None
    current_state = None
    current_via = None
    
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
                'count': count,
                'violation': is_violation,
                'state': state,
                'via': via
            })
    
    if not paths:
        print("No paths found. Make sure to run rmem in non-interactive mode:")
        print("  ./rmem -model promising -interactive false -random_traces N test.litmus")
        return
    
    # 按违例/正常分组
    violations = [p for p in paths if p['violation']]
    normal = [p for p in paths if not p['violation']]
    
    print(f"📊 Summary:")
    print(f"  Total paths:     {len(paths)}")
    print(f"  ❌ Violations:    {len(violations)}")
    print(f"  ✅ Normal:        {len(normal)}")
    print()
    
    # 打印违例路径
    if violations:
        print("=" * 120)
        print("❌ VIOLATION PATHS (存在弱内存可见性问题)")
        print("=" * 120)
        print()
        
        for i, path in enumerate(violations, 1):
            print(f"Path {i}/{len(violations)} (出现 {path['count']} 次):")
            print(f"  Final State: {path['state']}")
            print(f"  Via Path:    {path['via']}")
            print()
    
    # 打印正常路径
    if normal:
        print("=" * 120)
        print("✅ NORMAL PATHS (满足内存一致性)")
        print("=" * 120)
        print()
        
        for i, path in enumerate(normal, 1):
            print(f"Path {i}/{len(normal)} (出现 {path['count']} 次):")
            print(f"  Final State: {path['state']}")
            print(f"  Via Path:    {path['via']}")
            print()
    
    print("=" * 120)
    print(f"Total: {len(paths)} unique execution paths")
    print("=" * 120)

if __name__ == "__main__":
    main()
