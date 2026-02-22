import os
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont
import fal_client
from src.models import VideoScript
from config import WORKSPACE_DIR

def _generate_dummy_image(prompt: str, output_path: str):
    """Générateur local de secours."""
    img = Image.new('RGB', (1024, 1792), color="#2C3E50")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=40)
    except TypeError:
        font = ImageFont.load_default()
    wrapped_text = textwrap.fill(prompt, width=30)
    draw.text((50, 800), wrapped_text, fill=(255, 255, 255), font=font)
    img.save(output_path)

def _generate_with_fal(prompt: str, output_path: str):
    """Génère une image via FLUX.1 (Fal.ai)."""
    handler = fal_client.submit(
        "fal-ai/flux/dev",
        arguments={"prompt": prompt, "image_size": "portrait_16_9"}
    )
    img_data = requests.get(handler.get()['images'][0]['url']).content
    with open(output_path, 'wb') as f:
        f.write(img_data)

# Le Registre des API : Facilite l'ajout d'une nouvelle API comme DALL-E ou Midjourney
IMAGE_ENGINES = {
    "dummy": _generate_dummy_image,
    "fal": _generate_with_fal,
}

def generate_images(script: VideoScript, project_id: str) -> VideoScript:
    """Aiguilleur principal utilisant le registre."""
    engine_name = script.config.image_engine
    engine_func = IMAGE_ENGINES.get(engine_name)
    
    if not engine_func:
        raise ValueError(f"Moteur d'image '{engine_name}' non reconnu dans le registre.")

    print(f"Génération des images (Moteur: {engine_name}) pour '{project_id}'...")

    images_dir = WORKSPACE_DIR / project_id / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for scene in script.scenes:
        file_path = str(images_dir / f"scene_{scene.id}.jpg")
        scene.image_path = file_path 
        
        print(f"Traitement de la scène {scene.id}...")
        try:
            # Exécution dynamique de la fonction correspondante
            engine_func(scene.visual_prompt, file_path)
        except Exception as e:
            print(f"Erreur scène {scene.id}: {e}")

    return script