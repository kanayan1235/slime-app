from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import numpy as np
import random
import os

app = FastAPI()

# 静的ファイルを /static で提供（frontend/index.html など）
app.mount("/static", StaticFiles(directory="frontend", html=True), name="static")

# トップページで index.html を返す
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("frontend/index.html", encoding="utf-8") as f:
        return f.read()

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # スライム画像をランダムに選択
    slime_folder = "kefirs"
    slime_files = [f for f in os.listdir(slime_folder) if f.endswith((".png", ".jpg"))]
    if not slime_files:
        return {"error": "No slime images found."}
    slime_path = os.path.join(slime_folder, random.choice(slime_files))

    person = Image.open(file_path).convert("RGBA")
    slime = Image.open(slime_path).convert("RGBA")
    slime = slime.resize(person.size)

    combined = Image.alpha_composite(person, slime)
    result_path = "uploads/result.png"
    combined.save(result_path)

    return FileResponse(result_path, media_type="image/png")
