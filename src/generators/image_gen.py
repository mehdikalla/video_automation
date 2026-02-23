import json
import argparse
import sys
import requests
import urllib.request
import urllib.parse
import time
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import fal_client

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
import config

# --- Configuration ComfyUI ---
COMFYUI_SERVER = "127.0.0.1:8188"
PROMPT_NODE_ID = "6"
SEED_NODE_ID = "3"

# --- Moteurs de génération ---

def _generate_with_fal(prompt: str, output_path: Path, lora_path: str = None, lora_scale: float = 1.0):
    arguments = {
        "prompt": prompt, 
        "image_size": "portrait_16_9",
        "num_inference_steps": 28,
        "guidance_scale": 3.5
    }
    
    if lora_path:
        arguments["loras"] = [{
            "path": lora_path,
            "scale": lora_scale
        }]

    handler = fal_client.submit(
        "fal-ai/flux/dev",
        arguments=arguments
    )
    result = handler.get()
    image_url = result['images'][0]['url']
    img_data = requests.get(image_url).content
    with open(output_path, 'wb') as f:
        f.write(img_data)

def _generate_with_comfy(prompt: str, output_path: Path, workflow_path: Path):
    if not workflow_path.exists():
        raise FileNotFoundError(f"Le fichier de template ComfyUI {workflow_path} est introuvable.")

    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)

    if PROMPT_NODE_ID in workflow:
        workflow[PROMPT_NODE_ID]["inputs"]["text"] = prompt
    else:
        raise KeyError(f"Le nœud de prompt ({PROMPT_NODE_ID}) est introuvable dans le workflow_api.json.")

    if SEED_NODE_ID in workflow and "seed" in workflow[SEED_NODE_ID]["inputs"]:
        workflow[SEED_NODE_ID]["inputs"]["seed"] = int(time.time() * 1000) % 10000000000

    def queue_prompt(prompt_workflow):
        p = {"prompt": prompt_workflow}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{COMFYUI_SERVER}/prompt", data=data)
        response = urllib.request.urlopen(req)
        return json.loads(response.read())

    def get_history(prompt_id):
        req = urllib.request.Request(f"http://{COMFYUI_SERVER}/history/{prompt_id}")
        response = urllib.request.urlopen(req)
        return json.loads(response.read())

    def get_image(filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        req = urllib.request.Request(f"http://{COMFYUI_SERVER}/view?{url_values}")
        response = urllib.request.urlopen(req)
        return response.read()

    try:
        prompt_response = queue_prompt(workflow)
        prompt_id = prompt_response.get("prompt_id")
    except Exception as e:
        raise RuntimeError(f"Impossible de se connecter à ComfyUI ({COMFYUI_SERVER}). Erreur : {e}")
    
    while True:
        history = get_history(prompt_id)
        if prompt_id in history:
            break
        time.sleep(2)
        
    history_data = history[prompt_id]
    image_data = None
    for node_id, node_output in history_data.get("outputs", {}).items():
        if "images" in node_output and len(node_output["images"]) > 0:
            image_info = node_output["images"][0]
            image_data = get_image(image_info["filename"], image_info["subfolder"], image_info["type"])
            break
            
    if not image_data:
        raise RuntimeError("Aucune image n'a été retournée par ComfyUI.")

    with open(output_path, "wb") as f:
        f.write(image_data)

def _generate_dummy_image(prompt: str, output_path: Path):
    img = Image.new('RGB', (768, 1344), color="#2C3E50")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=40)
    except TypeError:
        font = ImageFont.load_default()
    wrapped_text = textwrap.fill(prompt, width=30)
    draw.text((50, 600), wrapped_text, fill=(255, 255, 255), font=font)
    img.save(output_path)

# --- Orchestrateur du module ---

def generate_images(input_json_path: str, engine: str = "fal", workflow_path_str: str = "workflow_api.json", lora_path: str = None, lora_scale: float = 1.0):
    print(f"Démarrage du Module 3 (Moteur: {engine}) à partir de : {input_json_path}")
    if lora_path:
        print(f"Injection du modèle LoRA : {lora_path} (Poids: {lora_scale})")
    
    input_path = Path(input_json_path)
    workflow_path = Path(workflow_path_str)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Le fichier {input_json_path} est introuvable.")

    with open(input_path, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    project_dir = input_path.parent
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    generated_images = []

    for scene in script_data.get("scenes", []):
        scene_id = scene.get("id")
        visual_prompt = scene.get("visual_prompt", "")
        
        if not visual_prompt:
            continue

        output_file = images_dir / f"scene_{scene_id}.jpg"
        print(f"Génération de la scène {scene_id} via {engine}...")
        
        try:
            if engine == "fal":
                _generate_with_fal(visual_prompt, output_file, lora_path, lora_scale)
            elif engine == "comfyui":
                _generate_with_comfy(visual_prompt, output_file, workflow_path)
            elif engine == "dummy":
                _generate_dummy_image(visual_prompt, output_file)
            else:
                raise ValueError(f"Moteur non reconnu : {engine}")
                
            generated_images.append({
                "scene_id": scene_id,
                "image_path": str(output_file.resolve())
            })
            
        except Exception as e:
            raise RuntimeError(f"Erreur lors de la génération pour la scène {scene_id} : {e}")

    for scene in script_data.get("scenes", []):
        for img_data in generated_images:
            if scene["id"] == img_data["scene_id"]:
                scene["image_path"] = img_data["image_path"]

    updated_json_path = project_dir / "script_with_images.json"
    with open(updated_json_path, 'w', encoding='utf-8') as f:
        json.dump(script_data, f, indent=4, ensure_ascii=False)

    result = {
        "status": "success",
        "engine_used": engine,
        "images_count": len(generated_images),
        "updated_script": str(updated_json_path.resolve())
    }
    
    print("\n--- OUTPUT JSON POUR N8N ---")
    print(json.dumps(result))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 3 : Génération d'images fixes (Multi-moteurs avec support LoRA)")
    parser.add_argument("--input-json", type=str, required=True, help="Chemin vers le fichier script.json")
    parser.add_argument("--engine", type=str, choices=["fal", "comfyui", "dummy"], default="fal", help="Moteur de génération à utiliser")
    parser.add_argument("--workflow", type=str, default="workflow_api.json", help="Chemin vers workflow_api.json (ComfyUI)")
    parser.add_argument("--lora-path", type=str, default=None, help="URL du modèle LoRA (.safetensors)")
    parser.add_argument("--lora-scale", type=float, default=1.0, help="Poids du modèle LoRA (défaut: 1.0)")
    
    args = parser.parse_args()
    
    try:
        generate_images(args.input_json, args.engine, args.workflow, args.lora_path, args.lora_scale)
    except Exception as e:
        print(f"Erreur critique dans le module 3 : {e}", file=sys.stderr)
        sys.exit(1)