from PIL import Image, ImageDraw, ImageFont
import os

def make_icon():
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # خلفية دائرية زرقاء متدرجة (محاكاة gradient)
    for r in range(size // 2, 0, -1):
        ratio = r / (size // 2)
        color = (
            int(21 + (13 - 21) * (1 - ratio)),
            int(101 + (71 - 101) * (1 - ratio)),
            int(192 + (161 - 192) * (1 - ratio)),
            255,
        )
        x0 = size // 2 - r
        y0 = size // 2 - r
        draw.ellipse([x0, y0, x0 + 2 * r, y0 + 2 * r], fill=color)

    # حرف A أبيض
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 300)
    except Exception:
        font = ImageFont.load_default()

    text = "A"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1] - 15),
              text, font=font, fill=(255, 255, 255, 255))

    os.makedirs("assets", exist_ok=True)
    img.save("assets/icon.png")
    print("✅ تم إنشاء assets/icon.png")

if __name__ == "__main__":
    make_icon()
