import sys

from .cli import interactive_mode
from .engine import InternetScraperAndCodeGenerator
from .gui import gui_mode


def main():
    use_ollama = '--ollama' in sys.argv

    if '--cli' in sys.argv:
        interactive_mode(use_ollama=use_ollama)
    elif '--test' in sys.argv:
        generator = InternetScraperAndCodeGenerator(use_ollama=use_ollama)
        try:
            generator.complete_workflow("create a neural network for image classification")
        finally:
            generator.close()
    else:
        gui_mode(use_ollama=use_ollama)


if __name__ == "__main__":
    main()
