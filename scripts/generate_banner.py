from __future__ import annotations

import math
import random
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
PHOTO = Path("C:/Users/Rithun/AppData/Local/Temp/codex-clipboard-baa0c8f6-8c47-472a-b81f-770a10eb6c7d.png")

W, H = 1061, 379
PORTRAIT_W, PORTRAIT_H = 378, 331
SEED = 2206

DARK = {
    "bg": "#0A101F",
    "panel": "#101827",
    "panel2": "#0d1524",
    "line": "#22314c",
    "chrome": "#22D3EE",
    "chrome2": "#0891B2",
    "portrait": "#A78BFA",
    "accent": "#10B981",
    "text": "#D7E7F3",
    "muted": "#83A4B7",
    "dim": "#536C80",
    "live": "#FF4D5E",
}

LIGHT = {
    "bg": "#F7FAFC",
    "panel": "#FFFFFF",
    "panel2": "#EEF6FA",
    "line": "#BDD5E4",
    "chrome": "#0891B2",
    "chrome2": "#22D3EE",
    "portrait": "#7C3AED",
    "accent": "#10B981",
    "text": "#13283A",
    "muted": "#44677A",
    "dim": "#7E97A6",
    "live": "#D81E3C",
}

ROWS = [
    ("Subject", "Rithun K P"),
    ("Role", "AI Engineer"),
    ("Origin", "Kerala, India"),
    ("Education", "BTech CS + AI / BS Data Science"),
    ("Status", "Building"),
    ("ToolChain", "resume"),
    ("Core.Lang", "Python, TypeScript, Java, C++"),
    ("Core.Frontend", "HTML, CSS, JavaScript, React, Bootstrap"),
    ("Core.Backend", "FastAPI, Node.js, Express"),
    ("Core.Database", "PostgreSQL, MongoDB, SQLite, ChromaDB"),
    ("Core.Infra", "Docker, Git, GitHub Actions, Vercel"),
    ("Grid.Mail", "rithunpriyesh@gmail.com"),
    ("Grid.Portfolio", "rithunkp.github.io"),
    ("Grid.LinkedIn", "linkedin.com/rithun-k-p"),
    ("Grid.GitHub", "github.com/rithunkp"),
    ("Grid.Facebook", "facebook.com/rithunkp"),
]


def crop_photo() -> Image.Image:
    im = Image.open(PHOTO).convert("RGB")
    # The current source is already cropped and low-resolution, so preserve the
    # full frame and pad into the 300x340 portrait grid without stretching.
    fitted = ImageOps.contain(im, (PORTRAIT_W, PORTRAIT_H), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (PORTRAIT_W, PORTRAIT_H), tuple(np.asarray(fitted).reshape(-1, 3).mean(axis=0).astype(int)))
    canvas.paste(fitted, ((PORTRAIT_W - fitted.width) // 2, (PORTRAIT_H - fitted.height) // 2))
    return canvas


def reference_png_bits() -> np.ndarray:
    im = Image.open(PHOTO).convert("RGB")
    arr = np.asarray(im)
    # The supplied PNG is already a purple dither portrait. Extract those lit
    # pixels directly instead of dithering a dithered source again.
    purple = (
        (arr[:, :, 2].astype(np.int16) > 92)
        & (arr[:, :, 0].astype(np.int16) > 70)
        & ((arr[:, :, 2].astype(np.int16) - arr[:, :, 1].astype(np.int16)) > 18)
    )
    h, w = purple.shape
    yy, xx = np.mgrid[:h, :w]
    # Remove copied panel chrome/text from the reference crop; our SVG draws
    # those structurally, and leaving them here causes doubled labels/borders.
    chrome = (xx < 4) | (yy < 4) | (xx > w - 5) | (yy > h - 5) | ((xx < 130) & (yy < 21))
    purple &= ~chrome
    mask_img = Image.fromarray((purple * 255).astype(np.uint8), "L")
    mask_img = ImageOps.contain(mask_img, (PORTRAIT_W, PORTRAIT_H), method=Image.Resampling.NEAREST)
    canvas = Image.new("L", (PORTRAIT_W, PORTRAIT_H), 0)
    canvas.paste(mask_img, ((PORTRAIT_W - mask_img.width) // 2, (PORTRAIT_H - mask_img.height) // 2))
    return (np.asarray(canvas) > 0).astype(np.uint8)


def floyd_steinberg(gray: np.ndarray) -> np.ndarray:
    arr = gray.astype(np.float32).copy()
    h, w = arr.shape
    out = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
        for x in xs:
            old = arr[y, x]
            new = 255.0 if old >= 128 else 0.0
            out[y, x] = 1 if new == 0 else 0
            err = old - new
            if y % 2 == 0:
                targets = [(x + 1, y, 7 / 16), (x - 1, y + 1, 3 / 16), (x, y + 1, 5 / 16), (x + 1, y + 1, 1 / 16)]
            else:
                targets = [(x - 1, y, 7 / 16), (x + 1, y + 1, 3 / 16), (x, y + 1, 5 / 16), (x - 1, y + 1, 1 / 16)]
            for tx, ty, mul in targets:
                if 0 <= tx < w and 0 <= ty < h:
                    arr[ty, tx] += err * mul
    return out


def largest_component(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    best: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            q = deque([(x, y)])
            seen[y, x] = True
            pts: list[tuple[int, int]] = []
            while q:
                cx, cy = q.popleft()
                pts.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            if len(pts) > len(best):
                best = pts
    out = np.zeros_like(mask, dtype=bool)
    for x, y in best:
        out[y, x] = True
    return out


def fill_holes(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    bg = ~mask
    seen = np.zeros_like(mask, dtype=bool)
    q = deque()
    for x in range(w):
        q.extend([(x, 0), (x, h - 1)])
    for y in range(h):
        q.extend([(0, y), (w - 1, y)])
    while q:
        x, y = q.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y, x] or not bg[y, x]:
            continue
        seen[y, x] = True
        q.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return mask | (~seen & bg)


def subject_mask(im: Image.Image) -> np.ndarray:
    arr = np.asarray(im).astype(np.int16)
    # Background is desaturated grey/green. Skin, hair and shirt move away from
    # the median background color enough to isolate the head-and-shoulders area.
    corners = np.concatenate(
        [
            arr[:55, :55].reshape(-1, 3),
            arr[:55, -55:].reshape(-1, 3),
            arr[-45:, :45].reshape(-1, 3),
            arr[-45:, -45:].reshape(-1, 3),
        ],
        axis=0,
    )
    bg = np.median(corners, axis=0)
    dist = np.linalg.norm(arr - bg, axis=2)
    mask = dist > 42
    img = Image.fromarray((mask * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    mask = np.asarray(img) > 0
    mask = fill_holes(largest_component(mask))
    edge = Image.fromarray((mask * 255).astype(np.uint8), "L").filter(ImageFilter.MinFilter(3))
    return np.asarray(edge) > 0


def make_portrait_bits() -> tuple[np.ndarray, np.ndarray]:
    if PHOTO.suffix.lower() == ".png":
        bits = reference_png_bits()
        return bits, bits.copy()
    base = crop_photo()
    processed = ImageOps.autocontrast(base, cutoff=1)
    processed = ImageEnhance.Contrast(processed).enhance(1.3)
    processed = processed.filter(ImageFilter.UnsharpMask(radius=3, percent=140))
    gray = ImageOps.grayscale(processed)
    gray_arr = np.asarray(gray).astype(np.float32)
    # Bias the diffusion input to land near the intended ~17k visible dots
    # instead of a conventional 50% binary halftone.
    dark_input = np.clip((255.0 - gray_arr) + 82.0, 0, 255)
    light_input = np.clip(gray_arr + 104.0, 0, 255)
    dark_bits = floyd_steinberg(dark_input)
    mask = subject_mask(base)
    dark_bits = dark_bits & mask.astype(np.uint8)
    light_bits = floyd_steinberg(light_input)
    return dark_bits, light_bits


def runs_for_points(points: list[tuple[int, int]], sx: float, sy: float, ox: float, oy: float) -> str:
    by_row: dict[int, list[int]] = {}
    for x, y in points:
        by_row.setdefault(y, []).append(x)
    parts = []
    for y in sorted(by_row):
        xs = sorted(set(by_row[y]))
        start = prev = xs[0]
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
            else:
                parts.append(f"M{ox + start * sx:.0f} {oy + y * sy:.0f}h{(prev - start + 1) * sx:.0f}")
                start = prev = x
        parts.append(f"M{ox + start * sx:.0f} {oy + y * sy:.0f}h{(prev - start + 1) * sx:.0f}")
    return "".join(parts)


def bit_points(bits: np.ndarray) -> list[tuple[int, int]]:
    ys, xs = np.where(bits > 0)
    return list(zip(xs.tolist(), ys.tolist()))


def logo_masks(size: int = 170) -> list[np.ndarray]:
    masks = []
    for name in ("flutter", "code", "vercel"):
        im = Image.new("L", (size, size), 0)
        d = ImageDraw.Draw(im)
        if name == "flutter":
            d.polygon([(108, 10), (32, 86), (58, 112), (160, 10)], fill=255)
            d.polygon([(58, 116), (86, 144), (160, 70), (132, 42)], fill=255)
            d.polygon([(86, 146), (118, 160), (160, 118), (132, 90)], fill=255)
        elif name == "code":
            d.line([(68, 45), (34, 84), (68, 123)], fill=255, width=17, joint="curve")
            d.line([(102, 45), (136, 84), (102, 123)], fill=255, width=17, joint="curve")
            d.line([(94, 35), (76, 135)], fill=255, width=14)
        else:
            d.polygon([(85, 25), (155, 145), (15, 145)], fill=255)
        masks.append(np.asarray(im.filter(ImageFilter.GaussianBlur(0.2))) > 0)
    return masks


def sample_mask(mask: np.ndarray, n: int, rng: random.Random) -> np.ndarray:
    ys, xs = np.where(mask)
    idx = np.linspace(0, len(xs) - 1, min(len(xs), n), dtype=int)
    pts = np.column_stack([xs[idx], ys[idx]]).astype(float)
    rng.shuffle(pts)
    if len(pts) < n:
        extra = pts[rng.choices(range(len(pts)), k=n - len(pts))]
        pts = np.vstack([pts, extra])
    return pts[:n]


def match_points(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    # Greedy matching in angular/radial order keeps paths short without needing
    # heavy optimal-transport dependencies in this small repo.
    def key(pts: np.ndarray) -> np.ndarray:
        c = pts.mean(axis=0)
        angle = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
        radius = np.linalg.norm(pts - c, axis=1)
        return np.lexsort((radius, angle))

    return dst[key(dst)][np.argsort(key(src))]


def traveller_points(rng: random.Random) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    masks = logo_masks()
    pts = [sample_mask(m, 900, rng) for m in masks]
    pts[1] = match_points(pts[0], pts[1])
    pts[2] = match_points(pts[1], pts[2])
    scale = 0.45
    origin = np.array([417.0, 57.0])
    return tuple(origin + p * scale for p in pts)  # type: ignore[return-value]


def intro_groups(points: list[tuple[int, int]], groups: int, rng: random.Random) -> list[list[tuple[int, int]]]:
    shuffled = points[:]
    rng.shuffle(shuffled)
    return [shuffled[i::groups] for i in range(groups)]


def drift_groups(points: list[tuple[int, int]], groups: int, rng: random.Random) -> list[list[tuple[int, int]]]:
    noisy = []
    for x, y in points:
        v = 0.53 * x + 0.47 * y + rng.gauss(0, 4.0)
        noisy.append((v, x, y))
    noisy.sort()
    return [[(x, y) for _, x, y in noisy[i::groups]] for i in range(groups)]


def evenness_metric(groups: list[list[tuple[int, int]]]) -> float:
    all_pts = [p for group in groups for p in group]
    total = np.zeros(16)
    for x, y in all_pts:
        total[min(3, x * 4 // PORTRAIT_W) + 4 * min(3, y * 4 // PORTRAIT_H)] += 1
    total = total / max(total.sum(), 1)
    metrics = []
    for pts in groups:
        if not pts:
            continue
        xs = np.array([p[0] for p in pts])
        ys = np.array([p[1] for p in pts])
        q = np.zeros(16)
        for x, y in zip(xs, ys):
            q[min(3, x * 4 // PORTRAIT_W) + 4 * min(3, y * 4 // PORTRAIT_H)] += 1
        q = q / max(q.sum(), 1)
        metrics.append(float(np.sqrt(np.mean((q - total) ** 2))))
    return float(np.mean(metrics))


def boundary_metric(groups: list[list[tuple[int, int]]]) -> float:
    vals = []
    for pts in groups:
        if len(pts) < 5:
            continue
        xs = np.array([p[0] for p in pts])
        ys = np.array([p[1] for p in pts])
        vals.append(abs(float(np.corrcoef(xs, ys)[0, 1])))
    return float(np.nanmean(vals) / 10)


def text_row(label: str, value: str, y: int, c: dict[str, str], label_x: int = 570, leader_x: int = 648) -> str:
    label_len = max(72, len(label) * 7)
    value_len = max(130, min(255, len(value) * 6))
    leader_count = max(7, 42 - len(label) - len(value))
    leaders = "." * leader_count
    return (
        f'<text x="{label_x}" y="{y}" class="row-label" textLength="{label_len}" lengthAdjust="spacingAndGlyphs">{label}</text>'
        f'<text x="{leader_x}" y="{y}" class="leaders" textLength="128" lengthAdjust="spacingAndGlyphs">{leaders}</text>'
        f'<text x="1020" y="{y}" class="row-value" text-anchor="end" textLength="{value_len}" lengthAdjust="spacingAndGlyphs">{value}</text>'
    )


def portrait_layers(bits: np.ndarray, c: dict[str, str], rng: random.Random) -> tuple[str, dict[str, float]]:
    sx = 1.0
    sy = 1.0
    ox, oy = 13.0, 44.0
    points = bit_points(bits)
    intro = intro_groups(points, 60, rng)
    bands = drift_groups(points, 94, rng)
    metrics = {"intro_evenness": evenness_metric(intro), "boundary": boundary_metric(bands), "ink": len(points) / (PORTRAIT_W * PORTRAIT_H)}
    sw = 1.35
    parts = [f'<g id="portrait-intro" opacity="1" stroke="{c["portrait"]}" stroke-width="{sw}" shape-rendering="crispEdges">']
    for i, group in enumerate(intro):
        begin = 0.08 + i * (2.0 / len(intro))
        d = runs_for_points(group, sx, sy, ox, oy)
        parts.append(
            f'<path d="{d}" opacity="0"><animate attributeName="opacity" values="0;1" begin="{begin:.2f}s" dur="0.48s" fill="freeze"/></path>'
        )
    parts.append('<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.90;0.96;1" dur="3.2s" fill="freeze"/></g>')
    parts.append(f'<g id="portrait-loop" stroke="{c["portrait"]}" stroke-width="{sw}" shape-rendering="crispEdges">')
    logo_cx, logo_cy = 470.0, 190.0
    for i, group in enumerate(bands):
        if not group:
            continue
        cx = sum(p[0] for p in group) / len(group)
        cy = sum(p[1] for p in group) / len(group)
        dx = (logo_cx - (ox + cx * sx)) * 0.42
        dy = (logo_cy - (oy + cy * sy)) * 0.42
        d = runs_for_points(group, sx, sy, ox, oy)
        parts.append(
            f'<path d="{d}" opacity="1">'
            f'<animateTransform attributeName="transform" type="translate" dur="14.2s" repeatCount="indefinite" '
            f'keyTimes="0;0.211;0.303;0.444;0.535;0.676;0.768;0.908;1" '
            f'values="0 0;0 0;{dx:.2f} {dy:.2f};{dx:.2f} {dy:.2f};{dx:.2f} {dy:.2f};{dx:.2f} {dy:.2f};{dx:.2f} {dy:.2f};0 0;0 0"/>'
            f'<animate attributeName="opacity" dur="14.2s" repeatCount="indefinite" '
            f'keyTimes="0;0.211;0.303;0.768;0.908;1" values="1;1;0.10;0.10;1;1"/>'
            f'</path>'
        )
    parts.append("</g>")
    return "".join(parts), metrics


def traveller_layer(c: dict[str, str], rng: random.Random) -> str:
    p1, p2, p3 = traveller_points(rng)
    parts = [f'<g id="travellers" fill="{c["accent"]}" shape-rendering="crispEdges">']
    for i in range(900):
        x1, y1 = p1[i]
        x2, y2 = p2[i]
        x3, y3 = p3[i]
        dx2, dy2 = x2 - x1, y2 - y1
        dx3, dy3 = x3 - x1, y3 - y1
        parts.append(
            f'<rect width="2.8" height="2.8" x="{x1:.1f}" y="{y1:.1f}" opacity="0">'
            f'<animateTransform attributeName="transform" type="translate" dur="14.2s" repeatCount="indefinite" '
            f'keyTimes="0;0.211;0.303;0.444;0.535;0.676;0.768;0.908;1" '
            f'values="0 0;0 0;0 0;0 0;{dx2:.1f} {dy2:.1f};{dx2:.1f} {dy2:.1f};{dx3:.1f} {dy3:.1f};{dx3:.1f} {dy3:.1f};0 0"/>'
            f'<animate attributeName="opacity" dur="14.2s" repeatCount="indefinite" '
            f'keyTimes="0;0.211;0.303;0.444;0.535;0.676;0.768;0.908;1" '
            f'values="0;0;1;1;1;1;1;1;0"/>'
            f'</rect>'
        )
    parts.append("</g>")
    return "".join(parts)


def svg(mode: str, bits: np.ndarray) -> tuple[str, dict[str, float]]:
    c = DARK if mode == "dark" else LIGHT
    rng = random.Random(SEED + (1 if mode == "dark" else 2))
    portrait, metrics = portrait_layers(bits, c, rng)
    travellers = traveller_layer(c, rng)
    rows_top = "\n".join(text_row(label, value, 80 + i * 17, c) for i, (label, value) in enumerate(ROWS[:6]))
    rows_core = "\n".join(text_row(label, value, 197 + i * 17, c) for i, (label, value) in enumerate(ROWS[6:11]))
    rows_grid = "\n".join(text_row(label, value, 293 + i * 17, c, 590, 668) for i, (label, value) in enumerate(ROWS[11:]))
    social_icons = "\n".join(
        [
            f'<text x="570" y="293" class="icon">✉</text>',
            f'<text x="570" y="310" class="icon">◉</text>',
            f'<text x="570" y="327" class="icon">in</text>',
            f'<text x="570" y="344" class="icon">⌘</text>',
            f'<text x="570" y="361" class="icon">f</text>',
        ]
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Rithun K P animated GitHub profile banner">\n'
        f"<style><![CDATA["
        f"text{{font-family:'SFMono-Regular','Cascadia Mono','Consolas',monospace}}"
        f".title{{fill:{c['text']};font-size:14px;font-weight:700}}"
        f".header{{fill:{c['chrome']};font-size:12px;font-weight:700}}"
        f".row-label{{fill:{c['chrome']};font-size:12px}}"
        f".leaders{{fill:{c['dim']};font-size:12px}}"
        f".row-value{{fill:{c['text']};font-size:12px;font-weight:500}}"
        f".icon{{fill:{c['chrome']};font-size:12px;font-weight:700}}"
        f"]]></style>\n"
        f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>\n'
        f'<rect x="0" y="0" width="{W}" height="27" fill="{c["panel2"]}" stroke="{c["chrome2"]}" stroke-width="1"/>\n'
        f'<circle cx="15" cy="13" r="5.5" fill="#ff5f57"/><circle cx="35" cy="13" r="5.5" fill="#ffbd2e"/><circle cx="55" cy="13" r="5.5" fill="#28c840"/>\n'
        f'<text x="530" y="18" text-anchor="middle" class="title">profile.sh --live</text><rect x="1034" y="13" width="12" height="3" fill="{c["portrait"]}"/>\n'
        f'<path d="M13 56V43H24M109 43H391V372H13V357" fill="none" stroke="{c["portrait"]}" stroke-width="1.4"/>\n'
        f'<text x="34" y="50" class="header" fill="{c["portrait"]}">VISUAL.MAP</text>\n'
        f"{portrait}\n{travellers}\n"
        f'<path d="M548 55V44H559M644 44H1049V378H548V365" fill="none" stroke="{c["chrome"]}" stroke-width="1.4"/>\n'
        f'<text x="570" y="51" class="header">SYSTEM.INFO</text>\n'
        f'<g><circle cx="842" cy="49" r="5.3" fill="{c["live"]}"><animate attributeName="opacity" values="0.55;1;0.55" dur="1.25s" repeatCount="indefinite"/></circle><text x="854" y="53" fill="{c["live"]}" font-size="12" font-weight="700">LIVE</text></g>\n'
        f'<rect x="903" y="39" width="91" height="21" rx="6" fill="{c["chrome2"]}" opacity="0.18" stroke="{c["chrome"]}"/><text x="948" y="54" text-anchor="middle" fill="{c["text"]}" font-size="13" font-weight="700">@rithunkp</text>\n'
        f"{rows_top}\n"
        f'<path d="M570 179H1019" stroke="{c["line"]}"/>\n'
        f"{rows_core}\n"
        f'<path d="M570 275H1019" stroke="{c["line"]}"/>\n'
        f"{social_icons}\n{rows_grid}\n"
        f"</svg>\n",
        metrics,
    )


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    dark_bits, light_bits = make_portrait_bits()
    np.save(DATA / "portrait_dark_bits.npy", dark_bits)
    np.save(DATA / "portrait_light_bits.npy", light_bits)
    all_metrics = {}
    for mode, bits in (("dark", dark_bits), ("light", light_bits)):
        content, metrics = svg(mode, bits)
        (ASSETS / f"{mode}.svg").write_text(content, encoding="utf-8")
        all_metrics[mode] = metrics
    lines = ["mode,intro_evenness,boundary_metric,ink_coverage,file_bytes"]
    for mode in ("dark", "light"):
        size = (ASSETS / f"{mode}.svg").stat().st_size
        m = all_metrics[mode]
        lines.append(f"{mode},{m['intro_evenness']:.4f},{m['boundary']:.4f},{m['ink']:.4f},{size}")
    (DATA / "banner_metrics.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
