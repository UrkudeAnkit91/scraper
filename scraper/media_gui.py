import threading
import os
from typing import Dict, Optional

from . import generation as gen_module
from .engine import InternetScraperAndCodeGenerator


class MediaGeneratorTab:
    def __init__(self, parent, ctk, generator: InternetScraperAndCodeGenerator,
                 fonts: dict, remember_font, set_text_fn):
        self.ctk = ctk
        self.generator = generator
        self.fonts = fonts
        self._remember_font = remember_font
        self._set_text = set_text_fn
        self.is_running = False
        self.last_image_path = None
        self.last_video_path = None
        self._build_ui(parent)

    def _build_ui(self, parent):
        ctk = self.ctk

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # -- Image Generation Section (left column) --
        img_frame = ctk.CTkFrame(main)
        img_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 8))
        img_frame.grid_columnconfigure(0, weight=1)
        img_frame.grid_rowconfigure(4, weight=1)

        img_label = ctk.CTkLabel(img_frame, text=" Image Generation")
        self._remember_font(img_label, 'section')
        img_label.grid(row=0, column=0, padx=14, pady=(14, 4), sticky="w")

        self.img_prompt = ctk.CTkEntry(
            img_frame,
            placeholder_text="e.g. a cat sitting on a beach, digital art",
            height=48,
        )
        self._remember_font(self.img_prompt, 'body')
        self.img_prompt.grid(row=1, column=0, padx=14, pady=6, sticky="ew")
        self.img_prompt.bind("<Return>", lambda _: self._start_image_gen())

        opt_row = ctk.CTkFrame(img_frame, fg_color="transparent")
        opt_row.grid(row=2, column=0, padx=14, pady=4, sticky="ew")
        opt_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(opt_row, text="Width:").grid(row=0, column=0, sticky="w")
        self.img_width = ctk.CTkOptionMenu(opt_row, values=["512", "768", "1024"], width=90)
        self.img_width.set("512")
        self.img_width.grid(row=0, column=1, padx=(0, 8))

        ctk.CTkLabel(opt_row, text="Height:").grid(row=0, column=2, sticky="w")
        self.img_height = ctk.CTkOptionMenu(opt_row, values=["512", "768", "1024"], width=90)
        self.img_height.set("512")
        self.img_height.grid(row=0, column=3)

        steps_row = ctk.CTkFrame(img_frame, fg_color="transparent")
        steps_row.grid(row=3, column=0, padx=14, pady=4, sticky="ew")
        steps_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(steps_row, text="Steps:").grid(row=0, column=0, sticky="w")
        self.img_steps = ctk.CTkSlider(steps_row, from_=5, to=50, number_of_steps=45)
        self.img_steps.set(25)
        self.img_steps.grid(row=0, column=1, padx=(8, 8), sticky="ew")
        self.img_steps_label = ctk.CTkLabel(steps_row, text="25")
        self.img_steps_label.grid(row=0, column=2, sticky="w")
        self.img_steps.configure(command=lambda v: self.img_steps_label.configure(text=str(int(v))))

        self.img_gen_btn = ctk.CTkButton(
            img_frame, text="Generate Image", height=48,
            command=self._start_image_gen,
        )
        self._remember_font(self.img_gen_btn, 'button')
        self.img_gen_btn.grid(row=4, column=0, padx=14, pady=10, sticky="ew")

        self.img_status = ctk.CTkTextbox(img_frame, wrap="word", height=80)
        self._remember_font(self.img_status, 'small')
        self.img_status.grid(row=5, column=0, padx=14, pady=(0, 14), sticky="ew")
        self._set_text(self.img_status, "Ready. Enter a prompt and click Generate Image.")

        self.img_preview_label = ctk.CTkLabel(img_frame, text="", fg_color="transparent")
        self.img_preview_label.grid(row=6, column=0, padx=14, pady=(0, 14))

        # -- Video Generation Section (right column) --
        vid_frame = ctk.CTkFrame(main)
        vid_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0))
        vid_frame.grid_columnconfigure(0, weight=1)
        vid_frame.grid_rowconfigure(4, weight=1)

        vid_label = ctk.CTkLabel(vid_frame, text=" Video Generation")
        self._remember_font(vid_label, 'section')
        vid_label.grid(row=0, column=0, padx=14, pady=(14, 4), sticky="w")

        self.vid_prompt = ctk.CTkEntry(
            vid_frame,
            placeholder_text="e.g. waves crashing on a shore, animation",
            height=48,
        )
        self._remember_font(self.vid_prompt, 'body')
        self.vid_prompt.grid(row=1, column=0, padx=14, pady=6, sticky="ew")
        self.vid_prompt.bind("<Return>", lambda _: self._start_video_gen())

        frames_row = ctk.CTkFrame(vid_frame, fg_color="transparent")
        frames_row.grid(row=2, column=0, padx=14, pady=4, sticky="ew")
        frames_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frames_row, text="Frames:").grid(row=0, column=0, sticky="w")
        self.vid_frames = ctk.CTkSlider(frames_row, from_=4, to=20, number_of_steps=16)
        self.vid_frames.set(8)
        self.vid_frames.grid(row=0, column=1, padx=(8, 8), sticky="ew")
        self.vid_frames_label = ctk.CTkLabel(frames_row, text="8")
        self.vid_frames_label.grid(row=0, column=2, sticky="w")
        self.vid_frames.configure(command=lambda v: self.vid_frames_label.configure(text=str(int(v))))

        self.vid_gen_btn = ctk.CTkButton(
            vid_frame, text="Generate Video", height=48,
            command=self._start_video_gen,
        )
        self._remember_font(self.vid_gen_btn, 'button')
        self.vid_gen_btn.grid(row=4, column=0, padx=14, pady=10, sticky="ew")

        self.vid_status = ctk.CTkTextbox(vid_frame, wrap="word", height=80)
        self._remember_font(self.vid_status, 'small')
        self.vid_status.grid(row=5, column=0, padx=14, pady=(0, 14), sticky="ew")
        self._set_text(self.vid_status, "Ready. Enter a prompt and click Generate Video.")

    # --- Image ---

    def _start_image_gen(self):
        if self.is_running:
            return
        prompt = self.img_prompt.get().strip()
        if not prompt:
            self._set_text(self.img_status, "Please enter a prompt first.")
            return

        self.is_running = True
        self.img_gen_btn.configure(state="disabled", text="Generating...")
        self._set_text(self.img_status, "Generating image, please wait...")

        threading.Thread(target=self._run_image_gen, args=(prompt,), daemon=True).start()

    def _run_image_gen(self, prompt: str):
        try:
            width = int(self.img_width.get())
            height = int(self.img_height.get())
            steps = int(self.img_steps.get())

            image = gen_module.generate_image(
                prompt=prompt,
                num_inference_steps=steps,
                width=width,
                height=height,
            )
            if image:
                info = gen_module.save_image(image, prompt)
                self.last_image_path = info["file_path"]
                msg = (f"Image saved: {info['file_path']}\n"
                       f"Size: {info['width']}x{info['height']}, {info['size_kb']}KB")
                self._show_image_preview(info["file_path"])
            else:
                msg = "Image generation failed. Check console for details."
        except Exception as e:
            msg = f"Error: {e}"

        self.app_ref = self.img_gen_btn
        self.app_ref.after(0, lambda: self._image_done(msg))

    def _image_done(self, msg: str):
        self._set_text(self.img_status, msg)
        self.img_gen_btn.configure(state="normal", text="Generate Image")
        self.is_running = False

    def _show_image_preview(self, path: str):
        try:
            from PIL import Image
            ctk = self.ctk
            pil_img = Image.open(path)
            max_w, max_h = 300, 300
            pil_img.thumbnail((max_w, max_h))
            ctk_img = ctk.CTkImage(pil_img, size=pil_img.size)
            self.img_preview_label.configure(image=ctk_img, text="")
        except Exception:
            pass

    # --- Video ---

    def _start_video_gen(self):
        if self.is_running:
            return
        prompt = self.vid_prompt.get().strip()
        if not prompt:
            self._set_text(self.vid_status, "Please enter a prompt first.")
            return

        self.is_running = True
        self.vid_gen_btn.configure(state="disabled", text="Generating...")
        self._set_text(self.vid_status, "Generating video frames, please wait...")

        threading.Thread(target=self._run_video_gen, args=(prompt,), daemon=True).start()

    def _run_video_gen(self, prompt: str):
        try:
            frames = int(self.vid_frames.get())
            video_path = gen_module.generate_video(prompt=prompt, num_frames=frames)
            if video_path:
                self.last_video_path = video_path
                size_kb = round(os.path.getsize(video_path) / 1024, 1)
                msg = f"Video saved: {video_path}\nSize: {size_kb}KB, Frames: {frames}"
            else:
                msg = "Video generation failed. Check console for details."
        except Exception as e:
            msg = f"Error: {e}"

        self.vid_gen_btn.after(0, lambda: self._video_done(msg))

    def _video_done(self, msg: str):
        self._set_text(self.vid_status, msg)
        self.vid_gen_btn.configure(state="normal", text="Generate Video")
        self.is_running = False
