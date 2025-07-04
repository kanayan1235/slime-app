from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from PIL import Image
import numpy as np
import os
import io
import random
import math
import requests

# 環境変数読み込み
load_dotenv()

# Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# FastAPIアプリ初期化
app = FastAPI()

# staticフォルダをマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# 雨素材ディレクトリ（jpeg, jpg, png対応）
RAIN_DIR = "backend/kefirs"

def get_random_rain_image():
    files = [f for f in os.listdir(RAIN_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    path = os.path.join(RAIN_DIR, random.choice(files))
    return Image.open(path).convert("RGBA")

# 合成処理関数
def combine_images(person_img: Image.Image, rain_img: Image.Image) -> Image.Image:
    canvas_w, canvas_h = person_img.size
    center_x, center_y = canvas_w // 2, canvas_h // 2

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

    def generate_slime_rain_field(base_img, canvas_size, count=3
):
        canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
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

    rain_layer = generate_slime_rain_field(rain_img, person_img.size)
    contact_mask = get_contact_mask(rain_layer)
    wet_person = apply_wet_effect(person_img, contact_mask)
    combined = Image.alpha_composite(wet_person, rain_layer)
    return combined

# ルート：アップロードフォーム
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>スライム雨合成</title>
    </head>
    <body>
        <h2>人物画像をアップロードしてスライム雨を合成！</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept="image/*" required>
            <input type="submit" value="アップロードして合成">
        </form>
    </body>
    </html>
    """

# POST：アップロード & 合成 & Cloudinary保存
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    person_img = Image.open(file.file).convert("RGBA")
    rain_img = get_random_rain_image()
    combined = combine_images(person_img, rain_img)

    buffer = io.BytesIO()
    combined.save(buffer, format="PNG")
    buffer.seek(0)

    result = cloudinary.uploader.upload(buffer, folder="slime/")
    image_url = result.get("secure_url")

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>合成完了</title>
    </head>
    <body>
        <h1>スライム雨 合成完了！</h1>
        <img src="{image_url}" style="max-width: 100%; height: auto;" alt="スライム画像">
        <p><a href="/">もう一度合成する</a></p>
    </body>
    </html>
    """)
