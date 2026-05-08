import threading
from typing import Dict

from .engine import InternetScraperAndCodeGenerator
from .media_gui import MediaGeneratorTab


class ScraperGUI:
    def __init__(self, use_ollama: bool = False):
        try:
            import customtkinter as ctk
            from tkinter import messagebox
        except ImportError as e:
            raise RuntimeError("Install customtkinter with: pip install customtkinter") from e

        self.ctk = ctk
        self.messagebox = messagebox
        self.generator = InternetScraperAndCodeGenerator(use_ollama=use_ollama)
        self.current_result = None
        self.is_running = False
        self.font_scale = 1
        self.fonts = {}
        self.font_widgets = []

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.app = ctk.CTk()
        self.app.title("AI Internet Scraper & Code Generator")
        self.app.geometry("1220x820")
        self.app.minsize(1050, 700)
        self.app.protocol("WM_DELETE_WINDOW", self._on_close)

        self._create_fonts()
        self._build_layout()

    def _font_size(self, base: int) -> int:
        return base + self.font_scale

    def _create_fonts(self):
        ctk = self.ctk
        self.fonts = {
            'title': ctk.CTkFont(size=self._font_size(30), weight="bold"),
            'section': ctk.CTkFont(size=self._font_size(22), weight="bold"),
            'body': ctk.CTkFont(size=self._font_size(19)),
            'small': ctk.CTkFont(size=self._font_size(16)),
            'button': ctk.CTkFont(size=self._font_size(17), weight="bold"),
            'code': ctk.CTkFont(family="Consolas", size=self._font_size(18)),
        }

    def _remember_font(self, widget, font_key: str):
        self.font_widgets.append((widget, font_key))
        widget.configure(font=self.fonts[font_key])
        return widget

    def _build_layout(self):
        ctk = self.ctk

        self.app.grid_columnconfigure(0, weight=1)
        self.app.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.app, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        title = ctk.CTkLabel(header, text="AI Internet Scraper & Code Generator")
        self._remember_font(title, 'title')
        title.grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

        zoom_row = ctk.CTkFrame(header, fg_color="transparent")
        zoom_row.grid(row=0, column=1, rowspan=2, padx=20, pady=14, sticky="e")

        self.zoom_out_button = ctk.CTkButton(
            zoom_row, text="A-", width=56, height=40,
            command=lambda: self._change_font_scale(-2),
        )
        self._remember_font(self.zoom_out_button, 'button')
        self.zoom_out_button.grid(row=0, column=0, padx=(0, 8))

        self.zoom_in_button = ctk.CTkButton(
            zoom_row, text="A+", width=56, height=40,
            command=lambda: self._change_font_scale(2),
        )
        self._remember_font(self.zoom_in_button, 'button')
        self.zoom_in_button.grid(row=0, column=1)

        self.status_label = ctk.CTkLabel(
            header, text=self._initial_status_text(), text_color="#a9b7c6",
        )
        self._remember_font(self.status_label, 'small')
        self.status_label.grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        self.tabview = ctk.CTkTabview(self.app)
        self.tabview.grid(row=1, column=0, padx=18, pady=(0, 18), sticky="nsew")
        self.tabview.grid_columnconfigure(0, weight=1)
        self.tabview.grid_rowconfigure(0, weight=1)

        # -- Code Generator Tab --
        code_tab = self.tabview.add("Code Generator")
        code_tab.grid_columnconfigure(0, weight=1)
        code_tab.grid_columnconfigure(1, weight=1)
        code_tab.grid_rowconfigure(1, weight=1)

        input_frame = ctk.CTkFrame(code_tab)
        input_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        input_frame.grid_columnconfigure(0, weight=1)
        for i in range(1, 5):
            input_frame.grid_columnconfigure(i, weight=0)

        self.query_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Ask something like: what is api? or create a calculator in Python",
            height=54,
        )
        self._remember_font(self.query_entry, 'body')
        self.query_entry.grid(row=0, column=0, padx=(14, 10), pady=14, sticky="ew")
        self.query_entry.bind("<Return>", lambda _event: self._start_generation())

        self.generate_button = ctk.CTkButton(
            input_frame, text="Generate", width=120, height=54,
            command=self._start_generation,
        )
        self._remember_font(self.generate_button, 'button')
        self.generate_button.grid(row=0, column=1, padx=(0, 8), pady=14)

        self.provider_menu = ctk.CTkOptionMenu(
            input_frame,
            values=["OpenRouter", "Ollama"],
            command=self._update_provider,
            width=130, height=54,
        )
        self.provider_menu.set("Ollama" if self.generator.use_ollama else "OpenRouter")
        self._remember_font(self.provider_menu, 'button')
        self.provider_menu.configure(dropdown_font=self.fonts['body'])
        self.provider_menu.grid(row=0, column=2, padx=(0, 8), pady=14)

        self.model_menu = ctk.CTkOptionMenu(
            input_frame,
            values=list(self.generator.model_profiles.keys()),
            command=self._update_model_profile,
            width=140, height=54,
        )
        self.model_menu.set(self.generator.ai_profile)
        self._remember_font(self.model_menu, 'button')
        self.model_menu.configure(dropdown_font=self.fonts['body'])
        self.model_menu.grid(row=0, column=3, padx=(0, 14), pady=14)

        left = ctk.CTkFrame(code_tab)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        explanation_label = ctk.CTkLabel(left, text="Explanation")
        self._remember_font(explanation_label, 'section')
        explanation_label.grid(row=0, column=0, padx=14, pady=(14, 8), sticky="w")
        self.explanation_box = ctk.CTkTextbox(left, wrap="word")
        self._remember_font(self.explanation_box, 'body')
        self.explanation_box.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        self._set_text(self.explanation_box, "Enter a request and click Generate.")

        right = ctk.CTkFrame(code_tab)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_rowconfigure(3, weight=1)

        code_label = ctk.CTkLabel(right, text="Generated Code")
        self._remember_font(code_label, 'section')
        code_label.grid(row=0, column=0, padx=14, pady=(14, 8), sticky="w")
        self.code_box = ctk.CTkTextbox(right, wrap="none")
        self._remember_font(self.code_box, 'code')
        self.code_box.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="nsew")
        self._set_text(self.code_box, "Generated code will appear here.")

        button_row = ctk.CTkFrame(right, fg_color="transparent")
        button_row.grid(row=2, column=0, padx=14, pady=(0, 10), sticky="ew")
        button_row.grid_columnconfigure(0, weight=1)

        self.save_button = ctk.CTkButton(
            button_row, text="Save Code", width=110, state="disabled",
            command=self._save_code,
        )
        self._remember_font(self.save_button, 'button')
        self.save_button.grid(row=0, column=1, sticky="e")

        results_label = ctk.CTkLabel(right, text="Search Results")
        self._remember_font(results_label, 'section')
        results_label.grid(row=3, column=0, padx=14, pady=(0, 8), sticky="sw")
        self.results_box = ctk.CTkTextbox(right, wrap="word", height=170)
        self._remember_font(self.results_box, 'small')
        self.results_box.grid(row=4, column=0, padx=14, pady=(0, 14), sticky="ew")
        self._set_text(self.results_box, "Search links will appear here.")

        # -- Media Generator Tab --
        media_tab = self.tabview.add("Media Generator")
        media_tab.grid_columnconfigure(0, weight=1)
        media_tab.grid_rowconfigure(0, weight=1)
        self.media_tab = MediaGeneratorTab(
            media_tab, ctk, self.generator, self.fonts,
            self._remember_font, self._set_text,
        )

    def _change_font_scale(self, delta: int):
        self.font_scale = max(0, min(12, self.font_scale + delta))
        self._create_fonts()
        for widget, font_key in self.font_widgets:
            widget.configure(font=self.fonts[font_key])
        if hasattr(self, 'model_menu'):
            self.model_menu.configure(dropdown_font=self.fonts['body'])

    def _update_model_profile(self, profile: str):
        self.generator.set_ai_profile(profile)
        self.status_label.configure(text=self._initial_status_text())

    def _update_provider(self, provider: str):
        self.generator.set_provider(provider)
        self.status_label.configure(text=self._initial_status_text())

    def _initial_status_text(self) -> str:
        provider = "Ollama" if self.generator.use_ollama else "OpenRouter"
        api_state = "key ready" if self.generator.api_key else "no API key"
        gpu_state = "GPU ready" if self.generator.gpu_available else "CPU mode"
        return f"{provider} • {api_state} • {gpu_state} • Profile: {self.generator.ai_profile}"

    def _start_generation(self):
        if self.is_running:
            return
        query = self.query_entry.get().strip()
        if not query:
            self.messagebox.showwarning("Missing request", "Enter what you want to search or generate.")
            return

        self.is_running = True
        self.current_result = None
        if hasattr(self, 'model_menu'):
            self.generator.set_ai_profile(self.model_menu.get())
        if hasattr(self, 'provider_menu'):
            self.generator.set_provider(self.provider_menu.get())
        self.generate_button.configure(state="disabled", text="Working...")
        self.save_button.configure(state="disabled")
        self.status_label.configure(text="Searching and generating...")
        self._set_text(self.explanation_box, "Working...")
        self._set_text(self.code_box, "")
        self._set_text(self.results_box, "")

        worker = threading.Thread(target=self._run_generation, args=(query,), daemon=True)
        worker.start()

    def _run_generation(self, query: str):
        try:
            result = self.generator.generate_code_from_search(query)
        except Exception as e:
            result = {'error': str(e), 'explanation': f"Something went wrong:\n{e}", 'code': None, 'has_code': False}
        self.app.after(0, lambda: self._show_result(result))

    def _show_result(self, result: Dict):
        self.current_result = result
        explanation = result.get('explanation') or result.get('error') or "No explanation returned."
        code = result.get('code') or ""
        self._set_text(self.explanation_box, explanation)
        self._set_text(self.code_box, code or "No code was generated for this request.")
        self._set_text(self.results_box, self._format_search_results())
        self.save_button.configure(state="normal" if code else "disabled")
        self.generate_button.configure(state="normal", text="Generate")
        self.status_label.configure(text=self._initial_status_text())
        self.is_running = False

    def _format_search_results(self) -> str:
        if not self.generator.search_results:
            return self.generator.last_search_error or "No search results found."
        lines = []
        for index, item in enumerate(self.generator.search_results, start=1):
            lines.append(f"{index}. [{item.get('source', 'Web')}] {item.get('title', 'Untitled')}")
            lines.append(f"   {item.get('url', '')}")
            if item.get('snippet'):
                lines.append(f"   {item['snippet']}")
            lines.append("")
        return "\n".join(lines).strip()

    def _save_code(self):
        if not self.current_result or not self.current_result.get('code'):
            self.messagebox.showinfo("No code", "There is no generated code to save yet.")
            return
        try:
            save_result = self.generator.save_generated_code(self.current_result['code'])
        except Exception as e:
            self.messagebox.showerror("Save failed", str(e))
            return
        message = (
            f"Saved:\n{save_result['code_file']}\n{save_result['clean_code_file']}\n\n"
            f"Syntax valid: {save_result['syntax_valid']}"
        )
        self.messagebox.showinfo("Code saved", message)

    def _set_text(self, widget, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

    def _on_close(self):
        self.generator.close()
        self.app.destroy()

    def run(self):
        self.app.mainloop()


def gui_mode(use_ollama: bool = False):
    try:
        ScraperGUI(use_ollama=use_ollama).run()
    except RuntimeError as e:
        print(e, flush=True)
