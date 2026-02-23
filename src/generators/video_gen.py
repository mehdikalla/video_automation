import json
import argparse
import sys
import subprocess
from pathlib import Path

def generate_videos_kenburns(input_json_path: str, duration: int = 4):
    print(f"Démarrage du Module 4 (Animation 2.5D via FFmpeg) à partir de : {input_json_path}")
    
    input_path = Path(input_json_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Le fichier {input_json_path} est introuvable.")

    with open(input_path, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    project_dir = input_path.parent
    videos_dir = project_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    generated_videos = []

    for scene in script_data.get("scenes", []):
        scene_id = scene.get("id")
        image_path_str = scene.get("image_path")
        
        if not image_path_str:
            print(f"Avertissement : Aucune image pour la scène {scene_id}. Ignorée.")
            continue

        image_path = Path(image_path_str)
        if not image_path.exists():
            continue

        output_video_path = videos_dir / f"scene_{scene_id}.mp4"
        print(f"Génération de l'animation (Zoom in) pour la scène {scene_id}...")
        
        # Calcul du nombre de frames (24 fps * durée)
        frames = duration * 24
        
        try:
            # Commande FFmpeg pure CPU pour un effet Ken Burns fluide
            command = [
                "ffmpeg", "-y", "-loop", "1",
                "-i", str(image_path.resolve()),
                "-vf", f"zoompan=z='min(zoom+0.0015,1.5)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=768x1344",
                "-c:v", "libx264",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                str(output_video_path.resolve())
            ]
            
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if not output_video_path.exists() or process.returncode != 0:
                raise RuntimeError(f"Échec FFmpeg :\n{process.stderr}")
                
            generated_videos.append({
                "scene_id": scene_id,
                "video_path": str(output_video_path.resolve())
            })
            print(f"Vidéo {scene_id} générée avec succès : {output_video_path}")
            
        except Exception as e:
            raise RuntimeError(f"Erreur lors de l'animation de la scène {scene_id} : {e}")

    for scene in script_data.get("scenes", []):
        for vid_data in generated_videos:
            if scene["id"] == vid_data["scene_id"]:
                scene["video_path"] = vid_data["video_path"]

    updated_json_path = project_dir / "script_with_videos.json"
    with open(updated_json_path, 'w', encoding='utf-8') as f:
        json.dump(script_data, f, indent=4, ensure_ascii=False)

    result = {
        "status": "success",
        "videos_count": len(generated_videos),
        "updated_script": str(updated_json_path.resolve())
    }
    
    print("\n--- OUTPUT JSON POUR N8N ---")
    print(json.dumps(result))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 4 : Animation 2.5D via FFmpeg")
    parser.add_argument("--input-json", type=str, required=True, help="Chemin vers le fichier script_with_images.json")
    parser.add_argument("--duration", type=int, default=4, help="Durée de chaque clip animé en secondes")
    
    args = parser.parse_args()
    
    try:
        generate_videos_kenburns(args.input_json, args.duration)
    except Exception as e:
        print(f"Erreur critique dans le module 4 : {e}", file=sys.stderr)
        sys.exit(1)