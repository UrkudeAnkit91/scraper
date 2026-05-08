import sys


def _configure_output_encoding():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8')
            except (OSError, ValueError):
                pass


_configure_output_encoding()

from .engine import InternetScraperAndCodeGenerator

__all__ = ['InternetScraperAndCodeGenerator']
