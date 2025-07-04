from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from PIL import Image
import numpy as np
import random
import math
import os
import io

# .envから環境変数を読み込む
load_dotenv()

# Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# FastAPIアプリ初期化
app = FastAPI()

# staticとtemplatesの設定
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 中心へ向けて回転角を計算
def rotate_toward_center(x, y, cx, cy):
    dx = cx - x
    dy = cy - y
    angle = math.degrees(math.atan2(dy, dx)) - 90
    return angle

# スライム雨の合成
def generate_slime_rain_field(base_img, canvas_size, center_x, center_y, count=3
):
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    for _ in range(count):
        scale = random.uniform(0.1, 0.8)
        w, h = base_img.size
        slime = base_img.resize((int(w * scale), int(h * scale)), resample=Image.BICUBIC)
        slime = slime.resize((slime.width, int(slime.height * random.uniform(1.3, 2.0))), resample=Image.BICUBIC)

        # アルファグラデーション
        arr = np.array(slime)
        height = arr.shape[0]
        gradient = np.linspace(1.0, 0.6, height).reshape(-1, 1)
        alpha = arr[:, :, 3].astype(np.float32)
        arr[:, :, 3] = (alpha * gradient).astype(np.uint8)
        slime = Image.fromarray(arr, 'RGBA')

        x = random.randint(0, canvas_size[0])
        y = random.randint(0, canvas_size[1] // 2)
        angle = rotate_toward_center(x, y, center_x, center_y)
        rotated = slime.rotate(angle, expand=True, resample=Image.BICUBIC)
        canvas.paste(rotated, (x, y), rotated)
    return canvas

# スライム接触マスク
def get_contact_mask(slime_rgba):
    alpha = np.array(slime_rgba)[:, :, 3]
    return (alpha > 30).astype(np.uint8) * 255

# 濡れ効果を加える
def apply_wet_effect(base_rgba, contact_mask, intensity=0.4):
    base_arr = np.array(base_rgba).astype(np.float32)
    mask = contact_mask / 255.0
    for c in range(3):
        base_arr[:, :, c] *= (1 - mask * intensity)
    return Image.fromarray(np.clip(base_arr, 0, 255).astype(np.uint8), 'RGBA')

# indexページ
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# アップロード＆合成処理
@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    # アップロード画像をRGBAで読み込み
    character_img = Image.open(file.file).convert("RGBA")
    canvas_w, canvas_h = character_img.size
    center_x, center_y = canvas_w // 2, canvas_h // 2

    # スライム素材フォルダからランダム選択
    kefir_dir = "backend/kefirs"
    slime_files = [f for f in os.listdir(kefir_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    slime_path = os.path.join(kefir_dir, random.choice(slime_files))
    slime_base = Image.open(slime_path).convert("RGBA")

    # 合成処理
    slime_field = generate_slime_rain_field(slime_base, character_img.size, center_x, center_y)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(character_img, contact_mask)
    combined = Image.alpha_composite(character_wet, slime_field)

    # JPEGに変換しバッファ保存
    background = Image.new("RGB", combined.size, (255, 255, 255))
    background.paste(combined, mask=combined.split()[3])
    buffer = io.BytesIO()
    background.save(buffer, format="JPEG")
    buffer.seek(0)

    # Cloudinaryへアップロード
    result = cloudinary.uploader.upload(buffer, folder="uploads/")
    image_url = result.get("secure_url")

    return templates.TemplateResponse("result.html", {
        "request": request,
        "image_url": image_url
    })
