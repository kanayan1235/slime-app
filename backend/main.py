# backend/main.py

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

# .env 読み込み
load_dotenv()

# Cloudinary 設定（Render 環境変数に設定する場合）
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# アプリ初期化
app = FastAPI()

# static/index.html に対応
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2テンプレート
templates = Jinja2Templates(directory="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """アップロードフォームを表示"""
    return templates.TemplateResponse("index.html", {"request": request, "image_url": None})


@app.post("/upload", response_class=HTMLResponse)
async def upload_image(request: Request, file: UploadFile = File(...)):
    """画像アップロードとCloudinaryへの保存処理"""
    filename = file.filename.lower()
    if not filename.endswith((".jpg", ".jpeg", ".png")):
        return templates.TemplateResponse("index.html", {
            "request": request,
            "image_url": None,
            "error": "JPEG または PNG 画像のみアップロード可能です。"
        })

    try:
        result = cloudinary.uploader.upload(file.file, public_id=None, folder="slime-uploads")
        image_url = result["secure_url"]
        return templates.TemplateResponse("index.html", {"request": request, "image_url": image_url})
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "image_url": None,
            "error": f"アップロードエラー: {str(e)}"
        })
