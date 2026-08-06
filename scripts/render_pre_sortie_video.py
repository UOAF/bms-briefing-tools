#!/usr/bin/env python3
"""Render a cinematic tactical pre-sortie briefing video from BMS brief assets.

This is intentionally asset-clean: it uses the repo's generated map images,
simple HUD-style graphics, and mission text. It does not use any third-party
game logos, audio, or copyrighted art.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import json
import math
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


WIDTH = 1920
HEIGHT = 1080
FPS = 30


@lru_cache(maxsize=None)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


FONT_CONDENSED = r"C:\Windows\Fonts\bahnschrift.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\arial.ttf"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if draw.textlength(candidate, font=fnt) <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def read_section(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}\s*$", re.M)
    match = pattern.search(markdown)
    if not match:
        return ""
    next_match = re.search(r"^## .+$", markdown[match.end() :], re.M)
    end = match.end() + next_match.start() if next_match else len(markdown)
    return markdown[match.end() : end].strip()


def first_paragraph(section: str) -> str:
    for chunk in section.split("\n\n"):
        text = " ".join(line.strip() for line in chunk.splitlines() if line.strip() and not line.strip().startswith("|"))
        if text:
            return text
    return ""


def bullet_lines(section: str, limit: int = 5) -> list[str]:
    lines = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            lines.append(stripped[2:])
        if len(lines) >= limit:
            break
    return lines


def parse_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "BMS Mission Briefing"


def clean_brief_line(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -")


def section_bullets(markdown: str, headings: list[str], limit: int = 5) -> list[str]:
    for heading in headings:
        bullets = [clean_brief_line(item) for item in bullet_lines(read_section(markdown, heading), limit=limit)]
        bullets = [item for item in bullets if item]
        if bullets:
            return bullets
    return []


def load_hype_script(path: Path | None) -> dict:
    if path is None:
        return {}
    if not path.is_file():
        raise FileNotFoundError(f"Hype script not found: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


@lru_cache(maxsize=1)
def base_template() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), "#050a0d")
    px = img.load()
    for y in range(HEIGHT):
        glow = int(16 + 18 * (y / HEIGHT))
        for x in range(WIDTH):
            edge = int(20 * abs(x - WIDTH / 2) / (WIDTH / 2))
            px[x, y] = (4, max(8, glow - edge // 3), max(10, 18 - edge // 4))
    return img


def base_frame() -> Image.Image:
    return base_template().copy()


def draw_grid(draw: ImageDraw.ImageDraw, t: float, alpha: int = 34) -> None:
    spacing = 64
    offset = int((t * 18) % spacing)
    color = (72, 218, 238, alpha)
    for x in range(-spacing, WIDTH + spacing, spacing):
        draw.line([(x + offset, 0), (x + offset, HEIGHT)], fill=color, width=1)
    for y in range(-spacing, HEIGHT + spacing, spacing):
        draw.line([(0, y + offset), (WIDTH, y + offset)], fill=color, width=1)


def fit_cover(image: Image.Image, box: tuple[int, int, int, int], zoom: float, pan_x: float, pan_y: float) -> Image.Image:
    bw = box[2] - box[0]
    bh = box[3] - box[1]
    scale = max(bw / image.width, bh / image.height) * zoom
    sw = int(image.width * scale)
    sh = int(image.height * scale)
    resized = image.resize((sw, sh), Image.Resampling.LANCZOS)
    max_x = max(0, sw - bw)
    max_y = max(0, sh - bh)
    left = int(max_x * max(0.0, min(1.0, pan_x)))
    top = int(max_y * max(0.0, min(1.0, pan_y)))
    return resized.crop((left, top, left + bw, top + bh))


def draw_map_panel(
    frame: Image.Image,
    map_img: Image.Image,
    box: tuple[int, int, int, int],
    *,
    t: float,
    zoom_start: float = 1.02,
    zoom_end: float = 1.10,
    pan_start: tuple[float, float] = (0.0, 0.5),
    pan_end: tuple[float, float] = (1.0, 0.5),
) -> None:
    progress = smoothstep(t)
    zoom = zoom_start + (zoom_end - zoom_start) * progress
    pan_x = pan_start[0] + (pan_end[0] - pan_start[0]) * progress
    pan_y = pan_start[1] + (pan_end[1] - pan_start[1]) * progress
    crop = fit_cover(map_img, box, zoom, pan_x, pan_y)
    crop = ImageEnhance.Contrast(crop).enhance(1.06)
    crop = ImageEnhance.Color(crop).enhance(0.82)
    frame.paste(crop, box[:2])
    overlay = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, overlay.width - 1, overlay.height - 1), outline=(75, 218, 238, 150), width=2)
    od.rectangle((0, 0, overlay.width - 1, overlay.height - 1), fill=(0, 14, 20, 34))
    sweep_x = int((t % 1.0) * overlay.width)
    od.rectangle((sweep_x - 3, 0, sweep_x + 3, overlay.height), fill=(75, 218, 238, 82))
    for y in range(0, overlay.height, 4):
        od.line((0, y, overlay.width, y), fill=(0, 0, 0, 22))
    frame.alpha_composite(overlay, box[:2])


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def draw_header(draw: ImageDraw.ImageDraw, title: str, scene_label: str, t: float) -> None:
    cyan = (83, 245, 224, 230)
    white = (235, 245, 245, 242)
    draw.rectangle((56, 42, 1864, 104), outline=(72, 218, 238, 128), width=2)
    draw.text((78, 54), "UOAF TACTICAL BRIEFING", font=font(FONT_CONDENSED, 25), fill=cyan)
    draw.text((1580, 54), scene_label.upper(), font=font(FONT_MONO, 23), fill=white, anchor="ra")
    draw.text((1788, 54), f"T+{int(t*100):03d}", font=font(FONT_MONO, 22), fill=(144, 230, 232, 190), anchor="ra")
    draw.line((78, 112, 780, 112), fill=(83, 245, 224, 180), width=3)
    draw.text((78, 126), title, font=font(FONT_CONDENSED, 34), fill=white)


def draw_subtitle(draw: ImageDraw.ImageDraw, text: str) -> None:
    fnt = font(FONT_BOLD, 32)
    lines = wrap_text(draw, text, fnt, 1460)[:2]
    box_top = 895
    draw.rounded_rectangle((210, box_top, 1710, 1028), radius=8, fill=(2, 10, 14, 218), outline=(82, 232, 238, 120), width=2)
    y = box_top + 25
    for line in lines:
        draw.text((WIDTH // 2, y), line, font=fnt, fill=(238, 246, 244, 242), anchor="ma")
        y += 43


def draw_bullets(draw: ImageDraw.ImageDraw, x: int, y: int, heading: str, bullets: list[str], width: int) -> None:
    draw.text((x, y), heading.upper(), font=font(FONT_CONDENSED, 36), fill=(85, 246, 225, 235))
    draw.line((x, y + 48, x + width, y + 48), fill=(85, 246, 225, 130), width=2)
    body = font(FONT_REGULAR, 31)
    yy = y + 72
    for item in bullets:
        wrapped = wrap_text(draw, item, body, width - 48)[:2]
        draw.rectangle((x, yy + 9, x + 16, yy + 25), fill=(229, 48, 57, 235))
        for line in wrapped:
            draw.text((x + 36, yy), line, font=body, fill=(225, 235, 235, 235))
            yy += 39
        yy += 12


def draw_title_scene(frame: Image.Image, draw: ImageDraw.ImageDraw, title: str, t: float) -> None:
    draw_grid(draw, t, alpha=28)
    draw.text((WIDTH // 2, 342), "PRE-SORTIE BRIEFING", font=font(FONT_CONDENSED, 88), fill=(237, 247, 245, 245), anchor="ma")
    draw.text((WIDTH // 2, 442), title, font=font(FONT_CONDENSED, 54), fill=(82, 246, 225, 235), anchor="ma")
    draw.line((520, 520, 1400, 520), fill=(82, 246, 225, 190), width=4)
    draw.text((WIDTH // 2, 566), "ORION / GIMHAE STRIKE PACKAGE", font=font(FONT_MONO, 30), fill=(230, 236, 232, 210), anchor="ma")


def rotate_point(x: float, y: float, angle: float) -> tuple[float, float]:
    ca = math.cos(angle)
    sa = math.sin(angle)
    return x * ca - y * sa, x * sa + y * ca


def draw_poly_aircraft(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    scale: float,
    angle: float,
    *,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
) -> None:
    # Stylized F-16-ish top silhouette: long nose, cropped delta-ish wings,
    # single tail, and intake/fuselage mass. Vector only, no external art.
    body = [
        (96, 0),
        (34, -10),
        (5, -12),
        (-28, -52),
        (-42, -48),
        (-18, -9),
        (-74, -7),
        (-96, -24),
        (-104, -20),
        (-92, 0),
        (-104, 20),
        (-96, 24),
        (-74, 7),
        (-18, 9),
        (-42, 48),
        (-28, 52),
        (5, 12),
        (34, 10),
    ]
    pts = []
    for x, y in body:
        rx, ry = rotate_point(x * scale, y * scale, angle)
        pts.append((cx + rx, cy + ry))
    draw.polygon(pts, fill=fill, outline=outline)

    # Canopy and spine glints.
    for x1, y1, x2, y2 in [(38, 0, 8, 0), (-15, 0, -68, 0)]:
        a, b = rotate_point(x1 * scale, y1 * scale, angle)
        c, d = rotate_point(x2 * scale, y2 * scale, angle)
        draw.line((cx + a, cy + b, cx + c, cy + d), fill=(100, 250, 255, 185), width=max(1, int(3 * scale)))


def draw_flares(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float, angle: float, t: float) -> None:
    rear_x, rear_y = rotate_point(-92 * scale, 0, angle)
    base_x = cx + rear_x
    base_y = cy + rear_y
    for index in range(11):
        spread = (index - 5) / 5.0
        distance = (95 + index * 28 + t * 190) * scale
        flare_angle = angle + math.pi + spread * 0.62
        fx = base_x + math.cos(flare_angle) * distance
        fy = base_y + math.sin(flare_angle) * distance + math.sin(t * 16 + index) * 14
        size = max(3, int((14 - index * 0.65) * scale))
        alpha = max(0, int(230 - index * 15 - t * 40))
        draw.line((base_x, base_y, fx, fy), fill=(255, 164, 42, max(40, alpha // 3)), width=max(1, int(4 * scale)))
        draw.ellipse((fx - size, fy - size, fx + size, fy + size), fill=(255, 226, 105, alpha), outline=(255, 74, 36, alpha))


def draw_f16_flares_pass(frame: Image.Image, global_t: float) -> None:
    passes = [
        (10.6, 6.2, -260, 640, WIDTH + 260, 250, -0.26, 1.05),
        (28.0, 5.6, WIDTH + 260, 330, -260, 605, 2.90, 0.82),
    ]
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    for start, duration, x0, y0, x1, y1, angle, scale in passes:
        if not (start <= global_t <= start + duration):
            continue
        p = smoothstep((global_t - start) / duration)
        cx = x0 + (x1 - x0) * p
        cy = y0 + (y1 - y0) * p
        draw_flares(draw, cx, cy, scale, angle, p)
        # Drop shadow/glow first, then the silhouette.
        draw_poly_aircraft(draw, cx + 8, cy + 10, scale * 1.05, angle, fill=(0, 0, 0, 110), outline=(0, 0, 0, 0))
        draw_poly_aircraft(draw, cx, cy, scale, angle, fill=(2, 8, 11, 235), outline=(89, 250, 255, 210))
    frame.alpha_composite(overlay)


def draw_arcade_chaos(frame: Image.Image, scene_name: str, global_t: float, local_t: float) -> None:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    pulse = 0.5 + 0.5 * math.sin(global_t * 8.7)
    fast = 0.5 + 0.5 * math.sin(global_t * 31.0)

    if int(global_t * 6) % 9 in {0, 1}:
        alpha = int(22 + 42 * fast)
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(255, 28, 42, alpha))
        draw.rectangle((22, 22, WIDTH - 22, HEIGHT - 22), outline=(255, 54, 64, 160), width=6)
    if int(global_t * 11) % 17 == 0:
        y = int(120 + (global_t * 131) % 740)
        draw.rectangle((0, y, WIDTH, y + 20), fill=(88, 245, 255, 125))
        draw.rectangle((0, y + 26, WIDTH, y + 34), fill=(255, 52, 67, 90))

    if scene_name in {"target", "objective", "terrain"}:
        label = "WEZ PENETRATION" if scene_name != "terrain" else "TERRAIN MASKING"
        box_alpha = int(120 + 80 * pulse)
        draw.rounded_rectangle((1180, 118, 1810, 186), radius=6, fill=(28, 0, 4, box_alpha), outline=(255, 42, 58, 220), width=3)
        draw.text((1495, 132), label, font=font(FONT_CONDENSED, 42), fill=(255, 228, 120, 245), anchor="ma")
        draw.text((1495, 192), "MISSILE STATE: ABSURD", font=font(FONT_MONO, 24), fill=(255, 78, 84, 220), anchor="ma")

    if scene_name == "route":
        draw.text((WIDTH // 2, 830), "ALL AIRCRAFT: COMMIT", font=font(FONT_CONDENSED, 66), fill=(255, 235, 132, int(130 + 105 * pulse)), anchor="ma")
    if scene_name == "execute":
        draw.text((WIDTH // 2, 760), "RETURN AS LEGENDS", font=font(FONT_CONDENSED, 82), fill=(255, 238, 142, int(160 + 80 * pulse)), anchor="ma")

    # Radar brackets and target boxes that flicker like someone spilled caffeine on the AWACS console.
    for idx in range(7):
        phase = (global_t * (0.17 + idx * 0.013) + idx * 0.19) % 1.0
        x = int(160 + phase * 1600)
        y = int(180 + ((phase * 1.7 + idx * 0.23) % 1.0) * 610)
        size = int(36 + 20 * ((idx + int(global_t * 3)) % 3))
        color = (255, 52, 68, 90) if idx % 2 else (80, 240, 255, 90)
        draw.line((x - size, y - size, x - size // 3, y - size), fill=color, width=3)
        draw.line((x - size, y - size, x - size, y - size // 3), fill=color, width=3)
        draw.line((x + size, y + size, x + size // 3, y + size), fill=color, width=3)
        draw.line((x + size, y + size, x + size, y + size // 3), fill=color, width=3)

    frame.alpha_composite(overlay)
    draw_f16_flares_pass(frame, global_t)


def render_video(args: argparse.Namespace) -> None:
    out_dir = args.out.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    markdown = args.brief.read_text(encoding="utf-8-sig")
    hype_script = load_hype_script(args.script)
    title = hype_script.get("title") or parse_title(markdown).replace(" Player Briefing", "")
    summary = first_paragraph(read_section(markdown, "Mission Summary"))
    intent = hype_script.get("intent") or section_bullets(markdown, ["Commander Intent", "Intent"], limit=5)
    execution = hype_script.get("execution") or section_bullets(markdown, ["Execution Notes", "Execution", "Game Plan"], limit=5)
    threats = hype_script.get("threats") or section_bullets(markdown, ["Threats", "Enemy Situation", "Air Threats"], limit=4)
    comm = hype_script.get("comm") or section_bullets(markdown, ["Comm Ladder", "Communications", "Comms"], limit=4)
    if not intent:
        intent = [summary or "Execute the package plan and preserve the force."]
    if not execution:
        execution = ["Follow assigned roles, timing, and deconfliction from the player brief."]
    if not threats:
        threats = ["Factor threats are marked on the route, target, and objective maps."]
    if not comm:
        comm = ["Use the current package comm ladder from the player brief."]
    map_dir = args.image_dir
    images: dict[str, Image.Image | None] = {
        "title": None,
        "route": Image.open(map_dir / "01_route_threat_map.png").convert("RGB"),
        "target": Image.open(map_dir / "02_target_area_map.png").convert("RGB"),
        "objective": Image.open(map_dir / "03_objective_area_map.png").convert("RGB"),
    }
    images["weather"] = Image.open(map_dir / "04_weather_map.png").convert("RGB") if (map_dir / "04_weather_map.png").is_file() else images["route"]
    three_d_path = map_dir / "05_3d_objective_area_close_labels_v25.png"
    images["terrain"] = Image.open(three_d_path).convert("RGB") if three_d_path.is_file() else images["objective"]

    default_scenes = [
        {"name": "title", "duration": 5.0, "subtitle": summary or "Mission package ready. Commit the plan."},
        {"name": "route", "duration": 9.0, "subtitle": "Route and threat picture: understand the flow before the fight gets loud."},
        {"name": "target", "duration": 8.0, "subtitle": "Target area: threats, fighter origins, and named anchors define the problem."},
        {"name": "objective", "duration": 8.0, "subtitle": "Objective area: hit the assigned targets and keep the corridor open."},
        {"name": "terrain", "duration": 7.0, "subtitle": "Terrain matters. Use masking, timing, and discipline."},
        {"name": "weather", "duration": 6.0, "subtitle": "Weather, visibility, cloud base, and winds set the working conditions."},
        {"name": "comms", "duration": 7.0, "subtitle": "One picture. Clean nets. Speak with purpose."},
        {"name": "execute", "duration": 6.0, "subtitle": "Execute the plan, solve the target, and bring everyone home."},
    ]
    scenes = hype_script.get("scenes") or default_scenes

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(args.out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    elapsed = 0.0
    for scene in scenes:
        scene_name = str(scene.get("name", "execute"))
        duration = float(scene.get("duration", 6.0))
        scene_map = images.get(scene.get("image", scene_name))
        subtitle = str(scene.get("subtitle", "Execute the plan."))
        frames = int(duration * FPS)
        for i in range(frames):
            local_t = i / max(frames - 1, 1)
            global_t = elapsed + i / FPS
            frame = base_frame().convert("RGBA")
            draw = ImageDraw.Draw(frame, "RGBA")
            if scene_name == "title":
                draw_title_scene(frame, draw, title, global_t)
            elif scene_map is not None:
                draw_map_panel(frame, scene_map, (96, 152, 1824, 850), t=local_t, pan_start=(0.15, 0.45), pan_end=(0.85, 0.55))
            elif scene_name == "comms":
                draw_grid(draw, global_t, alpha=28)
                draw_bullets(draw, 250, 230, "Comm Ladder", comm, 1420)
            else:
                draw_grid(draw, global_t, alpha=28)
                draw_bullets(draw, 210, 175, "Commander Intent", intent, 720)
                draw_bullets(draw, 1020, 175, "Execution", execution, 700)
            if args.arcade_chaos:
                draw_arcade_chaos(frame, scene_name, global_t, local_t)
            if scene_name in {"route", "target", "objective", "terrain", "weather"}:
                draw_header(draw, title, scene_name, local_t)
                if scene_name == "target":
                    draw_bullets(draw, 1200, 190, "Threat Read", threats, 560)
            elif scene_name != "title":
                draw_header(draw, title, scene_name, local_t)
            draw_subtitle(draw, subtitle)
            vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vignette, "RGBA")
            vd.rectangle((0, 0, WIDTH, 70), fill=(0, 0, 0, 100))
            vd.rectangle((0, HEIGHT - 90, WIDTH, HEIGHT), fill=(0, 0, 0, 110))
            frame.alpha_composite(vignette)
            proc.stdin.write(frame.convert("RGB").tobytes())
        elapsed += duration
    proc.stdin.close()
    return_code = proc.wait()
    if return_code:
        raise RuntimeError(f"ffmpeg exited with {return_code}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--script", type=Path, help="Optional JSON script with title, scene subtitles, and bullets for mission-specific hype videos.")
    parser.add_argument("--arcade-chaos", action="store_true", help="Add flashing arcade-briefing overlays and a stylized F-16 flare pass.")
    return parser.parse_args()


def main() -> int:
    render_video(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
