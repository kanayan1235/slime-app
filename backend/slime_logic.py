
from PIL import Image, ImageEnhance

def process_image(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    # 仮処理（輝度アップ）
    enhancer = ImageEnhance.Brightness(img)
    result = enhancer.enhance(1.2)
    result.save(output_path)
