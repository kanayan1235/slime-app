from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
from PIL import Image, ImageEnhance, ImageFilter
import io
import random

# 環境変数読み込み
load_dotenv()

# Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# FastAPI初期化
app = FastAPI()

# 静的ファイルとテンプレート設定
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# 📌 スライム雨合成関数
def apply_slime_rain(character_img: Image.Image, rain_img: Image.Image) -> Image.Image:
    width, height = character_img.size
    rain_composite = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    num_rains = random.randint(10, 20)
    for _ in range(num_rains):
        scale = random.uniform(0.1, 0.2)
        r = rain_img.copy()
        r = r.resize((int(r.width * scale), int(r.height * scale)))
        x = random.randint(0, width - r.width)
        y = random.randint(0, height - r.height)
        rain_composite.paste(r, (x, y), r)

    # 合成
    combined = Image.alpha_composite(character_img, rain_composite)

    # シャドウと輝度調整
    combined = combined.filter(ImageFilter.GaussianBlur(radius=0.5))
    enhancer = ImageEnhance.Brightness(combined)
    combined = enhancer.enhance(1.1)

    return combined


# ルート：フォーム表示
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# POSTアップロード処理（人物画像＋スライム雨画像）
@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...), slime: UploadFile = File(...)):
    character_img = Image.open(file.file).convert("RGBA")
    rain_img = Image.open(slime.file).convert("RGBA")

    # スライム雨合成処理
    result_img = apply_slime_rain(character_img, rain_img)

    # JPEG対応：白背景と合成
    background = Image.new("RGB", result_img.size, (255, 255, 255))
    background.paste(result_img, mask=result_img.split()[3])

    buffer = io.BytesIO()
    background.save(buffer, format="JPEG")
    buffer.seek(0)

    # Cloudinaryにアップロード
    result = cloudinary.uploader.upload(buffer, folder="uploads/")
    image_url = result.get("secure_url")

    return templates.TemplateResponse("result.html", {
        "request": request,
        "image_url": image_url
    })
