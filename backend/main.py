from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from PIL import Image
import numpy as np
import random
import math
import io
import os

# .env読み込み
load_dotenv()

# Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# アプリ初期化
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# 雨素材読み込み
KEFIR_DIR = "backend/kefirs"
def get_random_kefir_image():
    exts = (".png", ".jpg", ".jpeg")
    images = [f for f in os.listdir(KEFIR_DIR) if f.lower().endswith(exts)]
    if not images:
        raise FileNotFoundError("kefirsフォルダに画像がありません")
    return os.path.join(KEFIR_DIR, random.choice(images))

# スライム合成関数
def generate_slime_effect(character_img):
    rain_base = Image.open(get_random_kefir_image()).convert("RGBA")
    canvas_w, canvas_h = character_img.size
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
        return math.degrees(math.atan2(dy, dx)) - 90

    def generate_slime_rain_field(base_img, canvas_size, count=3
):
        canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        for _ in range(count):
            scale = random.uniform(0.1, 0.8)
            slime = base_img.resize(
                (int(base_img.width * scale), int(base_img.height * scale)),
                resample=Image.BICUBIC,
            )
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

    def apply_wet_effect(base_rgba, contact_mask, intensity=0.4):
        base_arr = np.array(base_rgba).astype(np.float32)
        mask = contact_mask / 255.0
        for c in range(3):
            base_arr[:, :, c] = base_arr[:, :, c] * (1 - mask * intensity)
        base_arr = np.clip(base_arr, 0, 255).astype(np.uint8)
        return Image.fromarray(base_arr, 'RGBA')

    slime_field = generate_slime_rain_field(rain_base, character_img.size)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(character_img, contact_mask)
    return Image.alpha_composite(character_wet, slime_field)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    original_img = Image.open(file.file).convert("RGBA")
    combined = generate_slime_effect(original_img)

    buffer = io.BytesIO()
    combined.convert("RGB").save(buffer, format="JPEG")
    buffer.seek(0)

    result = cloudinary.uploader.upload(buffer, folder="slime/")
    image_url = result.get("secure_url")

    return templates.TemplateResponse("result.html", {
        "request": request,
        "image_url": image_url
    })

@app.post("/reapply")
async def reapply(request: Request, image_url: str = Form(...)):
    response = cloudinary.uploader.download(image_url)
    original_img = Image.open(io.BytesIO(response)).convert("RGBA")
    combined = generate_slime_effect(original_img)

    buffer = io.BytesIO()
    combined.convert("RGB").save(buffer, format="JPEG")
    buffer.seek(0)

    result = cloudinary.uploader.upload(buffer, folder="slime/")
    image_url = result.get("secure_url")

    return templates.TemplateResponse("result.html", {
        "request": request,
        "image_url": image_url
    })
