from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import random, io, os

app = FastAPI()

# スライム画像フォルダ
kefirs_dir = "kefirs"
rain_files = [f for f in os.listdir(kefirs_dir) if f.endswith((".png", ".jpg", ".jpeg"))]
rain_paths = [os.path.join(kefirs_dir, f) for f in rain_files]

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <h1>Slime Rain App</h1>
    <form action="/upload" enctype="multipart/form-data" method="post">
        <input name="file" type="file" accept="image/*">
        <input type="submit">
    </form>
    """

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    character_img = Image.open(io.BytesIO(contents)).convert("RGBA")
    canvas_w, canvas_h = character_img.size

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

    def generate_rain(canvas_size, count=30):
        canvas = Image.new("RGBA", canvas_size, (0,0,0,0))
        for _ in range(count):
            rain_img = Image.open(random.choice(rain_paths)).convert("RGBA")
            scale = random.uniform(0.1, 0.3)
            slime = rain_img.resize((int(rain_img.width * scale), int(rain_img.height * scale)))
            slime = stretch_slime(slime, scale_y=random.uniform(1.3, 2.0))
            slime = apply_alpha_gradient(slime)
            x = random.randint(0, canvas_size[0])
            y = random.randint(0, canvas_size[1] // 2)
            angle = rotate_toward_center(x, y, canvas_w//2, canvas_h//2)
            rotated = slime.rotate(angle, expand=True)
            canvas.paste(rotated, (x, y), rotated)
        return canvas

    rain_layer = generate_rain(character_img.size, count=40)
    final_img = Image.alpha_composite(character_img, rain_layer)

    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
