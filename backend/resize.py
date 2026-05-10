"""Image resizing with configurable algorithm and size mode."""

from PIL import Image

_RESAMPLE_MAP = {
    "lanczos": Image.Resampling.LANCZOS,
    "bicubic": Image.Resampling.BICUBIC,
    "bilinear": Image.Resampling.BILINEAR,
    "nearest": Image.Resampling.NEAREST,
}


def get_target_size(
    images: list[Image.Image],
    mode: str,  # "max" | "min" | "manual" | "none"
    manual_px: int | None = None,
) -> int | None:
    """Return the target longest-edge in pixels, or None for no resize."""
    if mode == "none":
        return None

    longest_edges = [max(img.width, img.height) for img in images]

    if mode == "max":
        return max(longest_edges)
    elif mode == "min":
        return min(longest_edges)
    elif mode == "manual":
        if manual_px is None or manual_px <= 0:
            raise ValueError("manual_px must be a positive integer when mode='manual'")
        return manual_px
    else:
        raise ValueError(f"Unknown size mode: {mode!r}")


def resize_image(
    img: Image.Image,
    target_longest_edge: int,
    algorithm: str = "lanczos",
) -> Image.Image:
    """Resize img so its longest edge equals target_longest_edge, preserving aspect ratio."""
    resample = _resample_for(algorithm)
    w, h = img.width, img.height
    longest = max(w, h)
    if longest == target_longest_edge:
        return img
    scale = target_longest_edge / longest
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    return img.resize((new_w, new_h), resample)


def resize_all(
    images: list[Image.Image],
    mode: str,
    algorithm: str = "lanczos",
    manual_px: int | None = None,
) -> list[Image.Image]:
    target = get_target_size(images, mode, manual_px)
    if target is None:
        return images
    return [resize_image(img, target, algorithm) for img in images]


def _resample_for(algorithm: str) -> Image.Resampling:
    key = algorithm.lower()
    if key not in _RESAMPLE_MAP:
        raise ValueError(f"Unknown algorithm: {algorithm!r}. Choose from {list(_RESAMPLE_MAP)}")
    return _RESAMPLE_MAP[key]
