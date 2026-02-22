import argparse
import time
import os
from src.models import PipelineConfig
from src.generators.script_gen import generate_script
from src.generators.voice_gen import generate_voices
from src.generators.image_gen import generate_images
from src.generators.video_gen import generate_videos
from src.generators.music_gen import generate_music
from src.editors.video_editor import assemble_video
from src.editors.subtitle_editor import apply_subtitles
from config import WORKSPACE_DIR

def get_next_project_id(base_name="projet"):
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    existing_dirs = [d for d in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, d)) and d.startswith(base_name)]
    
    max_num = 0
    for d in existing_dirs:
        try:
            num = int(d.split('_')[-1])
            if num > max_num:
                max_num = num
        except ValueError:
            continue
            
    return f"{base_name}_{max_num + 1}"

def main():
    parser = argparse.ArgumentParser(
        description="Pipeline automatisée de génération de vidéos par IA."
    )
    
    parser.add_argument(
        "theme", 
        type=str, 
        help="Le thème principal de la vidéo (entre guillemets)."
    )
    
    parser.add_argument(
        "--project-id", 
        type=str, 
        default=None, 
        help="Identifiant du projet. Si omis, un numéro incrémenté sera généré."
    )
    parser.add_argument(
        "--num-scenes", 
        type=int, 
        default=12, 
        help="Nombre de scènes (et d'images) à générer pour la vidéo."
    )
    parser.add_argument(
        "--duration", 
        type=int, 
        default=20, 
        help="Durée cible de la vidéo en secondes."
    )
    parser.add_argument(
        "--angle", 
        type=str, 
        default=None, 
        help="Angle spécifique, ton ou instructions additionnelles pour orienter le script."
    )
    parser.add_argument(
        "--script-engine", 
        type=str, 
        default="gemini", 
        choices=["gemini"], 
        help="Moteur de génération de texte."
    )
    parser.add_argument(
        "--voice-engine", 
        type=str, 
        default="edge_tts", 
        choices=["edge_tts"], 
        help="Moteur de synthèse vocale."
    )
    parser.add_argument(
        "--image-engine", 
        type=str, 
        default="dummy", 
        choices=["dummy", "fal"], 
        help="Moteur de génération d'images."
    )
    parser.add_argument(
        "--video-engine", 
        type=str, 
        default="moviepy", 
        choices=["moviepy", "runway"], 
        help="Moteur d'animation vidéo."
    )
    parser.add_argument(
        "--music-engine", 
        type=str, 
        default="dummy", 
        choices=["dummy", "local", "replicate"], 
        help="Moteur de génération musicale."
    )

    args = parser.parse_args()
    
    project_id = args.project_id if args.project_id else get_next_project_id()
    
    config = PipelineConfig(
        script_engine=args.script_engine,
        voice_engine=args.voice_engine,
        image_engine=args.image_engine,
        video_engine=args.video_engine,
        music_engine=args.music_engine,
        num_scenes=args.num_scenes,
        target_duration=args.duration,
        angle=args.angle
    )
    
    print("-" * 50)
    print(f"Lancement de la production : {project_id}")
    print(f"Thème ciblé : {args.theme}")
    print("Configuration active :")
    for key, value in config.model_dump().items():
        print(f"  - {key}: {value}")
    print("-" * 50)
    
    try:
        script_obj = generate_script(
            theme=args.theme, 
            num_scenes=args.num_scenes, 
            target_duration=args.duration,
            angle=args.angle
        )
        script_obj.config = config
        
        script_obj = generate_voices(script_obj, project_id)
        script_obj = generate_images(script_obj, project_id)
        script_obj = generate_videos(script_obj, project_id)
        script_obj = generate_music(script_obj, project_id)
        
        assemble_video(script_obj, project_id)
        apply_subtitles(script_obj, project_id)
        
        print(f"Production terminée. Fichiers disponibles dans workspace/{project_id}/")
        
    except Exception as e:
        print(f"Arrêt critique de la pipeline : {e}")

if __name__ == "__main__":
    main()