import re
import time
from typing import Dict, Optional, Tuple


def parse_ai_response(response: str) -> Tuple[str, Optional[str]]:
    code_pattern = r'```(?:python)?\n?(.*?)```'
    matches = re.findall(code_pattern, response, re.DOTALL)

    if matches:
        code = matches[-1].strip()
        explanation = re.sub(code_pattern, '', response, flags=re.DOTALL).strip()
    else:
        lines = response.split('\n')
        code_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith(('def ', 'class ', 'import ', 'from ')):
                code_start = i
                break
        if code_start is not None:
            explanation = '\n'.join(lines[:code_start]).strip()
            code = '\n'.join(lines[code_start:]).strip()
        else:
            explanation = response
            code = None

    return explanation, code


def fix_syntax_error(code: str, error: SyntaxError) -> str:
    print("🔧 Attempting to fix syntax error...", flush=True)
    lines = code.split('\n')
    error_line = error.lineno - 1 if error.lineno else 0

    if error_line < len(lines):
        if 'print' in lines[error_line] and ')' not in lines[error_line]:
            lines[error_line] = lines[error_line].replace('print', 'print(') + ')'
        if ('def ' in lines[error_line] or 'if ' in lines[error_line]) and ':' not in lines[error_line]:
            lines[error_line] += ':'

    return '\n'.join(lines)


def enhance_code_with_gpu(code: str, gpu_available: bool) -> str:
    if not gpu_available or not code or 'torch' not in code.lower():
        return code

    print("🔧 Enhancing code with GPU support...", flush=True)

    gpu_setup = '''# GPU setup (auto-added)
import torch
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

'''

    if 'device' not in code:
        code = gpu_setup + code
        print("✅ Added GPU device setup", flush=True)

    return code


def save_generated_code(code: str, gpu_available: bool) -> Dict:
    if gpu_available:
        code = enhance_code_with_gpu(code, gpu_available)

    filename = f"generated_{int(time.time())}.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(code)

    try:
        compile(code, filename, 'exec')
        syntax_ok = True
        fixed = False
    except SyntaxError as e:
        syntax_ok = False
        fixed = True
        print(f"❌ Syntax error: {e}", flush=True)
        code = fix_syntax_error(code, e)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)

    clean_filename = f"clean_{filename}"
    with open(clean_filename, 'w', encoding='utf-8') as f:
        f.write(code)

    return {
        'code_file': filename,
        'clean_code_file': clean_filename,
        'code': code,
        'syntax_valid': syntax_ok,
        'syntax_fixed': fixed,
    }
