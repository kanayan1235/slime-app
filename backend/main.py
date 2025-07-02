from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import os, random, math
from uuid import uuid4

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
KEFIR_DIR = "kefirs"
RESULT_IMG = "result.png"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    filename = f"{uuid4().hex}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(await file.read())

    final_path = slime_rain_process(filepath)
    return FileResponse(final_path, media_type="image/png")

def slime_rain_process(img_path):
    img = Image.open(img_path).convert("RGBA")
    canvas_w, canvas_h = img.size

    def stretch(img, y_scale): return img.resize((img.width, int(img.height * y_scale)))
    def alpha_gradient(img, min_a=0.7):
        arr = np.array(img)
        h = arr.shape[0]
        gradient = np.linspace(0.95, min_a, h).reshape(-1, 1)
        arr[..., 3] = (arr[..., 3] * gradient).astype(np.uint8)
        return Image.fromarray(arr, 'RGBA')
    def angle_to_center(x, y, cx, cy): return math.degrees(math.atan2(cy - y, cx - x)) - 90
    def wet_effect(base, mask, strength=0.2):
        arr = np.array(base).astype(np.float32)
        mask = mask / 255.0
        for c in range(3):
            arr[..., c] *= (1 - mask * strength)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    def get_mask(rain): return (np.array(rain)[..., 3] > 30).astype(np.uint8) * 255

    rain_files = [os.path.join(KEFIR_DIR, f) for f in os.listdir(KEFIR_DIR) if f.lower().endswith(('.png', '.jpg'))]

    def draw_rain(n, sticky=False):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        for _ in range(n):
            r = Image.open(random.choice(rain_files)).convert("RGBA")
            s = random.uniform(0.1, 0.3) if not sticky else random.uniform(0.15, 0.25)
            r = r.resize((int(r.width * s), int(r.height * s)))
            r = stretch(r, random.uniform(1.5, 2.0) if not sticky else random.uniform(2.0, 2.5))
            r = alpha_gradient(r)
            if sticky:
                r = r.filter(ImageFilter.GaussianBlur(radius=1.2))
                x = random.randint(canvas_w // 5, canvas_w * 4 // 5)
                y = random.randint(int(canvas_h * 0.7), int(canvas_h * 0.95))
            else:
                x = random.randint(0, canvas_w)
                y = random.randint(0, canvas_h // 2)
                tx, ty = canvas_w // 2, canvas_h * 3 // 4
                angle = angle_to_center(x, y, tx, ty)
                r = r.rotate(angle, expand=True)
            layer.paste(r, (x, y), r)
        return layer

    rain1 = draw_rain(30)
    rain2 = draw_rain(20, sticky=True)
    combined = Image.alpha_composite(rain1, rain2)
    mask = get_mask(combined)
    wet = wet_effect(img, mask)
    final = Image.alpha_composite(wet, combined)

    out_path = os.path.join(UPLOAD_DIR, RESULT_IMG)
    final.save(out_path)
    return out_path
