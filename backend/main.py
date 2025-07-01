from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import os, random, io, datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# フォルダ作成
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("kefirs", exist_ok=True)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    upload_path = f"uploads/{now}_{file.filename}"
    with open(upload_path, "wb") as buffer:
        buffer.write(await file.read())

    character_img = Image.open(upload_path).convert("RGBA")
    canvas_w, canvas_h = character_img.size

    # --- スライム合成処理 ---
    rain_paths = [os.path.join("kefirs", f) for f in os.listdir("kefirs") if f.endswith((".png", ".jpg", ".jpeg"))]

    def stretch_slime(img, scale_y=1.5):
        w, h = img.size
        return img.resize((w, int(h * scale_y)), resample=Image.BICUBIC)

    def apply_alpha_gradient(img, min_alpha=0.7):
        arr = np.array(img)
        h = arr.shape[0]
        gradient = np.linspace(0.95, min_alpha, h).reshape(-1, 1)
        alpha = arr[:, :, 3].astype(np.float32)
        arr[:, :, 3] = (alpha * gradient).astype(np.uint8)
        return Image.fromarray(arr, 'RGBA')

    def rotate_toward_center(x, y, cx, cy):
        dx, dy = cx - x, cy - y
        return np.degrees(np.arctan2(dy, dx)) - 90

    def generate_slime_rain(canvas_size, count=30):
        canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        for _ in range(count):
            rain_img = Image.open(random.choice(rain_paths)).convert("RGBA")
            scale = random.uniform(0.1, 0.4)
            slime = rain_img.resize((int(rain_img.width * scale), int(rain_img.height * scale)))
            slime = stretch_slime(slime, scale_y=random.uniform(1.3, 2.0))
            slime = apply_alpha_gradient(slime)
            x = random.randint(0, canvas_size[0])
            y = random.randint(0, canvas_size[1] // 2)
            target_x = random.randint(canvas_w // 5, canvas_w * 4 // 5)
            target_y = random.randint(canvas_h // 4, canvas_h * 9 // 10)
            angle = rotate_toward_center(x, y, target_x, target_y)
            rotated = slime.rotate(angle, expand=True)
            canvas.paste(rotated, (x, y), rotated)
        return canvas

    def generate_sticky_slime(canvas_size, count=20):
        canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        for _ in range(count):
            rain_img = Image.open(random.choice(rain_paths)).convert("RGBA")
            scale = random.uniform(0.12, 0.22)
            slime = rain_img.resize((int(rain_img.width * scale), int(rain_img.height * scale)))
            slime = stretch_slime(slime, scale_y=random.uniform(1.8, 2.5))
            slime = apply_alpha_gradient(slime)
            slime = slime.filter(ImageFilter.GaussianBlur(radius=1.2))
            x = random.randint(canvas_w // 5, canvas_w * 4 // 5)
            y = random.randint(int(canvas_h * 0.7), int(canvas_h * 0.95))
            canvas.paste(slime, (x, y), slime)
        return canvas

    def get_contact_mask(rain_img):
        alpha = np.array(rain_img)[:, :, 3]
        return (alpha > 30).astype(np.uint8) * 255

    def apply_wet_effect(base_img, contact_mask, intensity=0.25):
        arr = np.array(base_img).astype(np.float32)
        mask = contact_mask / 255.0
        for c in range(3):
            arr[:, :, c] *= (1 - mask * intensity)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')

    def adjust_image_final(image, brightness=1.05, shadow=0.98, highlight=1.1):
        enhancer_b = ImageEnhance.Brightness(image)
        img = enhancer_b.enhance(brightness)
        arr = np.array(img).astype(np.float32)
        shadow_mask = (arr[..., :3] < 128).astype(np.float32)
        arr[..., :3] *= (1 - shadow_mask * (1 - shadow))
        highlight_mask = (arr[..., :3] >= 128).astype(np.float32)
        arr[..., :3] *= (1 + highlight_mask * (highlight - 1))
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, 'RGBA')

    rain_normal = generate_slime_rain(character_img.size, count=30)
    rain_sticky = generate_sticky_slime(character_img.size, count=20)
    rain_combined = Image.alpha_composite(rain_normal, rain_sticky)
    mask = get_contact_mask(rain_combined)
    wet_img = apply_wet_effect(character_img, mask, intensity=0.25)
    final_img = Image.alpha_composite(wet_img, rain_combined)
    final_img = adjust_image_final(final_img)

    output_path = f"outputs/slime_{now}.png"
    final_img.save(output_path)
    return FileResponse(output_path, media_type="image/png")
