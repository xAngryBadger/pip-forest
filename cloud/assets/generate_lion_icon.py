"""Generate a simple abstract lion icon for the SRF desktop app."""
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow nao instalado – usando icone placeholder vazio.")
    p = Path(__file__).with_name("srf_lion_icon.ico")
    if not p.exists():
        img = __import__("struct")
        # Minimal 16x16 1-bit ICO
        raise SystemExit("Instale Pillow: pip install Pillow")

SIZE = 256
OUT = Path(__file__).with_name("srf_lion_icon.ico")


def draw_lion(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    s = SIZE
    bg = "#d93025"
    fg = "#ffffff"

    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s // 6, fill=bg)

    cx, cy = s // 2, int(s * 0.48)
    r = int(s * 0.28)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fg)

    ear_r = int(s * 0.13)
    for dx in (-1, 1):
        ex = cx + dx * int(r * 0.75)
        ey = cy - int(r * 0.85)
        d.ellipse([ex - ear_r, ey - ear_r, ex + ear_r, ey + ear_r], fill=fg)

    nose_r = int(s * 0.05)
    ny = cy + int(r * 0.15)
    d.ellipse([cx - nose_r, ny - nose_r, cx + nose_r, ny + nose_r], fill=bg)

    eye_r = int(s * 0.04)
    ey = cy - int(r * 0.15)
    for dx in (-1, 1):
        ex = cx + dx * int(r * 0.35)
        d.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r], fill=bg)

    mane_pts = []
    import math
    for i in range(12):
        a = math.radians(i * 30 - 90)
        inner = r + int(s * 0.04)
        outer = r + int(s * 0.12)
        ri = outer if i % 2 == 0 else inner
        mane_pts.append((cx + int(ri * math.cos(a)), cy + int(ri * math.sin(a))))
    d.polygon(mane_pts, fill=fg, outline=fg)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fg)
    d.ellipse([cx - nose_r, ny - nose_r, cx + nose_r, ny + nose_r], fill=bg)
    for dx in (-1, 1):
        ex = cx + dx * int(r * 0.35)
        d.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r], fill=bg)


def main():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw_lion(img)
    sizes = [(s, s) for s in (16, 32, 48, 64, 128, 256)]
    img.save(str(OUT), format="ICO", sizes=sizes)
    print(f"Icon gerado: {OUT}")


if __name__ == "__main__":
    main()
