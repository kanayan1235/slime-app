from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from PIL import Image
import io

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <h1>Slime Rain App</h1>
    <form action="/upload" enctype="multipart/form-data" method="post">
        <input name="file" type="file">
        <input type="submit">
    </form>
    """

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    img = Image.open(io.BytesIO(contents))
    img = img.convert("L")  # グレースケール変換（仮処理）
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"message": "画像を受け取りました", "filename": file.filename}
