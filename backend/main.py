from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os
from PIL import Image
import io
import random

# 環境変数の読み込み
load_dotenv()

# Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# FastAPIアプリ初期化
app = FastAPI()

# static ディレクトリのマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# index.htmlをルートで表示
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return FileResponse("static/index.html")

# アップロード処理と画像合成＋Cloudinaryアップロード
@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    image = Image.open(file.file).convert("RGBA")
    width, height = image.size

    # スライム雨素材（.jpg/.jpeg/.pngのいずれか）を読み込み
    rain_path = None
    for fname in os.listdir("static"):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            rain_path = os.path.join("static", fname)
            break

    if not rain_path:
        return HTMLResponse("<h1>雨素材画像が見つかりません</h1>", status_code=400)

    rain_img = Image.open(rain_path).convert("RGBA")

    # ランダムな雨の合成
    for _ in range(100):
        scale = random.uniform(0.1, 0.2)
        rain_resized = rain_img.resize(
            (int(rain_img.width * scale), int(rain_img.height * scale))
        )
        x = random.randint(0, width - rain_resized.width)
        y = random.randint(0, height - rain_resized.height)
        image.alpha_composite(rain_resized, dest=(x, y))

    # JPEG変換（白背景にする）
    background = Image.new("RGB", image.size, (255, 255, 255))
    background.paste(image, mask=image.split()[3])

    # Cloudinaryにアップロード
    buffer = io.BytesIO()
    background.save(buffer, format="JPEG")
    buffer.seek(0)
    result = cloudinary.uploader.upload(buffer, folder="uploads/")
    image_url = result.get("secure_url")

    # レスポンスHTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>合成完了</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>スライム雨 合成完了！</h1>
        <p>以下がアップロード画像と雨の合成結果です。</p>
        <img src="{image_url}" alt="合成画像" style="max-width: 100%; height: auto;">
        <br><br>
        <a href="/">← 戻る</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
