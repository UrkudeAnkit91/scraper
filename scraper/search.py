import re
from typing import Callable, Dict, List, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from .config import (
    EXPLAINER_PREFIXES,
    EXPLAINER_STARTERS,
    KNOWN_SITES,
)


def is_explainer_question(query: str) -> bool:
    normalized = query.strip().lower()
    return normalized.startswith(EXPLAINER_STARTERS)


def extract_subject(query: str) -> str:
    normalized = query.strip().lower().rstrip('?.!')
    for prefix in EXPLAINER_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return re.sub(r'[^a-z0-9]+', '', normalized)


def dedupe_results(results: List[Dict]) -> List[Dict]:
    seen = set()
    deduped = []
    for result in results:
        url = result.get('url')
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(result)
    return deduped


def clean_duckduckgo_url(href: str) -> str:
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    if 'uddg' in query and query['uddg']:
        return unquote(query['uddg'][0])
    return href


def search_wikipedia(
    query: str, limit: int, get_json_fn: Callable
) -> List[Dict]:
    search_url = (
        "https://en.wikipedia.org/w/api.php"
        f"?action=query&list=search&format=json&srlimit={limit}&srsearch={quote_plus(query)}"
    )
    data, error = get_json_fn(search_url)
    if error:
        return []

    results = []
    for item in data.get('query', {}).get('search', [])[:limit]:
        title = item.get('title')
        if not title:
            continue
        snippet = BeautifulSoup(item.get('snippet', ''), 'html.parser').get_text(' ', strip=True)
        page_url = f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
        results.append({
            'title': title,
            'url': page_url,
            'snippet': snippet,
            'source': 'Wikipedia',
        })
    return results


def search_stackoverflow(
    query: str, limit: int, get_page_fn: Callable
) -> List[Dict]:
    url = f"https://stackoverflow.com/search?q={quote_plus(query)}"
    response, error = get_page_fn(url)
    if error:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    selectors = [
        '.s-post-summary--content-title a',
        'div.result-link a',
        'a.question-hyperlink',
    ]

    for selector in selectors:
        for link in soup.select(selector):
            href = link.get('href')
            title = link.get_text(' ', strip=True)
            if not href or not title:
                continue
            summary = link.find_parent(class_='s-post-summary')
            snippet_node = summary.select_one('.s-post-summary--content-excerpt') if summary else None
            results.append({
                'title': title,
                'url': urljoin('https://stackoverflow.com', href),
                'snippet': snippet_node.get_text(' ', strip=True) if snippet_node else '',
                'source': 'Stack Overflow',
            })
            if len(results) >= limit:
                return results
    return results


def search_direct_sites(
    query: str, limit: int, get_page_fn: Callable
) -> List[Dict]:
    subject = extract_subject(query)
    if not subject:
        return []

    candidate_urls = KNOWN_SITES.get(subject, [])
    if not candidate_urls and len(subject) >= 4:
        candidate_urls = [
            f"https://www.{subject}.com/",
            f"https://{subject}.com/",
        ]

    results = []
    for url in candidate_urls:
        if len(results) >= limit:
            break
        response, error = get_page_fn(url)
        if error:
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        title_node = soup.find('title')
        description_node = soup.find('meta', attrs={'name': 'description'})
        og_description_node = soup.find('meta', attrs={'property': 'og:description'})

        title = title_node.get_text(' ', strip=True) if title_node else url
        snippet = ''
        if description_node and description_node.get('content'):
            snippet = description_node['content'].strip()
        elif og_description_node and og_description_node.get('content'):
            snippet = og_description_node['content'].strip()

        results.append({
            'title': title,
            'url': url,
            'snippet': snippet,
            'source': 'Direct website',
        })
    return results


def search_duckduckgo(
    query: str, limit: int, get_page_fn: Callable
) -> List[Dict]:
    suffix = '' if is_explainer_question(query) else ' python code example'
    url = f"https://duckduckgo.com/html/?q={quote_plus(query + suffix)}"
    response, error = get_page_fn(url)
    if error:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    for result in soup.select('.result')[:limit]:
        link = result.select_one('.result__a')
        if not link:
            continue
        snippet_node = result.select_one('.result__snippet')
        href = link.get('href')
        title = link.get_text(' ', strip=True)
        if href and title:
            href = clean_duckduckgo_url(href)
            results.append({
                'title': title,
                'url': href,
                'snippet': snippet_node.get_text(' ', strip=True) if snippet_node else '',
                'source': 'DuckDuckGo',
            })
    return results


def search_bing(
    query: str, limit: int, get_page_fn: Callable
) -> List[Dict]:
    suffix = '' if is_explainer_question(query) else ' python code example'
    url = f"https://www.bing.com/search?q={quote_plus(query + suffix)}"
    response, error = get_page_fn(url)
    if error:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    for item in soup.select('li.b_algo')[:limit]:
        link = item.select_one('h2 a')
        if not link:
            continue
        snippet_node = item.select_one('.b_caption p')
        href = link.get('href')
        title = link.get_text(' ', strip=True)
        if href and title:
            results.append({
                'title': title,
                'url': href,
                'snippet': snippet_node.get_text(' ', strip=True) if snippet_node else '',
                'source': 'Bing',
            })
    return results
