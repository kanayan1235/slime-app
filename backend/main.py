from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from PIL import Image
import os
import uuid

app = FastAPI()

from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="static", html=True), name="static")

UPLOAD_FOLDER = "backend/uploads"
KEFIR_FOLDER = "backend/kefirs"
OUTPUT_FOLDER = "backend/outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(KEFIR_FOLDER, exist_ok=True)

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # 一意なファイル名に変換して保存
    ext = os.path.splitext(file.filename)[-1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    upload_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(upload_path, "wb") as buffer:
        buffer.write(await file.read())

    # 画像を開く
    base_img = Image.open(upload_path).convert("RGBA")

    # kefir画像の1枚をランダム選択
    kefir_files = [f for f in os.listdir(KEFIR_FOLDER) if f.lower().endswith((".png", ".jpg"))]
    if not kefir_files:
        return {"error": "ケフィア画像がありません"}

    import random
    kefir_path = os.path.join(KEFIR_FOLDER, random.choice(kefir_files))
    kefir_img = Image.open(kefir_path).convert("RGBA")

    # スライム画像をベース画像に合成（中央に配置）
    base_w, base_h = base_img.size
    kefir_w, kefir_h = kefir_img.size
    pos = ((base_w - kefir_w) // 2, (base_h - kefir_h) // 2)
    base_img.paste(kefir_img, pos, kefir_img)

    # 保存
    output_path = os.path.join(OUTPUT_FOLDER, f"output_{unique_filename}")
    base_img.save(output_path)

    return FileResponse(output_path)
