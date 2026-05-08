import os
from typing import Dict, List, Optional

from . import database
from . import gpu as gpu_module
from . import network
from . import search as search_module
from . import ai as ai_module
from . import llm_ollama
from . import generation as gen_module
from . import code_utils
from .config import HEADERS


class InternetScraperAndCodeGenerator:
    def __init__(self, use_ollama: bool = False):
        self.headers = HEADERS
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.ai_profile = os.getenv('OPENROUTER_MODEL_PROFILE', 'Auto')
        self.model_profiles = ai_module.get_model_profiles()
        self.search_results = []
        self.last_search_error = None
        self.use_ollama = use_ollama
        self.ollama_model = "mistral:7b"
        self.ollama_available = llm_ollama.is_available() if use_ollama else False

        self.conn, self.cursor = database.init_database()
        self.gpu_available, self.gpu_info = gpu_module.init_gpu()

        if self.use_ollama and self.ollama_available:
            available = llm_ollama.list_models()
            print(f"✅ Ollama ready — models: {', '.join(available) or 'none'}", flush=True)
        elif self.api_key:
            print("✅ OpenRouter API key found", flush=True)
        else:
            print("⚠️ No AI provider configured (set OPENROUTER_API_KEY or use Ollama).", flush=True)

    def set_provider(self, provider: str):
        if provider.lower() == "ollama":
            self.use_ollama = True
            self.ollama_available = llm_ollama.is_available()
            if self.ollama_available:
                print("✅ Ollama enabled", flush=True)
        else:
            self.use_ollama = False

    def _make_get_page(self):
        return lambda url, timeout=15: network.get_page(url, self.headers, timeout)

    def _make_get_json(self):
        return lambda url, timeout=15: network.get_json(url, self.headers, timeout)

    def set_ai_profile(self, profile: str):
        if profile not in self.model_profiles:
            profile = 'Auto'
        self.ai_profile = profile

    def set_ollama_model(self, model: str):
        self.ollama_model = model

    def refresh_ollama_models(self) -> List[str]:
        self.ollama_available = llm_ollama.is_available()
        return llm_ollama.list_models()

    def search_internet(self, query: str, num_results: int = 10) -> List[Dict]:
        print(f"🔍 Searching for: {query}", flush=True)
        self.last_search_error = None
        results = []

        get_page = self._make_get_page()
        get_json = self._make_get_json()

        if search_module.is_explainer_question(query):
            providers = [
                lambda q, l: search_module.search_wikipedia(q, l, get_json),
                lambda q, l: search_module.search_direct_sites(q, l, get_page),
                lambda q, l: search_module.search_bing(q, l, get_page),
                lambda q, l: search_module.search_duckduckgo(q, l, get_page),
            ]
        else:
            providers = [
                lambda q, l: search_module.search_stackoverflow(q, l, get_page),
                lambda q, l: search_module.search_wikipedia(q, l, get_json),
                lambda q, l: search_module.search_direct_sites(q, l, get_page),
                lambda q, l: search_module.search_bing(q, l, get_page),
                lambda q, l: search_module.search_duckduckgo(q, l, get_page),
            ]

        for provider in providers:
            if len(results) >= num_results:
                break
            try:
                remaining = num_results - len(results)
                results.extend(provider(query, remaining))
            except Exception as e:
                print(f"  Search parser error: {e}", flush=True)

        deduped = search_module.dedupe_results(results)
        self.search_results = deduped[:num_results]

        if self.search_results:
            print(f"✅ Found {len(self.search_results)} result(s)", flush=True)
        elif self.last_search_error:
            print(f"❌ No search results. Last network error: {self.last_search_error}", flush=True)
        else:
            print("⚠️ No search results found. The sites may have changed their HTML or blocked the request.", flush=True)

        return self.search_results

    def generate_image_from_query(self, query: str) -> Dict:
        import re
        prompt = re.sub(
            r"^(generate|create|make|draw|paint)\s*(an?\s*)?(image|picture|photo|artwork|art|illustration)\s*(of\s*|:)?\s*",
            "", query, flags=re.IGNORECASE
        ).strip()
        if not prompt:
            prompt = query

        print(f"\n🎨 Generating image: {prompt[:80]}...")
        image = gen_module.generate_image(prompt=prompt)
        if image:
            info = gen_module.save_image(image, prompt)
            explanation = f"Generated image: {info['file_path']} ({info['width']}x{info['height']}, {info['size_kb']}KB)"
            print(f"  {explanation}", flush=True)
            return {"type": "image", "data": info, "image": image, "explanation": explanation, "code": None, "has_code": False}
        return {"type": "image", "error": "Image generation failed", "explanation": "Image generation failed. Check dependencies or try a different prompt.", "code": None, "has_code": False}

    def generate_video_from_query(self, query: str) -> Dict:
        import re
        prompt = re.sub(
            r"^(generate|create|make|animate)\s*(an?\s*)?(video|clip|animation)\s*(of\s*|:)?\s*",
            "", query, flags=re.IGNORECASE
        ).strip()
        if not prompt:
            prompt = query

        print(f"\n🎬 Generating video: {prompt[:80]}...")
        video_path = gen_module.generate_video(prompt=prompt)
        if video_path:
            explanation = f"Generated video: {video_path}"
            print(f"  {explanation}", flush=True)
            return {"type": "video", "data": {"file_path": video_path}, "explanation": explanation, "code": None, "has_code": False}
        return {"type": "video", "error": "Video generation failed", "explanation": "Video generation failed.", "code": None, "has_code": False}

    def generate_code_from_search(self, query: str) -> Dict:
        is_img = gen_module.is_image_request(query)
        is_vid = gen_module.is_video_request(query)
        if is_img or is_vid:
            return self.generate_image_from_query(query) if is_img else self.generate_video_from_query(query)

        print(f"\n🤖 Generating response for: {query}")
        results = self.search_internet(query, 3)
        database.save_search(self.cursor, self.conn, query, len(results))

        if results:
            print("\nTop search results:", flush=True)
            for index, item in enumerate(results, start=1):
                print(f"  {index}. [{item.get('source', 'Web')}] {item.get('title')}", flush=True)
                print(f"     {item.get('url')}", flush=True)

        ai_response = None
        wants_code = ai_module.is_code_request(query)
        is_advanced = ai_module.is_advanced_python_request(query, self.ai_profile)
        system_content, user_content = ai_module.build_ai_prompt(
            query, results, wants_code, is_advanced, self.gpu_info
        )

        if self.use_ollama and self.ollama_available:
            ai_response = llm_ollama.generate(
                model=self.ollama_model,
                system_prompt=system_content,
                user_prompt=user_content,
                temperature=0.35,
                max_tokens=6000,
            )
        elif self.api_key:
            model, max_tokens, temperature = ai_module.select_ai_model(query, self.ai_profile, self.model_profiles)
            ai_response = ai_module.generate_code_with_ai(
                self.api_key, model, max_tokens, temperature, system_content, user_content
            )
        else:
            provider = "Ollama" if self.use_ollama else "OpenRouter"
            print(f"ℹ️ {provider} is not available. AI generation will be skipped.", flush=True)

        if ai_response and len(ai_response) > 100:
            explanation, code = code_utils.parse_ai_response(ai_response)
            print(f"✅ Generated explanation ({len(explanation)} chars) and code ({len(code) if code else 0} chars)", flush=True)
        else:
            if ai_response is not None:
                print("❌ AI generation failed", flush=True)
            if results:
                explanation = self._build_search_only_explanation(query, results)
            elif self.last_search_error:
                explanation = self._build_local_fallback(query)
                if explanation:
                    explanation += (
                        "\n\nNote: live internet/AI lookup was unavailable. "
                        f"Last lookup status: {self.last_search_error}"
                    )
                else:
                    explanation = (
                        f"Unable to generate content for: {query}\n\n"
                        f"Internet search failed: {self.last_search_error}\n\n"
                        "This may be a site block/rate limit, an API-key issue, or a local network block."
                    )
            else:
                explanation = self._build_local_fallback(query) or f"Unable to generate content for: {query}"
            code = None

        return {'explanation': explanation, 'code': code, 'has_code': bool(code and len(code) > 50)}

    def _build_search_only_explanation(self, query: str, results: List[Dict]) -> str:
        lines = [
            f"Found web results for: {query}",
            "",
            "AI generation is unavailable, so here is what the scraper found:",
        ]
        for index, item in enumerate(results, start=1):
            lines.append(f"{index}. {item.get('title', 'Untitled')}")
            lines.append(f"   Source: {item.get('source', 'Web')}")
            lines.append(f"   URL: {item.get('url', '')}")
            if item.get('snippet'):
                lines.append(f"   Summary: {item['snippet']}")
        return '\n'.join(lines)

    def _build_local_fallback(self, query: str) -> Optional[str]:
        normalized = query.strip().lower().rstrip('?.!')
        if ai_module.is_advanced_python_request(query, self.ai_profile):
            return self._advanced_python_lesson()

        if normalized in {'what is api', 'what is an api', 'define api', 'explain api'}:
            return (
                "API stands for Application Programming Interface.\n\n"
                "An API is a way for one program to talk to another program in a controlled way. "
                "For example, a weather app can use a weather service API to ask for today's forecast. "
                "The app sends a request, the API receives it, and the service sends back a response, often as JSON.\n\n"
                "Simple example:\n\n"
                "```python\n"
                "import requests\n\n"
                "response = requests.get('https://api.github.com')\n"
                "print(response.status_code)\n"
                "print(response.json())\n"
                "```\n\n"
                "In short: an API is a contract that says what you can ask for, how to ask, "
                "and what kind of answer you will get back."
            )

        if normalized in {'what is computer', 'what is a computer', 'define computer', 'explain computer'}:
            return (
                "A computer is an electronic machine that accepts input, processes data using instructions, "
                "stores information, and produces output.\n\n"
                "For example, when you type into a keyboard, the computer receives that input, the processor "
                "runs instructions, memory and storage hold the data, and the screen shows the result.\n\n"
                "Main parts include the CPU, memory/RAM, storage, input devices, output devices, and software."
            )

        if normalized in {'what is hotelkey', 'define hotelkey', 'explain hotelkey'}:
            return (
                "HotelKey is a hospitality software platform/company focused on hotel operations. "
                "It is commonly associated with cloud property-management software for hotels, along with "
                "related tools for reservations, payments, point of sale, and guest operations.\n\n"
                "For the latest company details, products, pricing, and customer list, use live search, set "
                "OPENROUTER_API_KEY, or run with --ollama for local AI generation."
            )

        return None

    def _advanced_python_lesson(self) -> str:
        return (
            "Advanced Python training mode is active.\n\n"
            "Lesson path:\n"
            "1. Python data model: dunder methods, iteration protocol, context managers.\n"
            "2. Functional tools: closures, decorators, generators, itertools, functools.\n"
            "3. Object model: descriptors, properties, dataclasses, protocols, metaclasses.\n"
            "4. Async Python: coroutines, tasks, cancellation, timeouts, queues.\n"
            "5. Production quality: logging, typing, pytest, packaging, profiling, security.\n\n"
            "Example: a reusable timing context manager\n\n"
            "```python\n"
            "from contextlib import contextmanager\n"
            "from time import perf_counter\n\n"
            "@contextmanager\n"
            "def timer(label: str):\n"
            "    start = perf_counter()\n"
            "    try:\n"
            "        yield\n"
            "    finally:\n"
            "        elapsed = perf_counter() - start\n"
            "        print(f'{label}: {elapsed:.4f}s')\n\n"
            "with timer('work'):\n"
            "    total = sum(i * i for i in range(1_000_000))\n"
            "```\n\n"
            "Why this is advanced:\n"
            "- `@contextmanager` turns a generator into a context manager.\n"
            "- `yield` marks the protected block.\n"
            "- `finally` guarantees cleanup/reporting even if an exception happens.\n\n"
            "Practice challenge: write a `retry()` decorator that retries a function three times, "
            "logs each failure, and re-raises the final exception."
        )

    def save_generated_code(self, code: str) -> Dict:
        return code_utils.save_generated_code(code, self.gpu_available)

    def complete_workflow(self, user_request: str) -> Dict:
        print("\n" + "=" * 60)
        print("🚀 STARTING COMPLETE CODE GENERATION WORKFLOW")
        print("=" * 60)
        print(f"📝 User request: {user_request}")

        result = self.generate_code_from_search(user_request)

        if not result or not result.get('explanation'):
            return {'success': False, 'error': 'Failed to generate response'}

        print("\n" + "=" * 60)
        print("📚 INFORMATION ABOUT YOUR REQUEST")
        print("=" * 60)
        print(result['explanation'])
        print("=" * 60)

        if result.get('has_code'):
            user_choice = input("\n💭 Would you like me to create the code for you? (y/n): ").strip().lower()
            if user_choice == 'y':
                save_result = self.save_generated_code(result['code'])
                print(f"\n✅ Code saved to: {save_result['code_file']}")
                return {
                    'success': True,
                    'original_request': user_request,
                    'code_file': save_result['code_file'],
                    'clean_code_file': save_result['clean_code_file'],
                    'code': save_result['code'],
                    'syntax_valid': save_result['syntax_valid'],
                    'explanation': result['explanation'],
                }
            else:
                print("\n👍 Alright! Information provided above.")
                return {'success': True, 'explanation_only': True}
        else:
            print("\n⚠️ No code was generated for this request.")
            return {'success': True, 'explanation_only': True}

    def close(self):
        if getattr(self, 'conn', None):
            self.conn.close()
            self.conn = None
