import os
import time
from typing import Dict, List, Optional, Tuple

import requests

from .config import API_URL, CODE_WORDS, ADVANCED_PYTHON_SIGNALS, COMPLEX_KEYWORDS, OPENROUTER_HEADERS
from .network import format_network_error


def get_model_profiles() -> Dict:
    return {
        'Auto': None,
        'Custom': {
            'model': os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-coder:free'),
            'max_tokens': int(os.getenv('OPENROUTER_MAX_TOKENS', '6000')),
            'temperature': float(os.getenv('OPENROUTER_TEMPERATURE', '0.45')),
        },
        'Coding': {
            'model': 'qwen/qwen3-coder:free',
            'max_tokens': 6000,
            'temperature': 0.35,
        },
        'Advanced Python Tutor': {
            'model': 'qwen/qwen3-coder:free',
            'max_tokens': 7000,
            'temperature': 0.32,
        },
        'Reasoning': {
            'model': 'nvidia/nemotron-3-nano-omni-30b-a3b:free',
            'max_tokens': 8000,
            'temperature': 0.45,
        },
        'Fast': {
            'model': 'qwen/qwen3-coder:free',
            'max_tokens': 2500,
            'temperature': 0.25,
        },
    }


def is_code_request(query: str) -> bool:
    normalized = query.lower()
    return any(word in normalized for word in CODE_WORDS)


def is_advanced_python_request(query: str, ai_profile: str) -> bool:
    normalized = query.lower()
    return ai_profile == 'Advanced Python Tutor' or any(
        signal in normalized for signal in ADVANCED_PYTHON_SIGNALS
    )


def advanced_python_training_context() -> str:
    return (
        "\n\nAdvanced Python tutor training context:\n"
        "- Teach from first principles, then show production-grade patterns.\n"
        "- Prefer modern Python 3.11+ style: dataclasses, pathlib, contextlib, typing, protocols, "
        "match/case when helpful, and clear exception design.\n"
        "- Cover advanced topics when relevant: iterators/generators, decorators, descriptors, context "
        "managers, metaclasses, async/await, asyncio tasks, concurrency vs parallelism, multiprocessing, "
        "type hints, protocols, dependency injection, packaging, testing with pytest, profiling, caching, "
        "logging, database access, and clean architecture.\n"
        "- For code answers, include: concept summary, complete code, explanation of important lines, "
        "common mistakes, and one practice challenge.\n"
        "- For learning questions, include a short lesson plan, examples, and exercises.\n"
        "- Emphasize readability, maintainability, security, and debuggability."
    )


def select_ai_model(query: str, ai_profile: str, model_profiles: Dict) -> Tuple[str, int, float]:
    selected = model_profiles.get(ai_profile)
    if selected:
        return selected['model'], selected['max_tokens'], selected['temperature']

    is_complex = any(word in query.lower() for word in COMPLEX_KEYWORDS)
    if is_complex:
        return 'nvidia/nemotron-3-nano-omni-30b-a3b:free', 8000, 0.45
    return 'qwen/qwen3-coder:free', 4500, 0.35


def build_ai_prompt(
    query: str,
    search_results: Optional[List[Dict]],
    wants_code: bool,
    is_advanced: bool,
    gpu_info: Optional[Dict],
) -> Tuple[str, str]:
    gpu_str = ""
    if gpu_info:
        gpu_str = f"\nUser has GPU: {gpu_info['name']} with {gpu_info['memory']:.1f}GB. Use CUDA when it is relevant."

    if wants_code:
        system_content = (
            "You are an expert Python developer and practical technical teacher.\n"
            "Return a clear explanation first, then complete runnable Python code.\n"
            "Use the user's request and search results as context, but do not invent facts from weak snippets.\n"
            "Include imports, error handling, simple setup notes, and example usage.\n"
            "Follow applicable law and platform safety rules. Do not hardcode secrets or API keys."
            f"{gpu_str}"
        )
        user_suffix = "Provide a concise explanation, then complete Python code in one fenced python block."
    else:
        system_content = (
            "You are a clear technical explainer.\n"
            "Answer the user's question directly in beginner-friendly language.\n"
            "Use search results as context when available and be honest when live sources are incomplete.\n"
            "Only include code if it genuinely helps explain the idea."
        )
        user_suffix = "Provide a clear explanation. Include a tiny example only if useful."

    if is_advanced:
        system_content += advanced_python_training_context()
        user_suffix += (
            " Teach it at an advanced Python level, with best practices, common pitfalls, "
            "and a practice exercise."
        )

    search_context = ""
    if search_results:
        lines = []
        for item in search_results[:6]:
            title = item.get('title', 'Untitled')
            url = item.get('url', '')
            snippet = item.get('snippet', '')
            source = item.get('source', 'Web')
            lines.append(f"- [{source}] {title}: {url}\n  {snippet}".strip())
        search_context = "\n\nRelevant search results:\n" + "\n".join(lines)

    user_content = f"Request: {query}{search_context}\n\n{user_suffix}"
    return system_content, user_content


def generate_code_with_ai(
    api_key: str,
    model: str,
    max_tokens: int,
    temperature: float,
    system_content: str,
    user_content: str,
) -> Optional[str]:
    print("🤖 Generating with AI (OpenRouter)...", flush=True)

    if not api_key:
        print("❌ Missing OPENROUTER_API_KEY environment variable", flush=True)
        return None

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost',
        'X-Title': 'Python Code Generator',
    }

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_content},
            {'role': 'user', 'content': user_content},
        ],
        'temperature': temperature,
        'max_tokens': max_tokens,
        'top_p': 0.9,
    }

    for attempt in range(5):
        try:
            print(f"  Attempt {attempt + 1}/5 with {model}...", flush=True)
            response = requests.post(API_URL, headers=headers, json=payload, timeout=180)

            if response.status_code == 200:
                try:
                    result = response.json()
                except ValueError:
                    print("  API returned invalid JSON", flush=True)
                    continue
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    if len(content) > 40:
                        print(f"✅ Generated {len(content)} chars", flush=True)
                        return content.strip()
                print(f"  API returned no usable content: {str(result)[:300]}", flush=True)
            elif response.status_code == 429:
                wait = 15 * (2 ** attempt)
                print(f"  Rate limited. Waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            else:
                print(f"  API error {response.status_code}: {response.text[:300]}", flush=True)

        except requests.RequestException as e:
            print(f"  Error: {format_network_error(e)}", flush=True)
            time.sleep(15)

    print("❌ All attempts failed", flush=True)
    return None
