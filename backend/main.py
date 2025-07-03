from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from PIL import Image
from fastapi.responses import JSONResponse
import numpy as np
import cloudinary
import cloudinary.uploader
import os
import math
import random
import io

# Cloudinary 設定
cloudinary.config(
    cloud_name="dgdqrrrzx",
    api_key="957982971854726",
api_secret="to_cKnWIXNVuLu7FE1Ze1pgzhX4",
    secure=True
)

app = FastAPI()

# static フォルダ公開（任意）
app.mount("/static", StaticFiles(directory="static"), name="static")

# フォルダ設定
KEFIR_DIR = "backend/kefirs"

def get_random_kefir_image():
    valid_exts = (".jpg", ".jpeg", ".png")
    candidates = [f for f in os.listdir(KEFIR_DIR) if f.lower().endswith(valid_exts)]
    if not candidates:
        raise FileNotFoundError("kefir画像が見つかりません（jpeg/png）")
    return os.path.join(KEFIR_DIR, random.choice(candidates))

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # 入力画像読み込み
    image_bytes = await file.read()
    character_img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    # 雨画像の読み込み
    kefir_path = get_random_kefir_image()
    rain_base = Image.open(kefir_path).convert("RGBA")

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
        angle = math.degrees(math.atan2(dy, dx)) - 90
        return angle

    def generate_slime_rain_field(base_img, canvas_size, count=120):
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

    def apply_wet_effect(base_rgba, contact_mask, intensity=0.35):
        base_arr = np.array(base_rgba).astype(np.float32)
        mask = contact_mask / 255.0
        for c in range(3):
            base_arr[:, :, c] = base_arr[:, :, c] * (1 - mask * intensity)
        base_arr = np.clip(base_arr, 0, 255).astype(np.uint8)
        return Image.fromarray(base_arr, 'RGBA')

    # 合成処理
    slime_field = generate_slime_rain_field(rain_base, character_img.size)
    contact_mask = get_contact_mask(slime_field)
    character_wet = apply_wet_effect(character_img, contact_mask, intensity=0.4)
    combined = Image.alpha_composite(character_wet, slime_field)

    # メモリに保存
    buffer = io.BytesIO()
    combined.save(buffer, format="PNG")
    buffer.seek(0)

    # Cloudinaryにアップロード
    result = cloudinary.uploader.upload(
        buffer,
        resource_type="image",
        public_id=f"slime_rain/result_{file.filename}",
        overwrite=True
    )

    return JSONResponse({"url": result["secure_url"]})
