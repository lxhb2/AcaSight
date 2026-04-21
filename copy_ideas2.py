import os, sys, shutil
sys.stdout.reconfigure(encoding='utf-8')

# Use subprocess with proper encoding
import subprocess
result = subprocess.run(
    ['cmd', '/c', 'chcp', '65001', '>', 'nul', '&&', 'dir', '/b', 'F:\\桌面\\AI-acdemic', 'app\\'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print("stdout:", result.stdout)
print("stderr:", result.stderr)

# Try with xcopy
result2 = subprocess.run(
    ['cmd', '/c', 'chcp', '65001', '>', 'nul', '&&', 'xcopy', '"F:\\桌面\\AI-acdemic app\\*"',
     r'"C:\Users\Administrator\.qclaw\workspace\papers\academic_ideas\\"', '/E', '/I', '/Y'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print("xcopy stdout:", result2.stdout)
print("xcopy stderr:", result2.stderr)
