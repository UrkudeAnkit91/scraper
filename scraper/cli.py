from .engine import InternetScraperAndCodeGenerator


def interactive_mode(use_ollama: bool = False):
    print("=" * 60)
    print("🤖 AI Code Generator (GPU Enhanced)")
    print("=" * 60)
    print("This tool will:")
    print("1. Generate detailed explanation using AI")
    print("2. Create code using AI reasoning")
    print("3. Use your GPU for heavy computations")
    print("=" * 60)

    generator = InternetScraperAndCodeGenerator(use_ollama=use_ollama)

    try:
        while True:
            print("\n" + "─" * 60)
            user_input = input("💭 What code would you like me to generate? (or 'quit' to exit): ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            if not user_input:
                print("⚠️ Please enter a valid request.")
                continue

            generator.complete_workflow(user_input)
            print("\n" + "─" * 60)
    finally:
        generator.close()
