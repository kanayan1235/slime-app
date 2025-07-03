from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import numpy as np
import math
import random
import os
import shutil
import cloudinary.uploader
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

# Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

app = FastAPI()

# パス設定
UPLOAD_DIR = "backend/uploaded"
RESULT_DIR = "backend/results"
STATIC_DIR = "static"
KEFIR_DIR = "backend/kefirs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# 静的ファイル公開
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def get_random_kefir_image():
    valid_exts = (".jpg", ".jpeg", ".png")
    files = [f for f in os.listdir(KEFIR_DIR) if f.lower().endswith(valid_exts)]
    if not files:
        raise FileNotFoundError("ケフィア画像が見つかりません。")
    return os.path.join(KEFIR_DIR, random.choice(files))

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    upload_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(upload_path, "wb") as f:
        f.write(await file.read())

    character_img = Image.open(upload_path).convert("RGBA")
    rain_base = Image.open(get_random_kefir_image()).convert("RGBA")
    canvas_w, canvas_h = character_img.size
    center_x, center_y = canvas_w // 2, canvas_h // 2

    def stretch_slime(img, scale_y=5.5):
        w, h = img.size
        return img.resize((w, int(h * scale_y)), Image.BICUBIC)

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

    def generate_slime_field(base_img, size, count=120):
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        for _ in range(count):
            scale = random.uniform(0.1, 0.8)
            slime = base_img.resize((int(base_img.width * scale), int(base_img.height * scale)), Image.BICUBIC)
            slime = stretch_slime(slime, random.uniform(1.3, 2.0))
            slime = apply_alpha_gradient(slime)
            x = random.randint(0, size[0])
            y = random.randint(0, size[1] // 2)
            angle = rotate_toward_center(x, y, center_x, center_y)
            rotated = slime.rotate(angle, expand=True, resample=Image.BICUBIC)
            canvas.paste(rotated, (x, y), rotated)
        return canvas

    def get_contact_mask(img):
        alpha = np.array(img)[:, :, 3]
        return (alpha > 30).astype(np.uint8) * 255

    def apply_wet_effect(img, mask, intensity=0.35):
        arr = np.array(img).astype(np.float32)
        mask = mask / 255.0
        for c in range(3):
            arr[:, :, c] *= (1 - mask * intensity)
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, 'RGBA')

    slime_field = generate_slime_field(rain_base, character_img.size)
    mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(character_img, mask, 0.4)
    combined = Image.alpha_composite(character_wet, slime_field)

    result_filename = f"result_{file.filename.rsplit('.', 1)[0]}.png"
    result_path = os.path.join(RESULT_DIR, result_filename)
    combined.save(result_path)

    # Cloudinaryへアップロード
    upload_result = cloudinary.uploader.upload(result_path, folder="slime-rain")
    url = upload_result.get("secure_url")

    # 後処理（保存しない場合は削除しても可）
    os.remove(result_path)

    return JSONResponse(content={"url": url})
