"""Generate 4 'Demo explainer' MP4 clips (720p, H.264) from data/videos.json chapters.
Usage: python scripts/make_demo_videos.py   (needs Pillow + imageio-ffmpeg)"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS, CH_SEC = 1280, 720, 12, 6
INK, CLOTH, THREAD, ACCENT, NAVY = (32, 38, 64), (234, 238, 244), (196, 30, 92), (232, 160, 20), (28, 49, 94)

STEP_TEXT = {
    "upper_thread_breaking": ["Stop and switch the power off", "Re-thread the full thread path", "Loosen upper tension slightly",
                              "Fit a new needle, fully up", "Test stitch on scrap fabric"],
    "needle_breaking": ["Stop and switch the power off", "Remove all broken pieces", "Insert new needle, eye facing front",
                        "Check hoop is locked, design fits", "Test at low speed"],
    "design_misalignment": ["Stop and switch the power off", "Re-hoop fabric drum-tight", "Add the right stabilizer",
                            "Check frame clamps are locked", "Test stitch on same fabric"],
    "thread_nesting": ["Stop and switch the power off", "Cut away the thread nest", "Re-thread through tension discs",
                       "Clean area, re-insert bobbin", "Test stitch on scrap fabric"],
}


def font(size: int, bold: bool = False):
    for name in (["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"]):
        for base in ("/usr/share/fonts/truetype/dejavu/", "C:/Windows/Fonts/", ""):
            try:
                return ImageFont.truetype(base + name, size)
            except OSError:
                continue
    return ImageFont.load_default()


def dashed(d, pts, color, dash=18, gap=12, width=5, phase=0.0):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
        L = math.hypot(x2 - x1, y2 - y1)
        pos = -phase
        while pos < L:
            a, b = max(pos, 0), min(pos + dash, L)
            if b > a:
                d.line([(x1 + (x2 - x1) * a / L, y1 + (y2 - y1) * a / L), (x1 + (x2 - x1) * b / L, y1 + (y2 - y1) * b / L)],
                       fill=color, width=width)
            pos += dash + gap


def icon(d, kind: str, cx: int, cy: int, t: float):
    bob = math.sin(t * 6) * 10
    if kind in ("power",):
        d.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], outline=INK, width=10)
        d.rectangle([cx - 8, cy - 95, cx + 8, cy - 10], fill=CLOTH)
        d.rectangle([cx - 6, cy - 90, cx + 6, cy - 5], fill=THREAD)
    elif kind == "needle":
        d.polygon([(cx - 8, cy - 120 + bob), (cx + 8, cy - 120 + bob), (cx + 3, cy + 90 + bob), (cx, cy + 110 + bob), (cx - 3, cy + 90 + bob)], fill=INK)
        d.ellipse([cx - 4, cy + 60 + bob, cx + 4, cy + 78 + bob], fill=CLOTH)
        dashed(d, [(cx, cy + 69 + bob), (cx + 110, cy - 40), (cx + 160, cy - 110)], THREAD, phase=t * 60)
    elif kind == "hoop":
        d.ellipse([cx - 120, cy - 90, cx + 120, cy + 90], outline=NAVY, width=14)
        d.ellipse([cx - 104, cy - 74, cx + 104, cy + 74], outline=ACCENT, width=6)
        dashed(d, [(cx - 70, cy), (cx + 70, cy)], THREAD, phase=t * 60)
    elif kind == "bobbin":
        d.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], outline=INK, width=10)
        d.ellipse([cx - 55, cy - 55, cx + 55, cy + 55], fill=THREAD)
        d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=CLOTH)
    elif kind == "dial":
        d.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], outline=INK, width=10)
        a = -math.pi / 2 + math.sin(t * 2) * 0.6
        d.line([(cx, cy), (cx + 60 * math.cos(a), cy + 60 * math.sin(a))], fill=THREAD, width=10)
    else:  # test stitch / thread wave
        pts = [(cx - 160 + i * 20, cy + math.sin(i * 0.9 + t * 3) * 25) for i in range(17)]
        dashed(d, pts, THREAD, phase=t * 40)
        d.line([(cx - 170, cy + 60), (cx + 170, cy + 60)], fill=NAVY, width=4)


ICON_FOR = {"power off": "power", "re-thread": "needle", "tension": "dial", "new needle": "needle", "insert needle": "needle",
            "remove pieces": "needle", "check hoop": "hoop", "re-hoop": "hoop", "stabilizer": "hoop", "frame check": "hoop",
            "remove nest": "thread", "bobbin": "bobbin", "test stitch": "thread"}


def frame(title: str, n: int, total: int, label: str, text: str, t: float, prog: float) -> Image.Image:
    im = Image.new("RGB", (W, H), CLOTH)
    d = ImageDraw.Draw(im)
    dashed(d, [(30, 30), (W - 30, 30), (W - 30, H - 30), (30, H - 30), (30, 30)], NAVY, dash=14, gap=10, width=3)
    d.text((70, 60), title, font=font(34, True), fill=NAVY)
    d.text((W - 330, 64), "Demo explainer", font=font(26), fill=THREAD)
    d.text((70, 170), str(n), font=font(260, True), fill=THREAD)
    d.text((300, 230), label, font=font(54, True), fill=INK)
    words, line, lines = text.split(), "", []
    for w in words:
        if len(line + " " + w) > 26:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    lines.append(line)
    for i, ln in enumerate(lines):
        d.text((300, 320 + i * 52), ln, font=font(40), fill=INK)
    icon(d, ICON_FOR.get(label.lower(), "thread"), 1000, 380, t)
    d.rectangle([70, H - 90, W - 70, H - 78], fill=(205, 212, 224))
    d.rectangle([70, H - 90, 70 + int((W - 140) * prog), H - 78], fill=ACCENT)
    d.text((70, H - 70), f"Step {n} of {total}  |  SAMPLE: technician review required", font=font(22), fill=NAVY)
    return im


def render(v: dict, out: Path, ffmpeg: str) -> None:
    chapters, steps = v["chapters"], STEP_TEXT[v["fault_id"]]
    total_frames = len(chapters) * CH_SEC * FPS
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "30", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(total_frames):
        ci = i // (CH_SEC * FPS)
        t = i / FPS
        im = frame(v["title"].replace(" (Demo explainer)", ""), ci + 1, len(chapters), chapters[ci]["label"], steps[ci], t, i / total_frames)
        p.stdin.write(im.tobytes())
    p.stdin.close()
    p.wait()


def main() -> None:
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    vids = json.loads((ROOT / "data" / "videos.json").read_text(encoding="utf-8"))["videos"]
    for v in vids:
        if not v["video"].startswith("/media/videos/"):
            continue
        out = ROOT / "data" / "videos" / Path(v["video"]).name
        render(v, out, ffmpeg)
        print("wrote", out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
