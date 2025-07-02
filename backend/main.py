from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from PIL import Image
import numpy as np
import io, os, random

app = FastAPI()

UPLOAD_DIR = "backend/uploads"
SLIME_DIR = "backend/kefirs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SLIME_DIR, exist_ok=True)

def compose_images(person_img: Image.Image, slime_img: Image.Image) -> Image.Image:
    person = person_img.convert("RGBA").resize((512, 512))
    slime = slime_img.convert("RGBA").resize((512, 512))
    return Image.alpha_composite(person, slime)

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    content = await file.read()
    img = Image.open(io.BytesIO(content)).convert("RGBA")
    with open(os.path.join(UPLOAD_DIR, file.filename), "wb") as f:
        f.write(content)

    slime_files = [f for f in os.listdir(SLIME_DIR) if f.endswith(('.png', '.jpg'))]
    slime_img = Image.open(os.path.join(SLIME_DIR, random.choice(slime_files)))
    composed = compose_images(img, slime_img)

    output = io.BytesIO()
    composed.save(output, format="PNG")
    output.seek(0)
    return StreamingResponse(output, media_type="image/png")
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="frontend", html=True), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("frontend/index.html", encoding="utf-8") as f:
        return f.read()
