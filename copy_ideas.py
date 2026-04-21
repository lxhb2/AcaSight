import os, sys
sys.stdout.reconfigure(encoding='utf-8')

# Find the desktop
desktop = None
for drive in ['F', 'E', 'D', 'C']:
    test = f'{drive}:\\'
    if os.path.exists(test):
        # Try common Chinese desktop paths
        for d in os.listdir(test):
            full = os.path.join(test, d)
            if os.path.isdir(full) and 'AI-acdemic' in d:
                print(f"Found: {full}")
                desktop = full
                break
    if desktop:
        break

if not desktop:
    # Use the path we know works from python os.listdir
    # Try direct file copy approach
    import shutil
    
    # Read all files from the folder
    src = r'F:\桌面\AI-acdemic app'
    
    # Since os.listdir worked before, try it again with the exact bytes
    base = 'F:\\'
    for d in os.listdir(base):
        if 'AI-acdemic' in d:
            src = os.path.join(base, d)
            break
    
    print(f"Source: {src}")
    dst = r'C:\Users\Administrator\.qclaw\workspace\papers\academic_ideas'
    os.makedirs(dst, exist_ok=True)
    
    for f in os.listdir(src):
        s = os.path.join(src, f)
        d = os.path.join(dst, f)
        if os.path.isfile(s):
            shutil.copy2(s, d)
            print(f"Copied: {f} ({os.path.getsize(s)} bytes)")
