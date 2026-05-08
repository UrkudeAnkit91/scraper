from typing import Dict, Optional, Tuple

import requests


def format_network_error(error: requests.RequestException) -> str:
    text = str(error)
    current = error
    while current:
        if (
            isinstance(current, PermissionError)
            or 'WinError 10013' in str(current)
            or '[Errno 10013]' in str(current)
            or any(isinstance(arg, PermissionError) for arg in getattr(current, 'args', ()))
        ):
            return (
                "Network blocked by Windows/firewall/antivirus "
                "(WinError 10013). Allow python.exe through the firewall."
            )
        current = getattr(current, '__cause__', None) or getattr(current, '__context__', None)

    if 'NameResolutionError' in text or 'getaddrinfo failed' in text:
        return "DNS lookup failed. Check your internet connection or DNS settings."
    if 'timed out' in text.lower():
        return "Request timed out. The site may be slow or blocking requests."
    return text


def get_page(
    url: str, headers: dict, timeout: int = 15
) -> Tuple[Optional[requests.Response], Optional[str]]:
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response, None

        if response.status_code in (202, 403, 429):
            reason = {
                202: "site returned a challenge/queued response",
                403: "site blocked automated access",
                429: "site rate-limited the request",
            }[response.status_code]
            error = f"HTTP {response.status_code} from {url} ({reason})"
        else:
            error = f"HTTP {response.status_code} from {url}"
        print(f"  {error}", flush=True)
        return None, error
    except requests.RequestException as e:
        error = format_network_error(e)
        print(f"  Search error: {error}", flush=True)
        return None, error


def get_json(
    url: str, headers: dict, timeout: int = 15
) -> Tuple[Optional[Dict], Optional[str]]:
    response, error = get_page(url, headers, timeout)
    if error:
        return None, error

    try:
        return response.json(), None
    except ValueError:
        error = f"Invalid JSON from {url}"
        print(f"  {error}", flush=True)
        return None, error
