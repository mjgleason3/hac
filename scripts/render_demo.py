#!/usr/bin/env python3
"""Render the HAC README demo as MP4 and an inline animated GIF."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - developer convenience
    raise SystemExit("Pillow is required: python3 -m pip install -e '.[media]'") from exc


WIDTH, HEIGHT, FPS, DURATION = 1280, 720, 30, 12
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
UI_FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MONO_FONT = "/System/Library/Fonts/Menlo.ttc"

BG = "#07111f"
PANEL = "#0f1d32"
LINE = "#334155"
CYAN = "#67e8f9"
PURPLE = "#a78bfa"
GREEN = "#22c55e"
GREEN_LIGHT = "#86efac"
RED = "#fb7185"
WHITE = "#f8fafc"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
DIM = "#64748b"


def rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    path = MONO_FONT if mono else BOLD_FONT if bold else UI_FONT
    return ImageFont.truetype(path, size=size)


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def reveal(t: float, start: float, duration: float = 0.25) -> int:
    return round(255 * ease((t - start) / duration))


def scene_alpha(t: float, start: float, end: float, fade: float = 0.22) -> int:
    return min(reveal(t, start, fade), reveal(end - t, 0, fade))


def apply_opacity(layer: Image.Image, opacity: int) -> Image.Image:
    if opacity >= 255:
        return layer
    result = layer.copy()
    alpha = result.getchannel("A").point(lambda value: value * opacity // 255)
    result.putalpha(alpha)
    return result


def put_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    size: int,
    color: str = TEXT,
    *,
    bold: bool = False,
    mono: bool = False,
    alpha: int = 255,
) -> None:
    draw.text(xy, value, font=font(size, bold=bold, mono=mono), fill=rgba(color, alpha))


def card(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    accent: str = LINE,
    *,
    fill: str = PANEL,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(bounds, radius=18, fill=rgba(fill, 248), outline=rgba(accent), width=width)


def base_frame(t: float) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    for x in range(0, WIDTH, 80):
        draw.line((x, 0, x, HEIGHT), fill="#0d1b2c", width=1)
    for y in range(0, HEIGHT, 80):
        draw.line((0, y, WIDTH, y), fill="#0d1b2c", width=1)
    draw.rectangle((0, 0, WIDTH, 7), fill=CYAN)
    draw.rectangle((0, 7, round(WIDTH * t / DURATION), 11), fill=PURPLE)
    put_text(draw, (54, 34), "HAC", 30, CYAN, bold=True)
    put_text(draw, (128, 41), "HIERARCHICAL AGENT CONTRACTS", 17, MUTED)
    return image


def scene_one(t: float) -> Image.Image:
    layer = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(layer)
    nodes = [
        ((164, 160, 256, 214), CYAN, "HUMAN INTENT", (174, 178), 13),
        ((76, 292, 168, 346), PURPLE, "SERVICE", (93, 310), 13),
        ((252, 292, 344, 346), PURPLE, "SERVICE", (269, 310), 13),
        ((94, 424, 150, 466), GREEN, "TASK", (105, 438), 12),
        ((270, 424, 326, 466), GREEN, "TASK", (281, 438), 12),
    ]
    draw.line((210, 214, 210, 268), fill=rgba(LINE), width=3)
    draw.line((122, 268, 298, 268), fill=rgba(LINE), width=3)
    draw.line((122, 268, 122, 292), fill=rgba(LINE), width=3)
    draw.line((298, 268, 298, 292), fill=rgba(LINE), width=3)
    draw.line((122, 346, 122, 424), fill=rgba(LINE), width=3)
    draw.line((298, 346, 298, 424), fill=rgba(LINE), width=3)
    for bounds, accent, label, position, size in nodes:
        draw.rounded_rectangle(bounds, radius=12, fill=rgba("#0b1220"), outline=rgba(accent), width=3)
        put_text(draw, position, label, size, TEXT, bold=True)
    put_text(draw, (438, 196), "INTENT DESCENDS.", 54, WHITE, bold=True)
    put_text(draw, (438, 268), "EVIDENCE RETURNS.", 54, PURPLE, bold=True)
    put_text(draw, (442, 360), "Authority only narrows.", 27, TEXT)
    put_text(
        draw,
        (442, 414),
        "formal intent  /  bounded authority  /  runtime evidence",
        18,
        CYAN,
        mono=True,
    )
    return apply_opacity(layer, scene_alpha(t, 0, 2.6))


def scene_two(t: float) -> Image.Image:
    layer = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(layer)
    put_text(draw, (54, 99), "A CONTRACT FIREWALL BEFORE EVERY SIDE EFFECT", 25, WHITE, bold=True)

    card(draw, (54, 154, 364, 558))
    put_text(draw, (82, 184), "PROPOSED ACTION", 16, MUTED, bold=True)
    put_text(draw, (82, 235), "agent:refund-specialist", 18, TEXT, mono=True)
    put_text(draw, (82, 291), "issue_refund", 30, WHITE, mono=True)
    put_text(draw, (82, 342), "$300  ·  ticket:99", 23, RED, mono=True)
    draw.rounded_rectangle((82, 438, 334, 498), radius=12, fill=rgba("#3b1220"))
    put_text(draw, (106, 457), "UNSAFE PROPOSAL", 19, "#fecdd3", bold=True)

    card(draw, (402, 154, 902, 558), CYAN)
    put_text(draw, (432, 184), "EFFECTIVE CONTRACT", 16, CYAN, bold=True)
    checks = [
        (3.10, 239, "01  identity_verified?", "NO"),
        (3.55, 329, "02  inherited · verify first", "FAIL"),
        (4.00, 419, "03  leaf limit · <= $250", "FAIL"),
    ]
    for at, y, label, result in checks:
        alpha = reveal(t, at)
        put_text(draw, (432, y), label, 21, TEXT, mono=True, alpha=alpha)
        put_text(draw, (806, y), result, 18, RED, mono=True, alpha=alpha)
        if y < 400:
            draw.line((432, y + 56, 872, y + 56), fill=rgba(LINE, alpha), width=1)
    put_text(
        draw,
        (432, 510),
        "ancestor rules cannot be dropped or rewritten",
        17,
        MUTED,
        alpha=reveal(t, 4.35),
    )

    card(draw, (944, 154, 1226, 558), RED, fill="#310f1b", width=3)
    result_alpha = reveal(t, 4.55)
    put_text(draw, (1022, 199), "DECISION", 17, "#fecdd3", bold=True, alpha=result_alpha)
    put_text(draw, (985, 285), "BLOCK", 53, RED, bold=True, alpha=result_alpha)
    put_text(draw, (1001, 386), "No side effect", 22, WHITE, alpha=result_alpha)
    put_text(draw, (984, 429), "Rule-level evidence", 19, TEXT, alpha=result_alpha)
    return apply_opacity(layer, scene_alpha(t, 2.3, 6.35))


def scene_three(t: float) -> Image.Image:
    layer = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(layer)
    put_text(draw, (54, 99), "THE SAME POLICY ALLOWS COMPLIANT WORK", 25, WHITE, bold=True)

    card(draw, (54, 154, 554, 558))
    put_text(draw, (84, 184), "OBSERVED TRACE", 16, MUTED, bold=True)
    draw.line((85, 245, 85, 424), fill=rgba(LINE), width=3)
    trace = [
        (6.45, 245, GREEN, "00:05  verify_identity", "ticket:42"),
        (6.85, 353, CYAN, "00:12  issue_refund", "$75  ·  ticket:42"),
    ]
    for at, y, accent, label, detail in trace:
        alpha = reveal(t, at)
        draw.rounded_rectangle((74, y, 96, y + 22), radius=5, fill=rgba(accent, alpha))
        put_text(draw, (119, y - 5), label, 22, TEXT, mono=True, alpha=alpha)
        put_text(draw, (119, y + 34), detail, 17, accent, mono=True, alpha=alpha)
    put_text(
        draw,
        (84, 492),
        "History is part of the decision.",
        21,
        TEXT,
        alpha=reveal(t, 7.1),
    )

    card(draw, (592, 154, 982, 558), CYAN)
    put_text(draw, (622, 184), "CONTRACT CHECK", 16, CYAN, bold=True)
    checks = [
        (7.25, 246, "[ok] identity verified"),
        (7.48, 306, "[ok] inherited rules"),
        (7.71, 366, "[ok] $75 <= $250"),
        (7.94, 426, "[ok] budget available"),
    ]
    for at, y, label in checks:
        put_text(draw, (622, y), label, 20, GREEN_LIGHT, mono=True, alpha=reveal(t, at))

    card(draw, (1020, 154, 1226, 558), GREEN, fill="#0d2c22", width=3)
    result_alpha = reveal(t, 8.05)
    put_text(draw, (1070, 199), "DECISION", 17, "#bbf7d0", bold=True, alpha=result_alpha)
    put_text(draw, (1048, 285), "ALLOW", 43, GREEN, bold=True, alpha=result_alpha)
    put_text(draw, (1050, 386), "Release to tool", 18, WHITE, alpha=result_alpha)
    return apply_opacity(layer, scene_alpha(t, 6.0, 9.55))


def scene_four(t: float) -> Image.Image:
    layer = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(layer)
    put_text(draw, (54, 99), "ONE CONTROL PLANE. EVERY CONTRACT.", 31, WHITE, bold=True)
    put_text(draw, (56, 148), "A prototype for inspectable multi-agent governance", 21, MUTED)
    metrics = [
        (54, CYAN, "4 / 4", "unsafe attempts blocked", 9.6),
        (469, PURPLE, "0 / 3", "false blocks", 9.82),
        (884, GREEN, "2 / 2", "delegation faults found", 10.04),
    ]
    for x, accent, value, label, at in metrics:
        alpha = reveal(t, at)
        card(draw, (x, 216, x + 342, 404), accent)
        put_text(draw, (x + 30, 248), value, 48, accent, bold=True, alpha=alpha)
        put_text(draw, (x + 32, 316), label, 21, TEXT, alpha=alpha)
        put_text(draw, (x + 32, 355), "synthetic fixture", 16, DIM, alpha=alpha)
    put_text(
        draw,
        (233, 486),
        "Intent descends.  Evidence returns.  Authority only narrows.",
        27,
        WHITE,
        alpha=reveal(t, 10.15),
    )
    put_text(
        draw,
        (334, 552),
        "github.com/mjgleason3/hac",
        20,
        CYAN,
        mono=True,
        alpha=reveal(t, 10.35),
    )
    return apply_opacity(layer, scene_alpha(t, 9.2, 12.25))


def render_frame(t: float) -> Image.Image:
    image = base_frame(t).convert("RGBA")
    for scene in (scene_one(t), scene_two(t), scene_three(t), scene_four(t)):
        image = Image.alpha_composite(image, scene)
    if t < 0.25:
        image = apply_opacity(image, round(255 * t / 0.25))
    if t > 11.7:
        image = apply_opacity(image, round(255 * (12 - t) / 0.3))
    background = Image.new("RGBA", image.size, rgba(BG))
    return Image.alpha_composite(background, image).convert("RGB")


def render(mp4_path: Path, gif_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise SystemExit("ffmpeg is required to render the demo")
    ASSETS.mkdir(exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(mp4_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for index in range(FPS * DURATION):
            process.stdin.write(render_frame(index / FPS).tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise SystemExit("ffmpeg failed while encoding MP4")

    gif_command = [
        ffmpeg,
        "-y",
        "-i",
        str(mp4_path),
        "-vf",
        (
            "fps=10,scale=800:-1:flags=lanczos,split[s0][s1];"
            "[s0]palettegen=max_colors=96:stats_mode=diff[p];"
            "[s1][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle"
        ),
        "-loop",
        "0",
        str(gif_path),
    ]
    subprocess.run(gif_command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mp4", type=Path, default=ASSETS / "hac-demo.mp4")
    parser.add_argument("--gif", type=Path, default=ASSETS / "hac-demo.gif")
    args = parser.parse_args()
    render(args.mp4, args.gif)
    print(f"Rendered {args.mp4}")
    print(f"Rendered {args.gif}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
