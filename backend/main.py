from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw
import io

app = FastAPI()
from fastapi.responses import FileResponse

@app.get("/")
def index():
    return FileResponse("static/index.html")
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    image = Image.open(file.file).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.ellipse((50, 50, 150, 150), fill=(0, 255, 0, 128))  # 仮スライム合成

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")
