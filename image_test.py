"""Prueba local del post de imagen: guion -> fondo IA -> render. No sube ni publica."""
import os
from src import image_script, image_gen, image_render

os.makedirs("build", exist_ok=True)

if os.environ.get("GEMINI_API_KEY"):
    data = image_script.generate_image_post(os.environ.get("NICHE", "tecnología y finanzas"))
else:
    # Sin API key: datos de ejemplo para probar SOLO el render (cero costo)
    data = {"big": "70%", "small": "no revisa sus cobros",
            "image_prompt": "cinematic dark blue finance background, abstract charts and coins"}

print("big:", data.get("big"), "| small:", data.get("small"))
print("caption:", data.get("caption", "(sin caption en modo ejemplo)"))

bg = image_gen.fetch_background(data.get("image_prompt", ""), "build/bg.png")
image_render.render_image(data.get("big", ""), data.get("small", ""), "build/post.jpg", bg_path=bg)
print("\nListo -> abre build\\post.jpg")