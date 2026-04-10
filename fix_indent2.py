with open('atm_v6.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The structure should be:
# Line 5769: if recursos_mec... (indent 12)
# Lines inside if: indent 16
# Line 5832: with pd.ExcelWriter... (indent 16) - inside the if
# Lines inside with: indent 20
# Line 5837: try: (indent 20) - inside the with
# Lines inside try: indent 24
# Line 5849: except (indent 20) - matches try
# Line 5850: pass (indent 24) - inside except
# Line 5851: with pd.ExcelWriter... (indent 16) - inside the if

# Line 5851 currently has indent 16, should be indent 16 - CORRECT

# Let me check the actual indentation
print('Lines around 5848-5853:')
for i in range(5848, 5855):
    if i < len(lines):
        line = lines[i]
        indent = len(line) - len(line.lstrip())
        print(f'{i+1}: [{indent}] {line[:70]}')
