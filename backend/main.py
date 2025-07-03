# 📦 必要ライブラリの読み込み
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import os
import random
import io
import requests
import numpy as np
import math
from PIL import Image

# 🌐 環境変数の読み込み
load_dotenv()

# ☁️ Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# 🚀 FastAPIアプリ初期化
app = FastAPI()

# 📁 staticとtemplatesの設定
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# 💧 ドロ〜っと縦に伸ばす
def stretch_slime(img, scale_y=5.5):
    w, h = img.size
    return img.resize((w, int(h * scale_y)), resample=Image.BICUBIC)

# 🌫 アルファグラデーション（上100% → 下60%）
def apply_alpha_gradient(img, min_alpha=0.6):
    arr = np.array(img)
    h = arr.shape[0]
    gradient = np.linspace(1.0, min_alpha, h).reshape(-1, 1)
    alpha = arr[:, :, 3].astype(np.float32)
    alpha = (alpha * gradient).astype(np.uint8)
    arr[:, :, 3] = alpha
    return Image.fromarray(arr, 'RGBA')

# 🔄 中心へ向けて角度計算
def rotate_toward_center(x, y, cx, cy):
    dx = cx - x
    dy = cy - y
    angle = math.degrees(math.atan2(dy, dx)) - 90
    return angle

# ☔ スライム雨生成
def generate_slime_rain_field(base_img, canvas_size, cx, cy, count=5
):
    canvas = Image.new("RGBA", canvas_size, (0,0,0,0))
    for _ in range(count):
        scale = random.uniform(0.1, 0.8)
        slime = base_img.resize((int(base_img.width * scale), int(base_img.height * scale)), resample=Image.BICUBIC)
        slime = stretch_slime(slime, scale_y=random.uniform(1.3, 2.0))
        slime = apply_alpha_gradient(slime, min_alpha=0.6)
        x = random.randint(0, canvas_size[0])
        y = random.randint(0, canvas_size[1] // 2)
        angle = rotate_toward_center(x, y, cx, cy)
        rotated = slime.rotate(angle, expand=True, resample=Image.BICUBIC)
        canvas.paste(rotated, (x, y), rotated)
    return canvas

# 🎭 接触マスク生成
def get_contact_mask(slime_rgba):
    alpha = np.array(slime_rgba)[:, :, 3]
    return (alpha > 30).astype(np.uint8) * 255

# 💧 濡れエフェクト
def apply_wet_effect(base_rgba, contact_mask, intensity=0.35):
    base_arr = np.array(base_rgba).astype(np.float32)
    mask = contact_mask / 255.0
    for c in range(3):
        base_arr[:, :, c] = base_arr[:, :, c] * (1 - mask * intensity)
    base_arr = np.clip(base_arr, 0, 255).astype(np.uint8)
    return Image.fromarray(base_arr, 'RGBA')

# 🏠 index表示
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 📤 画像アップロード
@app.post("/upload")
def upload(request: Request, file: UploadFile = File(...)):
    image = Image.open(file.file).convert("RGBA")
    canvas_w, canvas_h = image.size
    cx, cy = canvas_w // 2, canvas_h // 2
    
    slime_path = random.choice([
        os.path.join("backend/kefirs", f) for f in os.listdir("backend/kefirs")
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ])
    rain_base = Image.open(slime_path).convert("RGBA")

    slime_field = generate_slime_rain_field(rain_base, image.size, cx, cy)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(image, contact_mask, intensity=0.4)
    combined = Image.alpha_composite(character_wet, slime_field)

    buffer = io.BytesIO()
    combined.convert("RGB").save(buffer, format="JPEG")
    buffer.seek(0)
    result = cloudinary.uploader.upload(buffer, folder="uploads/")
    image_url = result.get("secure_url")

    return templates.TemplateResponse("result.html", {"request": request, "image_url": image_url})

# 🔁 スライム雨を追加合成
@app.post("/reapply")
def reapply(request: Request, image_url: str = Form(...)):
    response = requests.get(image_url)
    image = Image.open(io.BytesIO(response.content)).convert("RGBA")
    canvas_w, canvas_h = image.size
    cx, cy = canvas_w // 2, canvas_h // 2

    slime_path = random.choice([
        os.path.join("backend/kefirs", f) for f in os.listdir("backend/kefirs")
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ])
    rain_base = Image.open(slime_path).convert("RGBA")

    slime_field = generate_slime_rain_field(rain_base, image.size, cx, cy)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(image, contact_mask, intensity=0.4)
    combined = Image.alpha_composite(character_wet, slime_field)

    buffer = io.BytesIO()
    combined.convert("RGB").save(buffer, format="JPEG")
    buffer.seek(0)
    result = cloudinary.uploader.upload(buffer, folder="uploads/")
    new_url = result.get("secure_url")

    return templates.TemplateResponse("result.html", {"request": request, "image_url": new_url})


以下は、あなたのスライム雨合成Webアプリの完全なセット（main.py + HTML）です：


---

✅ main.py

上記の内容を [Slime Rain App] に保存しました。


---

✅ static/index.html

<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>スライム雨アップローダー</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>スライム雨を降らせよう！</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*" required>
        <button type="submit">アップロードして合成</button>
    </form>
</body>
</html>


---

✅ static/result.html

<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>スライム雨 合成結果</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>スライム雨 合成完了！</h1>
    <img src="{{ image_url }}" alt="合成画像" style="max-width: 100%; height: auto;">
    <form action="/reapply" method="post">
        <input type="hidden" name="image_url" value="{{ image_url }}">
        <button type="submit">さらにスライム雨を追加する</button>
    </form>
    <br>
    <a href="/">← 戻る</a>
</body>
</html>


---

backend/kefirs/ にスライム素材（PNG, JPG, JPEG）を複数置けば、ランダムに読み込んで合成されます。

次に必要な要素（CSSやCloudinary動作確認など）があれば、お知らせください。

