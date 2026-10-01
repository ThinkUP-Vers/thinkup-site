#!/usr/bin/env python3
"""Rend les scripts de scripts-video-2026-09.md en vidéos motion design.

Lit les tableaux du markdown (minutage, plan, texte à l'écran, voix off),
dessine chaque image avec Pillow et encode avec ffmpeg (H.264, 30 i/s).

Usage : python3 render_motion.py SORTIE [--only 1-tiktok] [--jobs 4]
Polices : variable d'environnement FONT_DIR (paquets @fontsource
source-sans-3 et eb-garamond extraits dans FONT_DIR/ss et FONT_DIR/gar).
"""
import math
import os
import random
import re
import subprocess
import sys
from multiprocessing import Pool

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_MD = os.path.join(HERE, "scripts-video-2026-09.md")
FONT_DIR = os.environ.get("FONT_DIR", "/tmp/claude-0/fonts")
FPS = 30

# Palette du site (style-v2.css)
PAPER = (250, 247, 243)
PAPER2 = (241, 234, 225)
INK = (42, 36, 31)
INK_SOFT = (108, 96, 87)
ACCENT = (56, 102, 95)
ACCENT_ON_DEEP = (143, 194, 183)
EMBER = (193, 120, 63)
DEEP = (38, 43, 41)
ON_DEEP = (244, 238, 230)
ON_DEEP_SOFT = (195, 184, 171)

FORMATS = {
    "tiktok": (1080, 1920),
    "linkedin": (1080, 1350),
    "facebook": (1080, 1350),
}

# ---------------------------------------------------------------- polices

def _font_path(kind, weight, italic=False):
    if kind == "sans":
        return f"{FONT_DIR}/ss/files/source-sans-3-latin-{weight}-normal.woff"
    style = "italic" if italic else "normal"
    return f"{FONT_DIR}/gar/files/eb-garamond-latin-{weight}-{style}.woff"


FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_cmap_cache = {}
_font_cache = {}


def cmap(path):
    if path not in _cmap_cache:
        _cmap_cache[path] = set(TTFont(path).getBestCmap().keys())
    return _cmap_cache[path]


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def runs(text, path):
    """Découpe en segments (texte, police) : repli DejaVu pour → ≠ etc."""
    have = cmap(path)
    out = []
    for ch in text:
        p = path if ord(ch) in have else FALLBACK
        if out and out[-1][1] == p:
            out[-1][0] += ch
        else:
            out.append([ch, p])
    return out


def text_width(text, path, size):
    return sum(font(p, size).getlength(t) for t, p in runs(text, path))


def render_word(text, path, size, color):
    """Rend un mot sur fond transparent ; renvoie (image, décalage_baseline)."""
    asc, desc = font(path, size).getmetrics()
    w = math.ceil(text_width(text, path, size)) + 4
    h = asc + desc + 4
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 2
    for t, p in runs(text, path):
        f = font(p, size)
        # aligne les bases des deux polices
        d.text((x, 2 + asc), t, font=f, fill=color + (255,), anchor="ls")
        x += f.getlength(t)
    return im


# ---------------------------------------------------------------- parsing

def parse_time(s):
    s = s.replace(",", ".").replace("s", "").strip()
    a, b = re.split(r"[–-]", s)
    return float(a), float(b)


def parse_md():
    subjects = []
    cur = None
    plat = None
    for line in open(SCRIPT_MD, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"^## (\d)\. (.+)$", line)
        if m:
            cur = {"num": int(m.group(1)), "title": m.group(2), "videos": {}}
            subjects.append(cur)
            plat = None
            continue
        m = re.match(r"^### (TikTok|LinkedIn|Facebook) — ", line)
        if m and cur:
            plat = m.group(1).lower()
            cur["videos"][plat] = []
            continue
        if line.startswith("### ") or line.startswith("## "):
            plat = None
            continue
        if plat and line.startswith("| ") and re.match(r"^\| \d", line):
            cells = [c.strip() for c in line.strip("|").split(" | ")]
            if len(cells) != 4:
                continue
            t0, t1 = parse_time(cells[0])
            cur["videos"][plat].append(
                {"t0": t0, "t1": t1, "plan": cells[1], "screen": cells[2], "vo": cells[3].strip("« »")}
            )
    return subjects


# ---------------------------------------------------------------- mise en forme

def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = min(max(t, 0.0), 1.0)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def classify(scene, idx, n):
    s = scene["screen"]
    if re.search(r"\b1\. .+ 2\. ", s):
        items = [x.strip() for x in re.split(r"\s*\d\.\s+", s) if x.strip()]
        return "list", items
    if " · " in s:
        return "list", [x.strip() for x in s.split(" · ")]
    if s.count("→") >= 2 or (s.count("→") == 1 and len(s) > 40):
        return "chain", [x.strip() for x in s.split("→")]
    if idx == n - 1:
        return "question", [s]
    if idx == 0:
        return "hook", [s]
    if s.startswith("«") and s.rstrip(".").endswith("»"):
        return "quote", [s]
    return "statement", [s]


def nbsp(text):
    """Insécables à la française : pas de « ? » ni de « » » orphelin."""
    text = re.sub(r" ([?!:;»])", "\u00a0\\1", text)
    text = text.replace("« ", "«\u00a0")
    text = re.sub(r"(\d) (m|s|h|min|%)\b", "\\1\u00a0\\2", text)
    return text


def words_of(text):
    return [w for w in nbsp(text).split(" ") if w]


def wrap(words, path, size, maxw):
    lines, line = [], []
    space = text_width(" ", path, size)
    w = 0
    for word in words:
        ww = text_width(word, path, size)
        if line and w + space + ww > maxw:
            lines.append(line)
            line, w = [word], ww
        else:
            w = w + (space if line else 0) + ww
            line.append(word)
    if line:
        lines.append(line)
    return lines


def fit(text, path, maxw, maxh, start, minsize=40, lh=1.12):
    words = words_of(text)
    size = start
    while size > minsize:
        lines = wrap(words, path, size, maxw)
        if len(lines) * size * lh <= maxh and all(
            text_width(" ".join(l), path, size) <= maxw for l in lines
        ):
            return size, lines
        size -= 4
    return size, wrap(words, path, size, maxw)


def is_emph(word):
    core = re.sub(r"[^\wÀ-ÿ]", "", word)
    return len(core) >= 5 and core.isupper()


class Layout:
    """Mots positionnés pour une scène, avec leur temps d'apparition."""

    def __init__(self):
        self.items = []  # (image, x, y, apparition_s, style)

    def add(self, im, x, y, t, style="rise"):
        self.items.append((im, x, y, t, style))


def build_scene(scene, idx, n, W, H, plat, dark):
    kind, parts = classify(scene, idx, n)
    fg = ON_DEEP if dark else INK
    soft = ON_DEEP_SOFT if dark else INK_SOFT
    acc = ACCENT_ON_DEEP if dark else ACCENT
    margin = 96 if plat == "tiktok" else 90
    maxw = W - 2 * margin - (40 if plat == "tiktok" else 0)
    # zone de contenu (TikTok : éviter l'interface en haut et en bas)
    if plat == "tiktok":
        top, bottom = 300, H - 520
    else:
        top, bottom = 170, H - 300
    lay = Layout()
    dur = scene["t1"] - scene["t0"]
    stagger = min(0.09, max(0.04, (dur * 0.35) / max(1, len(words_of(scene["screen"])))))

    sans_b = _font_path("sans", 900 if kind == "hook" else 700)
    serif_i = _font_path("serif", 500, italic=True)

    if kind in ("list", "chain"):
        path = _font_path("sans", 700)
        size = 92 if plat == "tiktok" else 80
        rows = []
        for it in parts:
            s, lines = fit(it, path, maxw - 110, 3 * size, size, lh=1.1)
            rows.append((s, lines))
        size = min(r[0] for r in rows)
        rows = [(size, wrap(words_of(it), path, size, maxw - 110)) for it in parts]
        gap = size * 0.55
        total = sum(len(l) * size * 1.1 for _, l in rows) + gap * (len(rows) - 1)
        y = top + (bottom - top - total) / 2
        per = max(0.35, min(0.8, dur * 0.6 / len(parts)))
        for i, (s, lines) in enumerate(rows):
            t = 0.15 + i * per
            # puce : numéro ou flèche
            mark = f"{i + 1}" if kind == "list" else ("" if i == 0 else "→")
            if mark:
                mim = render_word(mark, _font_path("sans", 900), int(size * 0.9), EMBER)
                lay.add(mim, margin, y + (size * 0.05), t, "pop")
            for j, line in enumerate(lines):
                x = margin + 110
                for k, word in enumerate(line):
                    col = EMBER if is_emph(word) else fg
                    im = render_word(word, path, s, col)
                    lay.add(im, x, y + j * s * 1.1, t + 0.05 + k * 0.03, "slide")
                    x += text_width(word + " ", path, s)
            y += len(lines) * s * 1.1 + gap
        cap_y = y - gap + 60
    else:
        text = parts[0]
        if kind == "quote":
            path = serif_i
            start = 120 if plat == "tiktok" else 104
        else:
            path = sans_b
            start = (150 if kind == "hook" else 124) if plat == "tiktok" else (124 if kind == "hook" else 104)
        size, lines = fit(text, path, maxw, (bottom - top) * 0.8, start, lh=1.1)
        lh = size * 1.1
        total = len(lines) * lh
        y0 = top + (bottom - top - total) / 2
        k = 0
        for j, line in enumerate(lines):
            x = margin
            for word in line:
                col = EMBER if is_emph(word) else (acc if kind == "question" and word.endswith("?") else fg)
                im = render_word(word, path, size, col)
                lay.add(im, x, y0 + j * lh, 0.12 + k * stagger, "punch" if kind == "hook" else "rise")
                x += text_width(word + " ", path, size)
                k += 1
        cap_y = y0 + total + 70
        # filet de soulignement animé sous le titre
        lay.rule = (margin, y0 + total + 18, min(maxw, 260), 0.12 + k * stagger)
    if not hasattr(lay, "rule"):
        lay.rule = None

    # sous-titre (voix off) : révélation mot à mot
    cpath = _font_path("sans", 600)
    csize = 50 if plat == "tiktok" else 42
    norm = lambda x: re.sub(r"[^\wÀ-ÿ]", "", x.lower())
    cwords = [] if norm(scene["vo"]) == norm(scene["screen"]) else words_of(scene["vo"])
    clines = wrap(cwords, cpath, csize, maxw)
    if len(clines) > 4:
        csize -= 6
        clines = wrap(cwords, cpath, csize, maxw)
    cap_y = min(cap_y, H - (420 if plat == "tiktok" else 120) - len(clines) * csize * 1.3)
    cap = []
    ci = 0
    reveal_end = max(0.6, dur * 0.85)
    nwords = max(1, len(cwords))
    for j, line in enumerate(clines):
        x = margin
        for word in line:
            on = render_word(word, cpath, csize, fg)
            off = render_word(word, cpath, csize, soft)
            t = 0.25 + (reveal_end - 0.25) * ci / nwords
            cap.append((on, off, x, cap_y + j * csize * 1.3, t))
            x += text_width(word + " ", cpath, csize)
            ci += 1
    lay.caption = cap
    lay.kind = kind
    return lay


# ---------------------------------------------------------------- fonds

def make_background(W, H, plan, dark, seed):
    """Fond pré-rendu, 25 % plus grand pour la dérive (Ken Burns)."""
    rnd = random.Random(f"{plan}-{seed}")
    BW, BH = int(W * 1.25), int(H * 1.25)
    base = DEEP if dark else PAPER
    other = (52, 60, 57) if dark else PAPER2
    bg = Image.new("RGB", (BW, BH), base)
    # dégradé radial doux
    g = Image.radial_gradient("L").resize((BW, BH))
    bg = Image.composite(bg, Image.new("RGB", (BW, BH), other), g)
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    col = (ACCENT_ON_DEEP if dark else ACCENT)
    motif = rnd.choice(["circles", "lines", "dots", "arcs"])
    if motif == "circles":
        cx, cy = rnd.uniform(0.6, 0.9) * BW, rnd.uniform(0.1, 0.4) * BH
        for r in range(120, int(BW * 1.1), 70):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (26,), width=3)
    elif motif == "lines":
        for i in range(-BH, BW, 90):
            d.line([(i, 0), (i + BH * 0.6, BH)], fill=col + (20,), width=3)
    elif motif == "dots":
        for yy in range(40, BH, 64):
            for xx in range(40, BW, 64):
                if rnd.random() < 0.7:
                    d.ellipse([xx - 4, yy - 4, xx + 4, yy + 4], fill=col + (34,))
    else:
        for _ in range(6):
            cx, cy = rnd.uniform(0, BW), rnd.uniform(0, BH)
            r = rnd.uniform(BW * 0.3, BW * 0.7)
            a0 = rnd.uniform(0, 360)
            d.arc([cx - r, cy - r, cx + r, cy + r], a0, a0 + rnd.uniform(60, 160), fill=col + (40,), width=4)
    # tache de couleur floutée
    blob = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    bx, by = rnd.uniform(0.1, 0.9) * BW, rnd.uniform(0.5, 0.95) * BH
    br = BW * 0.35
    bd.ellipse([bx - br, by - br, bx + br, by + br], fill=(EMBER if rnd.random() < 0.5 else col) + (38 if dark else 30,))
    blob = blob.filter(ImageFilter.GaussianBlur(160))
    out = bg.convert("RGBA")
    out.alpha_composite(blob)
    out.alpha_composite(layer)
    return out.convert("RGB"), rnd.uniform(0, math.tau)


def bg_frame(bgimg, W, H, t, dur, phase):
    """Dérive lente + léger zoom, en sous-pixel."""
    BW, BH = bgimg.size
    p = t / max(dur, 0.1)
    scale = 1.0 + 0.06 * p
    cx = BW / 2 + math.cos(phase) * 40 * p
    cy = BH / 2 + math.sin(phase) * 40 * p
    w, h = W * (BW / W / 1.25) / scale, H * (BH / H / 1.25) / scale
    x0, y0 = cx - w / 2, cy - h / 2
    return bgimg.transform((W, H), Image.AFFINE, (w / W, 0, x0, 0, h / H, y0), resample=Image.BILINEAR)


# ---------------------------------------------------------------- rendu

def with_alpha(im, a):
    if a >= 0.999:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return out


def draw_scene(frame, lay, t):
    for im, x, y, t0, style in lay.items:
        p = (t - t0) / 0.38
        if p <= 0:
            continue
        e = ease_out(p)
        a = min(1.0, p * 1.6)
        if style == "punch":
            s = 1.0 + 0.25 * (1 - e)
            if s > 1.001:
                w, h = im.size
                im2 = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.BILINEAR)
                frame.alpha_composite(with_alpha(im2, a), (int(x - (im2.width - w) / 2), int(y - (im2.height - h) / 2)))
                continue
            frame.alpha_composite(with_alpha(im, a), (int(x), int(y)))
        elif style == "slide":
            frame.alpha_composite(with_alpha(im, a), (int(x + 60 * (1 - e)), int(y)))
        elif style == "pop":
            s = 0.4 + 0.6 * ease_out(p * 1.3) + 0.08 * math.sin(min(p, 1) * math.pi)
            w, h = im.size
            im2 = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.BILINEAR)
            frame.alpha_composite(with_alpha(im2, a), (int(x + (w - im2.width) / 2), int(y + (h - im2.height) / 2)))
        else:
            frame.alpha_composite(with_alpha(im, a), (int(x), int(y + 50 * (1 - e))))
    if lay.rule:
        x, y, w, t0 = lay.rule
        p = ease_out((t - t0) / 0.5)
        if p > 0:
            ImageDraw.Draw(frame).rectangle([x, y, x + w * p, y + 8], fill=EMBER + (255,))
    for on, off, x, y, t0 in lay.caption:
        if t < 0.2:
            continue
        frame.alpha_composite(on if t >= t0 else with_alpha(off, 0.55), (int(x), int(y)))


def chrome(frame, W, H, plat, t, total, dark):
    d = ImageDraw.Draw(frame)
    # barre de progression
    by = 0 if plat != "tiktok" else 0
    d.rectangle([0, by, W * min(1, t / total), by + 10], fill=EMBER + (255,))
    # signature
    path = _font_path("sans", 700)
    col = ON_DEEP if dark else INK
    y = 70 if plat != "tiktok" else 190
    mark = render_word("Think’UP", path, 40, col)
    frame.alpha_composite(mark, (90, y))
    d.ellipse([90 + mark.width + 4, y + 36, 90 + mark.width + 16, y + 48], fill=EMBER + (255,))


def end_card(W, H, t):
    frame = Image.new("RGBA", (W, H), DEEP + (255,))
    d = ImageDraw.Draw(frame)
    p = ease_out(t / 0.6)
    name = render_word("Think’UP", _font_path("sans", 900), 150, ON_DEEP)
    x = (W - name.width) / 2
    y = H / 2 - 170 + 40 * (1 - p)
    frame.alpha_composite(with_alpha(name, min(1, p * 1.5)), (int(x), int(y)))
    d.rectangle([W / 2 - 130 * p, y + 200, W / 2 + 130 * p, y + 208], fill=EMBER + (255,))
    for i, (txt, sz, f) in enumerate([
        ("Patrick Langlais", 54, _font_path("serif", 500, True)),
        ("think-up.fr", 46, _font_path("sans", 600)),
    ]):
        q = ease_out((t - 0.3 - i * 0.15) / 0.5)
        if q > 0:
            im = render_word(txt, f, sz, ON_DEEP if i == 0 else ACCENT_ON_DEEP)
            frame.alpha_composite(with_alpha(im, q), (int((W - im.width) / 2), int(y + 250 + i * 80)))
    return frame


TRANS = 0.22  # durée d'un demi-volet (s)


def render_video(job):
    subj, plat, scenes, out_dir = job
    W, H = FORMATS[plat]
    end = plat != "tiktok"
    end_dur = 2.5 if end else 0
    total = scenes[-1]["t1"] + end_dur
    n = len(scenes)
    name = f"{subj['num']}-{slug(subj['title'])}-{plat}.mp4"
    out = os.path.join(out_dir, name)
    preps = []
    for i, sc in enumerate(scenes):
        dark = i == 0 or i == n - 1 or i % 2 == 0
        bgimg, phase = make_background(W, H, f"{subj['num']}-{sc['plan']}", dark, plat)
        lay = build_scene(sc, i, n, W, H, plat, dark)
        preps.append((sc, dark, bgimg, phase, lay))

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-vf", "noise=alls=4:allf=t+u,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
        "-r", str(FPS), "-g", str(FPS * 2),
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nframes = int(round(total * FPS))
    for f in range(nframes):
        t = f / FPS
        if t >= scenes[-1]["t1"]:
            frame = end_card(W, H, t - scenes[-1]["t1"])
        else:
            i = next(k for k, p in enumerate(preps) if p[0]["t1"] > t or k == n - 1)
            sc, dark, bgimg, phase, lay = preps[i]
            lt = t - sc["t0"]
            dur = sc["t1"] - sc["t0"]
            frame = bg_frame(bgimg, W, H, lt, dur, phase).convert("RGBA")
            draw_scene(frame, lay, lt)
            chrome(frame, W, H, plat, t, total, dark)
            # volet de transition : entre en fin de scène, sort au début de la suivante
            rem = dur - lt
            has_next = i < n - 1 or end
            if has_next and rem < TRANS:
                p = ease_in_out(1 - rem / TRANS)
                ImageDraw.Draw(frame).rectangle([0, H * (1 - p), W, H], fill=ACCENT + (255,))
            if i > 0 and lt < TRANS:
                p = ease_in_out(lt / TRANS)
                ImageDraw.Draw(frame).rectangle([0, 0, W, H * (1 - p)], fill=ACCENT + (255,))
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    return out, proc.returncode


def slug(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    only = None
    jobs_n = 4
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    if "--jobs" in sys.argv:
        jobs_n = int(sys.argv[sys.argv.index("--jobs") + 1])
    jobs = []
    for subj in parse_md():
        for plat, scenes in subj["videos"].items():
            if only and only != f"{subj['num']}-{plat}":
                continue
            jobs.append((subj, plat, scenes, out_dir))
    with Pool(jobs_n) as pool:
        for out, rc in pool.imap_unordered(render_video, jobs):
            print(("OK " if rc == 0 else "ERREUR ") + out, flush=True)


if __name__ == "__main__":
    main()
