# 📦 必要ライブラリ
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from PIL import Image
import numpy as np
import random
import math
import os
import io

# 🌍 環境変数の読み込み
load_dotenv()
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# 🚀 FastAPI初期化とstaticフォルダのマウント
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🎨 画像加工関数
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

def generate_slime_rain_field(base_img, canvas_size, center_x, center_y, count=15):
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    for _ in range(count):
        scale = random.uniform(0.1, 0.8)
        w, h = base_img.size
        new_size = (int(w * scale), int(h * scale))
        slime = base_img.resize(new_size, resample=Image.BICUBIC)
        slime = stretch_slime(slime, scale_y=random.uniform(1.3, 2.0))
        slime = apply_alpha_gradient(slime)

        x = random.randint(0, canvas_size[0])
        y = random.randint(0, canvas_size[1] // 2)
        angle = rotate_toward_center(x, y, center_x, center_y)
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
        base_arr[:, :, c] *= (1 - mask * intensity)
    base_arr = np.clip(base_arr, 0, 255).astype(np.uint8)
    return Image.fromarray(base_arr, 'RGBA')

# 🏠 ルート：アップロードフォーム
@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse("static/index.html")

# 📤 POST：画像アップロードと合成処理
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    character_img = Image.open(file.file).convert("RGBA")
    canvas_w, canvas_h = character_img.size
    center_x, center_y = canvas_w // 2, canvas_h // 2

    # 📂 backend/kefirs 内からPNG/JPEG画像をランダム選択
    kefir_dir = "backend/kefirs"
    candidates = [f for f in os.listdir(kefir_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    slime_path = os.path.join(kefir_dir, random.choice(candidates))
    slime_img = Image.open(slime_path).convert("RGBA")

    slime_field = generate_slime_rain_field(slime_img, character_img.size, center_x, center_y)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(character_img, contact_mask, intensity=0.4)
    combined = Image.alpha_composite(character_wet, slime_field)

    # JPEGへ変換してCloudinaryへ保存
    background = Image.new("RGB", combined.size, (255, 255, 255))
    background.paste(combined, mask=combined.split()[3])
    buffer = io.BytesIO()
    background.save(buffer, format="JPEG")
    buffer.seek(0)

    result = cloudinary.uploader.upload(buffer, folder="uploads/")
    image_url = result.get("secure_url")

    # HTMLを直接返す
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>スライム雨合成</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>スライム雨 合成完了！</h1>
        <img src="{image_url}" alt="合成画像" style="max-width: 100%;">
        <br><br>
        <a href="/">← 戻る</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
