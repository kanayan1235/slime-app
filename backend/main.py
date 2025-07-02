from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import os
import random
import math
from uuid import uuid4

app = FastAPI()

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
KEFIR_FOLDER = "kefirs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(KEFIR_FOLDER, exist_ok=True)  # 空でもOK

def stretch_slime(img, scale_y=1.5):
    w, h = img.size
    return img.resize((w, int(h * scale_y)), resample=Image.BICUBIC)

def apply_alpha_gradient(img, min_alpha=0.7):
    arr = np.array(img)
    h = arr.shape[0]
    gradient = np.linspace(0.95, min_alpha, h).reshape(-1, 1)
    alpha = arr[:, :, 3].astype(np.float32)
    arr[:, :, 3] = (alpha * gradient).astype(np.uint8)
    return Image.fromarray(arr, 'RGBA')

def rotate_toward_center(x, y, cx, cy):
    dx, dy = cx - x, cy - y
    return math.degrees(math.atan2(dy, dx)) - 90

def generate_slime(canvas_size, count=25):
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    slime_paths = [os.path.join(KEFIR_FOLDER, f) for f in os.listdir(KEFIR_FOLDER) if f.endswith((".png", ".jpg"))]
    if not slime_paths:
        return canvas
    for _ in range(count):
        slime_img = Image.open(random.choice(slime_paths)).convert("RGBA")
        scale = random.uniform(0.1, 0.4)
        slime = slime_img.resize((int(slime_img.width * scale), int(slime_img.height * scale)))
        slime = stretch_slime(slime, random.uniform(1.2, 1.8))
        slime = apply_alpha_gradient(slime)
        x = random.randint(0, canvas_size[0])
        y = random.randint(0, canvas_size[1])
        angle = rotate_toward_center(x, y, canvas_size[0]//2, canvas_size[1]//2)
        rotated = slime.rotate(angle, expand=True)
        canvas.paste(rotated, (x, y), rotated)
    return canvas

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # 📁 画像保存
    filename = f"{uuid4().hex}_{file.filename}"
    upload_path = os.path.join(UPLOAD_FOLDER, filename)
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 📷 読み込みと合成
    base_img = Image.open(upload_path).convert("RGBA")
    rain_layer = generate_slime(base_img.size, count=40)
    result = Image.alpha_composite(base_img, rain_layer)

    # 📦 保存して返す
    output_path = os.path.join(OUTPUT_FOLDER, f"result_{filename}.png")
    result.save(output_path)
    return FileResponse(output_path, media_type="image/png")
