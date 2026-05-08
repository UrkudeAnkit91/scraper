import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

API_URL = 'https://openrouter.ai/api/v1/chat/completions'

DB_PATH = 'search_history.db'

COMPLEX_KEYWORDS = (
    'neural', 'ai', 'machine learning', 'deep learning',
    'brain', 'network', 'algorithm', 'gpu', 'cuda',
    'architecture', 'debug', 'optimize',
)

CODE_WORDS = (
    'create', 'build', 'make', 'generate', 'write',
    'code', 'script', 'program', 'app', 'gui',
    'website', 'calculator', 'bot', 'automation', 'scraper',
)

ADVANCED_PYTHON_SIGNALS = (
    'advanced python', 'expert python', 'teach python', 'learn python',
    'decorator', 'descriptor', 'metaclass', 'asyncio',
    'generator', 'context manager', 'type hint', 'typing',
    'dataclass', 'performance', 'profiling', 'concurrency',
    'multiprocessing', 'pytest', 'packaging',
)

EXPLAINER_STARTERS = (
    'what is ', 'what are ', 'explain ', 'define ',
    'meaning of ', 'tell me about ',
)

EXPLAINER_PREFIXES = (
    'what is an ', 'what is a ', 'what is ',
    'what are ', 'explain ', 'define ',
    'meaning of ', 'tell me about ',
)

KNOWN_SITES = {
    'hotelkey': ['https://www.hotelkeyapp.com/'],
}

CUDA_MAP = {
    '124': 'cu124',
    '123': 'cu123',
    '122': 'cu122',
    '121': 'cu121',
}

OPENROUTER_HEADERS = {
    'Authorization': '',
    'Content-Type': 'application/json',
    'HTTP-Referer': 'http://localhost',
    'X-Title': 'Python Code Generator',
}
