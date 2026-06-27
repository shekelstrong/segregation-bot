import subprocess
from typing import List, Iterable
from PIL import Image as PILImage

VALID_PRESETS = {
    "ultrafast", "superfast", "veryfast", "faster", "fast",
    "medium", "slow", "slower", "veryslow", "placebo"
}

def encode_visually_lossless_from_pil(
    frames: List[PILImage.Image],
    output_file: str,
    framerate: int = 60,
    crf: int = 12,
    preset: str = "fast",
):
    """
    Encode a sequence of Pillow images into a near–visually-lossless H.264 MP4
    using ffmpeg, without saving intermediate frame files.

    Args:
        frames:      list of PIL.Image.Image objects (all same size)
        output_file: target .mp4 filename (e.g. "out.mp4")
        framerate:   frames per second
        crf:         0–51 quality (lower ⇒ higher quality; 12 is near-visually-lossless)
        preset:      x264 preset (must be one of VALID_PRESETS)
    """

    if not frames:
        raise ValueError("frames list is empty")

    if preset not in VALID_PRESETS:
        raise ValueError(
            f"Invalid preset {preset!r}. Choose from: {', '.join(sorted(VALID_PRESETS))}"
        )

    # All frames must have the same size
    width, height = frames[0].size
    for i, f in enumerate(frames):
        if f.size != (width, height):
            raise ValueError(
                f"Frame {i} has size {f.size}, expected {(width, height)}"
            )

    # ffmpeg command: read raw RGB frames from stdin, encode as H.264, output MP4
    cmd = [
        "ffmpeg",
        "-y",                      # overwrite output
        "-f", "rawvideo",          # input format
        "-pix_fmt", "rgb24",       # pixel format of raw input
        "-s", f"{width}x{height}", # frame size
        "-r", str(framerate),      # input frame rate
        "-i", "-",                 # read from stdin
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",     # output pixel format
        output_file,
    ]

    # Open ffmpeg process with stdin pipe
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        for frame in frames:
            # Ensure RGB format; convert from RGBA or others if needed
            rgb = frame.convert("RGB")
            # Write raw bytes to ffmpeg stdin
            proc.stdin.write(rgb.tobytes())

        proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg exited with non-zero status {ret}")
    finally:
        # Just in case
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()


def iter_encode_visually_lossless_from_pil(
    frames: Iterable[PILImage.Image],
    output_file: str,
    framerate: int = 60,
    crf: int = 12,
    preset: str = "fast",
):
    """
    Encode a sequence of Pillow images into a near–visually-lossless H.264 MP4
    using ffmpeg, without saving intermediate frame files.

    `frames` can be *any iterable*: list, generator, etc.
    All frames must have the same size.
    """

    if preset not in VALID_PRESETS:
        raise ValueError(
            f"Invalid preset {preset!r}. Choose from: {', '.join(sorted(VALID_PRESETS))}"
        )

    frame_iter = iter(frames)

    try:
        # Get first frame to determine size and also verify we’re not empty
        first_frame = next(frame_iter)
    except StopIteration:
        raise ValueError("frames iterable is empty")

    if not isinstance(first_frame, PILImage.Image):
        raise TypeError(f"Expected PIL.Image.Image, got {type(first_frame)}")

    width, height = first_frame.size

    # ffmpeg command: read raw RGB frames from stdin, encode as H.264, output MP4
    cmd = [
        "ffmpeg",
        "-y",                      # overwrite output
        "-f", "rawvideo",          # input format
        "-pix_fmt", "rgb24",       # pixel format of raw input
        "-s", f"{width}x{height}", # frame size
        "-r", str(framerate),      # input frame rate
        "-i", "-",                 # read from stdin
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",     # output pixel format
        output_file,
    ]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def _write_frame(frame: PILImage.Image):
        # Check size consistency
        if frame.size != (width, height):
            raise ValueError(
                f"Frame has size {frame.size}, expected {(width, height)}"
            )
        # Ensure RGB format; convert from RGBA or others if needed
        rgb = frame.convert("RGB")
        # Write raw bytes to ffmpeg stdin
        proc.stdin.write(rgb.tobytes())
        # Free image memory as soon as we're done with it
        if hasattr(frame, "close"):
            frame.close()

    try:
        # Write first frame
        _write_frame(first_frame)

        # Write remaining frames from iterator
        for frame in frame_iter:
            _write_frame(frame)

        proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg exited with non-zero status {ret}")
    finally:
        # Just in case
        if proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except Exception:
                pass