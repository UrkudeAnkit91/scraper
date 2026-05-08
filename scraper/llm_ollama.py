import json
import time
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


OLLAMA_BASE_URL = "http://localhost:11434"


def _api_call(endpoint: str, payload: Optional[Dict] = None, timeout: int = 180) -> Optional[Dict]:
    url = f"{OLLAMA_BASE_URL}{endpoint}"
    data = json.dumps(payload).encode() if payload else None
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except URLError as e:
        print(f"  Ollama connection error: {e.reason}", flush=True)
        return None
    except Exception as e:
        print(f"  Ollama error: {e}", flush=True)
        return None


def is_available() -> bool:
    result = _api_call("/api/tags", timeout=5)
    return result is not None


def list_models() -> List[str]:
    result = _api_call("/api/tags", timeout=5)
    if not result:
        return []
    return [m["name"] for m in result.get("models", [])]


def generate(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.35,
    max_tokens: int = 6000,
) -> Optional[str]:
    print(f"🤖 Generating with Ollama ({model})...", flush=True)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    for attempt in range(3):
        try:
            print(f"  Attempt {attempt + 1}/3...", flush=True)
            result = _api_call("/api/chat", payload, timeout=300)
            if not result:
                time.sleep(10)
                continue

            message = result.get("message", {})
            content = message.get("content", "")

            if len(content) > 20:
                print(f"✅ Generated {len(content)} chars", flush=True)
                return content.strip()

            print(f"  Ollama returned short/empty content: {str(result)[:300]}", flush=True)
        except Exception as e:
            print(f"  Error: {e}", flush=True)
            time.sleep(10)

    print("❌ All Ollama attempts failed", flush=True)
    return None
