from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import numpy as np
import os
import random
import math
from io import BytesIO

app = FastAPI()

from fastapi.staticfiles import StaticFiles

# ⛳ static をルートからマウント
app.mount("/", StaticFiles(directory="static", html=True), name="static")
# 画像合成系関数（コラボと同じ処理）
def stretch_slime(img, scale_y=5.5):
    w, h = img.size
    return img.resize((w, int(h * scale_y)), resample=Image.BICUBIC)

def apply_alpha_gradient(img, min_alpha=0.6):
    arr = np.array(img)
    h = arr.shape[0]
    gradient = np.linspace(1.0, min_alpha, h).reshape(-1, 1)
    alpha = arr[:, :, 3].astype(np.float32)
    alpha = (alpha * gradient).astype(np.uint8)
    arr[:, :, 3] = alpha
    return Image.fromarray(arr, 'RGBA')

def rotate_toward_center(x, y, cx, cy):
    dx = cx - x
    dy = cy - y
    angle = math.degrees(math.atan2(dy, dx)) - 90
    return angle

def generate_slime_rain_field(base_img, canvas_size, center, count=120):
    canvas = Image.new("RGBA", canvas_size, (0,0,0,0))
    for _ in range(count):
        scale = random.uniform(0.1, 0.8)
        w, h = base_img.size
        new_size = (int(w * scale), int(h * scale))
        slime = base_img.resize(new_size, resample=Image.BICUBIC)
        slime = stretch_slime(slime, scale_y=random.uniform(1.3, 2.0))
        slime = apply_alpha_gradient(slime, min_alpha=0.6)
        x = random.randint(0, canvas_size[0])
        y = random.randint(0, canvas_size[1] // 2)
        angle = rotate_toward_center(x, y, center[0], center[1])
        rotated = slime.rotate(angle, expand=True, resample=Image.BICUBIC)
        canvas.paste(rotated, (x, y), rotated)
    return canvas

def get_contact_mask(slime_rgba):
    alpha = np.array(slime_rgba)[:, :, 3]
    return (alpha > 30).astype(np.uint8) * 255

def apply_wet_effect(base_rgba, contact_mask, intensity=0.35):
    base_arr = np.array(base_rgba).astype(np.float32)
    mask = contact_mask / 255.0
    for c in range(3):
        base_arr[:, :, c] = base_arr[:, :, c] * (1 - mask * intensity)
    base_arr = np.clip(base_arr, 0, 255).astype(np.uint8)
    return Image.fromarray(base_arr, 'RGBA')

# POST: /upload
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    img = Image.open(BytesIO(await file.read())).convert("RGBA")
    canvas_w, canvas_h = img.size
    center_x, center_y = canvas_w // 2, canvas_h // 2

    # ランダムにケフィア雨PNG選択
    kefir_files = [f for f in os.listdir("backend/kefirs") if f.lower().endswith(".png")]
    if not kefir_files:
        return {"error": "kefirs フォルダに PNG がありません"}
    kefir_path = os.path.join("backend/kefirs", random.choice(kefir_files))
    rain_base = Image.open(kefir_path).convert("RGBA")

    # 合成処理
    slime_field = generate_slime_rain_field(rain_base, img.size, (center_x, center_y))
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(img, contact_mask, intensity=0.4)
    combined = Image.alpha_composite(character_wet, slime_field)

    # 画像バッファに保存して返却
    output = BytesIO()
    combined.save(output, format="PNG")
    output.seek(0)
    return FileResponse(output, media_type="image/png", filename="result.png")
