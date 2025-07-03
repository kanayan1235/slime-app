わfrom fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import os, random, uuid
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 静的ファイル（frontend）のマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# `/` にアクセスしたら index.html を返す
@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# アップロード処理（例）
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    contents = await file.read()
    with open(f"uploaded_{file.filename}", "wb") as f:
        f.write(contents)
    return FileResponse(f"uploaded_{file.filename})"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "backend/uploaded"
RESULT_FOLDER = "backend/results"
KEFIR_FOLDER = "backend/kefirs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    img = Image.open(file.file).convert("RGBA")
    img = img.resize((512, 512))

    rain_files = [f for f in os.listdir(KEFIR_FOLDER) if f.lower().endswith((".png"))]
    if not rain_files:
        return {"error": "雨画像が見つかりません"}

    rain_path = os.path.join(KEFIR_FOLDER, random.choice(rain_files))
    rain = Image.open(rain_path).convert("RGBA")
    rain = rain.resize((512, 512))

    combined = Image.alpha_composite(img, rain)

    out_path = os.path.join(RESULT_FOLDER, f"{uuid.uuid4().hex}.png")
    combined.save(out_path)

 return FileResponse(f"uploaded_{file.filename}")
