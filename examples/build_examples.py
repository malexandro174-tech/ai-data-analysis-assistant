from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

root = Path(__file__).parent
pd.DataFrame([
    {"campaign": "Search", "budget": 820, "leads": 218, "conversion_rate": 0.042},
    {"campaign": "Social", "budget": 640, "leads": 161, "conversion_rate": 0.036},
    {"campaign": "Partner", "budget": 530, "leads": 133, "conversion_rate": 0.039},
]).to_excel(root / "sample_marketing.xlsx", index=False)
for suffix, color in (("png", "#7c3aed"), ("jpeg", "#0f766e")):
    image = Image.new("RGB", (720, 400), "#101827")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((85, 80, 635, 315), radius=22, fill=color)
    draw.text((180, 180), "Sample business chart", fill="white")
    image.save(root / f"sample_chart.{suffix}")
