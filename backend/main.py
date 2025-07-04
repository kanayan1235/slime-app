from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
import cloudinary
import cloudinary.uploader
import numpy as np
import os
import io
import random
import math
import requests
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

app = FastAPI()

# static & template
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="backend/templates")

# スライム雨の合成処理
def generate_slime_rain(character_img, slime_base, count=100):
    canvas_w, canvas_h = character_img.size
    center_x, center_y = canvas_w // 2, canvas_h // 2
    canvas = Image.new("RGBA", character_img.size, (0,0,0,0))

    def stretch_slime(img, scale_y=1.5):
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

    for _ in range(count):
        scale = random.uniform(0.1, 0.8)
        slime = slime_base.resize((int(slime_base.width * scale), int(slime_base.height * scale)))
        slime = stretch_slime(slime, random.uniform(1.3, 2.0))
        slime = apply_alpha_gradient(slime)

        x = random.randint(0, canvas_w)
        y = random.randint(0, canvas_h // 2)
        angle = rotate_toward_center(x, y, center_x, center_y)
        rotated = slime.rotate(angle, expand=True)
        canvas.paste(rotated, (x, y), rotated)
    return canvas

def get_contact_mask(slime_rgba):
    alpha = np.array(slime_rgba)[:, :, 3]
    return (alpha > 30).astype(np.uint8) * 255

def apply_wet_effect(base_rgba, contact_mask, intensity=0.4):
    base_arr = np.array(base_rgba).astype(np.float32)
    mask = contact_mask / 255.0
    for c in range(3):
        base_arr[:, :, c] *= (1 - mask * intensity)
    return Image.fromarray(np.clip(base_arr, 0, 255).astype(np.uint8), 'RGBA')

# ルート表示
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 初回アップロード
@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    character = Image.open(file.file).convert("RGBA")
    slime_files = [f for f in os.listdir("backend/kefirs") if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    slime_path = os.path.join("backend/kefirs", random.choice(slime_files))
    slime = Image.open(slime_path).convert("RGBA")

    slime_field = generate_slime_rain(character, slime)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(character, contact_mask)
    result = Image.alpha_composite(character_wet, slime_field)

    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    buffer.seek(0)

    upload_result = cloudinary.uploader.upload(buffer, folder="uploads/")
    image_url = upload_result["secure_url"]

    return templates.TemplateResponse("result.html", {"request": request, "image_url": image_url})

# 再合成処理
@app.post("/reapply")
async def reapply(request: Request, image_url: str = Form(...)):
    response = requests.get(image_url)
    character = Image.open(io.BytesIO(response.content)).convert("RGBA")
    slime_files = [f for f in os.listdir("backend/kefirs") if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    slime_path = os.path.join("backend/kefirs", random.choice(slime_files))
    slime = Image.open(slime_path).convert("RGBA")

    slime_field = generate_slime_rain(character, slime)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(character, contact_mask)
    result = Image.alpha_composite(character_wet, slime_field)

    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    buffer.seek(0)

    upload_result = cloudinary.uploader.upload(buffer, folder="uploads/")
    new_url = upload_result["secure_url"]

    return templates.TemplateResponse("result.html", {"request": request, "image_url": new_url})
