import json
import argparse
import sys
import os
import subprocess
from pathlib import Path

def format_time_ass(seconds: float) -> str:
    """Convertit des secondes en format temporel ASS (H:MM:SS.cs)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def generate_ass_subtitles(timestamps_path: Path, output_ass_path: Path):
    """Génère un fichier de sous-titres stylisé à partir des données de Whisper."""
    if not timestamps_path.exists():
        raise FileNotFoundError(f"Fichier d'horodatage introuvable : {timestamps_path}")

    with open(timestamps_path, 'r', encoding='utf-8') as f:
        words_data = json.load(f)

    # En-tête ASS : Définit la résolution 9:16 et un style de sous-titre "Shorts" (Gros, Jaune, Contour noir)
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 768
PlayResY: 1344

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ShortsStyle,Arial,75,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,5,10,10,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(output_ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_header)
        
        # Regroupement des mots (Chunking) : on affiche 2 à 3 mots par écran pour un rythme dynamique
        chunk = []
        for idx, word_info in enumerate(words_data):
            chunk.append(word_info)
            # On coupe si le chunk atteint 3 mots, ou si c'est le dernier mot, ou s'il y a un grand silence
            if len(chunk) == 3 or idx == len(words_data) - 1:
                start_time = format_time_ass(chunk[0]['start'])
                end_time = format_time_ass(chunk[-1]['end'])
                text = " ".join([w['word'] for w in chunk]).strip()
                
                # Écriture de la ligne de dialogue
                f.write(f"Dialogue: 0,{start_time},{end_time},ShortsStyle,,0,0,0,,{text}\n")
                chunk = []

    print(f"Sous-titres dynamiques générés : {output_ass_path}")

def assemble_final_video(input_json_path: str):
    print(f"Démarrage du Module 5 (Montage Final) à partir de : {input_json_path}")
    
    # AJOUT DE .resolve() ICI pour forcer le chemin absolu
    input_path = Path(input_json_path).resolve() 
    
    if not input_path.exists():
        raise FileNotFoundError(f"Le fichier {input_json_path} est introuvable.")

    with open(input_path, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    project_dir = input_path.parent
    audio_path = project_dir / "audio" / "voiceover.mp3"
    timestamps_path = project_dir / "audio" / "timestamps.json"
    
    if not audio_path.exists():
        raise FileNotFoundError("La piste vocale globale (voiceover.mp3) est introuvable.")
        
    # 1. Génération des sous-titres
    ass_path = project_dir / "subtitles.ass"
    generate_ass_subtitles(timestamps_path, ass_path)

    # 2. Préparation du fichier de concaténation pour FFmpeg
    concat_list_path = project_dir / "concat.txt"
    valid_videos = []
    
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for scene in script_data.get("scenes", []):
            video_str = scene.get("video_path")
            if video_str and Path(video_str).exists():
                # On écrit le chemin relatif depuis le dossier du projet pour éviter les bugs de caractères Windows/Linux
                rel_path = Path(video_str).relative_to(project_dir)
                f.write(f"file '{rel_path}'\n")
                valid_videos.append(video_str)

    if not valid_videos:
        raise RuntimeError("Aucune vidéo valide n'a été trouvée pour l'assemblage.")

    output_final_path = project_dir / "FINAL_VIDEO.mp4"

    print("Mixage et incrustation via FFmpeg en cours...")
    
    try:
        # Exécution dans le dossier du projet pour faciliter les chemins relatifs des filtres
        command = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", "concat.txt",  # Flux vidéo (liste des clips)
            "-i", "audio/voiceover.mp3",                       # Flux audio global
            "-vf", "ass=subtitles.ass",                        # Incrustation physique des sous-titres
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",                                       # Coupe la vidéo quand l'audio se termine
            "FINAL_VIDEO.mp4"
        ]
        
        process = subprocess.run(command, cwd=str(project_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if process.returncode != 0:
            raise RuntimeError(f"Erreur FFmpeg :\n{process.stderr}")
            
    except Exception as e:
        raise RuntimeError(f"Échec de l'assemblage final : {e}")
        
    # Nettoyage du fichier de concaténation
    if concat_list_path.exists():
        concat_list_path.unlink()

    # Sortie formatée pour l'orchestrateur (n8n)
    result = {
        "status": "success",
        "final_video": str(output_final_path.resolve())
    }
    
    print("\n--- OUTPUT JSON POUR N8N ---")
    print(json.dumps(result))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 5 : Rendu Final (Assemblage & Sous-titres)")
    parser.add_argument("--input-json", type=str, required=True, help="Chemin vers le fichier script_with_videos.json")
    
    args = parser.parse_args()
    
    try:
        assemble_final_video(args.input_json)
    except Exception as e:
        print(f"Erreur critique dans le module 5 : {e}", file=sys.stderr)
        sys.exit(1)