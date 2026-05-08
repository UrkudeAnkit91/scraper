import subprocess
import sys
from typing import Optional, Tuple
from .config import CUDA_MAP


def init_gpu() -> Tuple[bool, Optional[dict]]:
    gpu_available = False
    gpu_info = None

    try:
        import torch
        print("✅ PyTorch installed", flush=True)

        if torch.cuda.is_available():
            gpu_available = True
            gpu_info = {
                'name': torch.cuda.get_device_name(0),
                'memory': torch.cuda.get_device_properties(0).total_memory / 1024 ** 3,
                'count': torch.cuda.device_count(),
            }
            print(f"✅ GPU detected: {gpu_info['name']} ({gpu_info['memory']:.1f}GB)", flush=True)
        else:
            print("⚠️ CUDA not available in PyTorch.", flush=True)
            try:
                result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print("  NVIDIA GPU detected but PyTorch has no CUDA support.", flush=True)
                    print("  For GPU support with Python 3.14:", flush=True)
                    print("  1. Install Python 3.12 from python.org", flush=True)
                    print("  2. Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124", flush=True)
                    print("  Using CPU version for now.", flush=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                print("  No NVIDIA GPU detected. Using CPU.", flush=True)
    except ImportError:
        print("⚠️ PyTorch not found. Install with: pip install torch", flush=True)
    except Exception as e:
        print(f"⚠️ GPU init error: {e}", flush=True)

    return gpu_available, gpu_info


def detect_cuda_version() -> str:
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'CUDA Version' in line:
                    version = line.split('CUDA Version:')[1].strip().split()[0]
                    major_minor = version.replace('.', '')
                    print(f"  Detected CUDA {version}", flush=True)
                    return major_minor
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    print("  Using default CUDA 12.1", flush=True)
    return '121'


def get_torch_url(cuda_version: str) -> Optional[str]:
    if sys.version_info >= (3, 14):
        print(f"  Python {sys.version_info.major}.{sys.version_info.minor} is too new for CUDA wheels", flush=True)
        print("  Using CPU version. For GPU, use Python 3.12 or 3.13", flush=True)
        return None

    cuda_tag = CUDA_MAP.get(cuda_version, 'cu121')
    return f"https://download.pytorch.org/whl/{cuda_tag}"
