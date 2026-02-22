import os
import time
import base64
import requests
from runwayml import RunwayML
from moviepy import ImageClip
from src.models import VideoScript
from config import WORKSPACE_DIR

def _get_base64_data_uri(file_path: str) -> str:
    """Convertit un fichier local en Base64 Data URI."""
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded_string}"

def _generate_with_moviepy(image_path: str, output_path: str, duration: int = 5):
    """Génère une vidéo statique de secours via MoviePy v2."""
    try:
        clip = ImageClip(image_path)
        clip = clip.with_duration(duration)
        clip.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            preset="ultrafast", 
            logger=None
        )
        clip.close()
    except Exception as e:
        raise RuntimeError(f"Erreur d'exportation MoviePy : {e}")

def _generate_with_runway(image_path: str, prompt: str, output_path: str, client: RunwayML):
    """Génère une vidéo animée via l'API RunwayML."""
    prompt_image_uri = _get_base64_data_uri(image_path)
    
    task = client.image_to_video.create(
        model="gen3a_turbo",
        prompt_image=prompt_image_uri,
        prompt_text=prompt
    )
    
    print(f"Tâche Runway envoyée (ID: {task.id}). En attente du rendu...")
    
    while task.status not in ["SUCCEEDED", "FAILED", "CANCELLED"]:
        time.sleep(10)
        task = client.tasks.retrieve(task.id)
        print(f"Statut Runway : {task.status}")
        
    if task.status == "SUCCEEDED":
        video_url = task.output[0]
        response = requests.get(video_url)
        with open(output_path, 'wb') as f:
            f.write(response.content)
    else:
        raise RuntimeError(f"Échec de la génération Runway. Statut final : {task.status}")

def generate_videos(script: VideoScript, project_id: str, api_choice: str = "moviepy") -> VideoScript:
    """
    Point d'entrée modulaire pour la génération de vidéos.
    Supporte 'moviepy' ou 'runway'.
    """
    print(f"Génération des vidéos en cours (Moteur : {api_choice}) pour le projet '{project_id}'...")

    videos_dir = WORKSPACE_DIR / project_id / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    # Initialisation conditionnelle du client
    runway_client = None
    if api_choice == "runway":
        runway_client = RunwayML()

    for scene in script.scenes:
        if not scene.image_path or not os.path.exists(scene.image_path):
            print(f"Image introuvable pour la scène {scene.id}. Ignorée.")
            continue
            
        output_path = str(videos_dir / f"scene_{scene.id}.mp4")
        scene.video_path = output_path
        
        print(f"Traitement de la scène {scene.id}/{len(script.scenes)}...")
        
        try:
            if api_choice == "moviepy":
                _generate_with_moviepy(scene.image_path, output_path)
            elif api_choice == "runway":
                _generate_with_runway(scene.image_path, scene.visual_prompt, output_path, runway_client)
            else:
                raise ValueError(f"Moteur de rendu '{api_choice}' non reconnu.")
                
        except Exception as e:
            print(f"Erreur lors du traitement de la scène {scene.id}: {e}")

    print("Génération des vidéos terminée.")
    return script

if __name__ == "__main__":
    from src.generators.script_gen import generate_script
    from src.generators.image_gen import generate_images
    
    test_theme = "La Pissodynamique quantique"
    
    script_obj = generate_script(test_theme)
    script_obj.scenes = script_obj.scenes[:1]
    
    script_obj = generate_images(script_obj, project_id="test_modulaire", api_choice="dummy")
    
    # Test avec MoviePy (par défaut)
    script_obj = generate_videos(script_obj, project_id="test_modulaire", api_choice="moviepy")