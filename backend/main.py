from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from PIL import Image
import numpy as np
import random, math

app = FastAPI()

# CORS設定（任意のドメインからアクセス許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# static/index.html をルートで返す
@app.get("/", response_class=HTMLResponse)
def read_index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

# staticフォルダを公開（画像表示やCSS/JS用）
app.mount("/static", StaticFiles(directory="static"), name="static")

# スライムを縦に引き伸ばす
def stretch_slime(img, scale_y=5.5):
    w, h = img.size
    return img.resize((w, int(h * scale_y)), resample=Image.BICUBIC)

# アルファグラデーション（上100% → 下60%）
def apply_alpha_gradient(img, min_alpha=0.6):
    arr = np.array(img)
    h = arr.shape[0]
    gradient = np.linspace(1.0, min_alpha, h).reshape(-1, 1)
    alpha = arr[:, :, 3].astype(np.float32)
    alpha = (alpha * gradient).astype(np.uint8)
    arr[:, :, 3] = alpha
    return Image.fromarray(arr, 'RGBA')

# 回転角の計算（中心に向かう角度）
def rotate_toward_center(x, y, cx, cy):
    dx = cx - x
    dy = cy - y
    angle = math.degrees(math.atan2(dy, dx)) - 90
    return angle

# スライム雨の合成
def generate_slime_rain_field(base_img, canvas_size, center_x, center_y, count=120):
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
        angle = rotate_toward_center(x, y, center_x, center_y)
        rotated = slime.rotate(angle, expand=True, resample=Image.BICUBIC)
        canvas.paste(rotated, (x, y), rotated)
    return canvas

# 接触マスク作成（アルファを白黒化）
def get_contact_mask(slime_rgba):
    alpha = np.array(slime_rgba)[:, :, 3]
    return (alpha > 30).astype(np.uint8) * 255

# 濡れエフェクト（暗くする）
def apply_wet_effect(base_rgba, contact_mask, intensity=0.35):
    base_arr = np.array(base_rgba).astype(np.float32)
    mask = contact_mask / 255.0
    for c in range(3):
        base_arr[:, :, c] = base_arr[:, :, c] * (1 - mask * intensity)
    base_arr = np.clip(base_arr, 0, 255).astype(np.uint8)
    return Image.fromarray(base_arr, 'RGBA')

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # 保存
    uploaded_path = f"uploaded_{file.filename}"
    with open(uploaded_path, "wb") as f:
        f.write(await file.read())

    # 読み込み
    character_img = Image.open(uploaded_path).convert("RGBA")
    canvas_w, canvas_h = character_img.size
    center_x, center_y = canvas_w // 2, canvas_h // 2

    # kefirs/ からランダムに雨画像
    kefir_dir = "backend/kefirs"
    kefir_files = [f for f in os.listdir(kefir_dir) if f.endswith(".png")]
    if not kefir_files:
        return {"error": "ケフィア雨画像がありません"}
    rain_path = os.path.join(kefir_dir, random.choice(kefir_files))
    rain_base = Image.open(rain_path).convert("RGBA")

    # 合成
    slime_field = generate_slime_rain_field(rain_base, character_img.size, center_x, center_y)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(character_img, contact_mask, intensity=0.4)
    combined = Image.alpha_composite(character_wet, slime_field)

    # 保存＆返却
    result_path = "static/result.png"
    combined.save(result_path)
    return FileResponse(result_path)
