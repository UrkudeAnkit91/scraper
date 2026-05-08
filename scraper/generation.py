import os
import re
import time
from typing import Dict, List, Optional, Tuple

IMAGE_WORDS = (
    "generate an image", "create an image", "make an image", "draw",
    "generate a picture", "create a picture", "paint",
    "generate a photo", "create a photo",
    "generate a image", "create a image",
    "generate artwork", "generate art",
    "illustration", "digital art",
    "wallpaper", "poster",
)

VIDEO_WORDS = (
    "generate a video", "create a video", "make a video",
    "generate video", "create video",
    "animation", "animate", "anim",
    "generate a clip", "short video", "video clip",
)

_sd_pipeline = None


def is_image_request(query: str) -> bool:
    q = query.lower().strip()
    if q.startswith(("img:", "image:", "--img")):
        return True
    return any(word in q for word in IMAGE_WORDS)


def is_video_request(query: str) -> bool:
    q = query.lower().strip()
    if q.startswith(("vid:", "video:", "--vid")):
        return True
    return any(word in q for word in VIDEO_WORDS)


def _detect_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _get_pipeline():
    global _sd_pipeline
    if _sd_pipeline is not None:
        return _sd_pipeline

    device = _detect_device()
    print(f"  Loading Stable Diffusion on {device.upper()}...", flush=True)

    if device == "cpu":
        print("  ⚠️  GPU (CUDA) not available in this Python environment.", flush=True)
        print("     Image generation will run on CPU and will be VERY slow.", flush=True)
        print("     For GPU acceleration, use Python 3.12 with CUDA PyTorch:", flush=True)
        print("     pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124", flush=True)

    try:
        from diffusers import StableDiffusionPipeline
        import torch

        model_id = "runwayml/stable-diffusion-v1-5"
        if device == "cpu":
            _sd_pipeline = StableDiffusionPipeline.from_pretrained(
                model_id, torch_dtype=torch.float32
            )
        else:
            _sd_pipeline = StableDiffusionPipeline.from_pretrained(
                model_id, torch_dtype=torch.float16, safety_checker=None
            )
            _sd_pipeline.enable_attention_slicing()

        _sd_pipeline = _sd_pipeline.to(device)
        print(f"  ✅ Stable Diffusion loaded on {device.upper()}", flush=True)
        return _sd_pipeline
    except Exception as e:
        print(f"  ❌ Failed to load Stable Diffusion: {e}", flush=True)
        raise


def generate_image(
    prompt: str,
    negative_prompt: str = "",
    num_inference_steps: int = 25,
    width: int = 512,
    height: int = 512,
    seed: Optional[int] = None,
):
    print(f"🎨 Generating image: {prompt[:60]}...", flush=True)

    try:
        pipeline = _get_pipeline()
    except Exception as e:
        print(f"  ❌ Cannot generate image: {e}", flush=True)
        return None

    generator = None
    if seed is not None:
        import torch
        generator = torch.Generator(device=_detect_device()).manual_seed(seed)

    try:
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt or None,
            num_inference_steps=num_inference_steps,
            width=width,
            height=height,
            generator=generator,
        )
        image = result.images[0]
        print(f"  ✅ Image generated: {image.size}", flush=True)
        return image
    except Exception as e:
        print(f"  ❌ Image generation failed: {e}", flush=True)
        return None


def generate_video(
    prompt: str,
    num_frames: int = 8,
    num_inference_steps: int = 20,
    seed: Optional[int] = None,
) -> Optional[str]:
    print(f"🎬 Generating video: {prompt[:60]}... ({num_frames} frames)", flush=True)

    try:
        from PIL import Image
        import cv2
    except ImportError as e:
        print(f"  ❌ Missing dependency for video: {e}", flush=True)
        return None

    try:
        pipeline = _get_pipeline()
    except Exception as e:
        print(f"  ❌ Cannot generate video: {e}", flush=True)
        return None

    import torch
    device = _detect_device()
    base_seed = seed or int(time.time())

    frames = []
    prompt_variations = [
        f"{prompt}, frame {i+1} of {num_frames}" for i in range(num_frames)
    ]

    for i, var_prompt in enumerate(prompt_variations):
        print(f"    Frame {i+1}/{num_frames}...", flush=True)
        frame_seed = base_seed + i
        g = torch.Generator(device=device).manual_seed(frame_seed)

        try:
            result = pipeline(
                prompt=var_prompt,
                num_inference_steps=num_inference_steps,
                width=512,
                height=512,
                generator=g,
            )
            frames.append(np.array(result.images[0]))
        except Exception as e:
            print(f"    ⚠️ Frame {i+1} failed: {e}", flush=True)
            continue

    if not frames:
        print("  ❌ No frames generated", flush=True)
        return None

    timestamp = int(time.time())
    video_path = f"generated_video_{timestamp}.mp4"

    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 2.0, (w, h))

    for frame in frames:
        rgb = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        for _ in range(3):
            out.write(rgb)

    out.release()
    print(f"  ✅ Video saved: {video_path} ({len(frames)} frames)", flush=True)
    return video_path


def save_image(image, prompt: str) -> Dict:
    timestamp = int(time.time())
    safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", prompt[:30].strip().lower()).strip("_") or "image"
    filename = f"generated_{safe_name}_{timestamp}.png"

    image.save(filename)
    print(f"  💾 Image saved: {filename}", flush=True)

    import os
    size_kb = os.path.getsize(filename) / 1024
    return {
        "file_path": filename,
        "size_kb": round(size_kb, 1),
        "width": image.width,
        "height": image.height,
    }
