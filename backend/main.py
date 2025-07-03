from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import os
import random
import io
from PIL import Image, ImageEnhance
import numpy as np

# 環境変数読み込み
load_dotenv()

# Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

app = FastAPI()

# static フォルダ公開（画像素材やCSS）
app.mount("/static", StaticFiles(directory="static"), name="static")

# ルートで index.html を返す
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return FileResponse("static/index.html")


# アップロード＆スライム雨合成
@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    # キャラ画像読み込み（RGBA）
    char_img = Image.open(file.file).convert("RGBA")
    width, height = char_img.size

    # スライム雨素材の中からランダム選択（.jpg, .jpeg, .png）
    rain_candidates = [
        f for f in os.listdir("static") if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not rain_candidates:
        return HTMLResponse("<h1>スライム素材が見つかりません</h1>", status_code=500)
    rain_path = os.path.join("static", random.choice(rain_candidates))
    rain_img = Image.open(rain_path).convert("RGBA")

    # 雨素材の縮小（スライム雨サイズ調整）
    scale = random.uniform(0.1, 0.2)
    rain_size = (int(rain_img.width * scale), int(rain_img.height * scale))
    rain_img = rain_img.resize(rain_size)

    # 合成キャンバス作成
    combined = char_img.copy()

    # ランダムな位置にスライム雨を複数合成
    num_rain = random.randint(20, 35)
    for _ in range(num_rain):
        x = random.randint(0, width - rain_size[0])
        y = random.randint(0, int(height * 0.6))  # 上半分を中心に
        combined.alpha_composite(rain_img, (x, y))

    # RGBA → RGB（白背景合成）
    background = Image.new("RGB", combined.size, (255, 255, 255))
    background.paste(combined, mask=combined.split()[3])

    # Cloudinaryへアップロード
    buffer = io.BytesIO()
    background.save(buffer, format="JPEG")
    buffer.seek(0)
    result = cloudinary.uploader.upload(buffer, folder="uploads/")
    image_url = result.get("secure_url")

    # HTMLレスポンス返却
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>合成結果</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>スライム雨 合成完了！</h1>
        <p>以下が合成結果です：</p>
        <img src="{image_url}" alt="合成画像" style="max-width: 100%; height: auto;">
        <br><br>
        <a href="/">← 戻る</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
