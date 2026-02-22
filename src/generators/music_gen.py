import os
import shutil
import json
from google import genai
from moviepy import AudioClip
from src.models import VideoScript
from config import WORKSPACE_DIR, BASE_DIR

MUSIC_ASSETS_DIR = BASE_DIR / "assets" / "music"

def _generate_dummy_music(script: VideoScript, output_path: str):
    """Génère une piste audio silencieuse de secours."""
    def make_frame(t):
        return [0, 0]
    
    clip = AudioClip(make_frame, duration=2, fps=44100)
    clip.write_audiofile(output_path, logger=None)
    clip.close()

def _select_local_music(script: VideoScript, output_path: str):
    """Sélectionne la meilleure piste locale via Gemini selon le thème."""
    MUSIC_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    catalog_path = MUSIC_ASSETS_DIR / "catalog.json"
    
    if not catalog_path.exists():
        print("Alerte : Fichier catalog.json introuvable. Création d'un catalogue de secours.")
        catalog = {"dummy.mp3": "Musique par défaut"}
        _generate_dummy_music(script, str(MUSIC_ASSETS_DIR / "dummy.mp3"))
    else:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

    client = genai.Client()
    
    prompt = (
        f"Tu es un superviseur musical. Le thème de la vidéo est : '{script.theme}'.\n"
        f"L'accroche vocale est : '{script.hook}'.\n\n"
        "Voici le catalogue des musiques disponibles avec leur description :\n"
        f"{json.dumps(catalog, ensure_ascii=False, indent=2)}\n\n"
        "Réponds UNIQUEMENT par le nom exact du fichier .mp3 qui correspond le mieux. "
        "N'ajoute aucune autre phrase ou ponctuation."
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    selected_file = response.text.strip()
    
    if selected_file not in catalog:
        print(f"Alerte : Nom de fichier invalide renvoyé par l'IA ({selected_file}). Sélection par défaut appliquée.")
        selected_file = list(catalog.keys())[0]
        
    print(f"Piste musicale sélectionnée par l'IA : {selected_file}")
    
    source_path = MUSIC_ASSETS_DIR / selected_file
    
    if source_path.exists():
        shutil.copy2(source_path, output_path)
    else:
        print(f"Alerte : Le fichier {selected_file} n'existe pas sur le disque. Utilisation d'un fichier silencieux.")
        _generate_dummy_music(script, output_path)

# Registre des API musicales
MUSIC_ENGINES = {
    "dummy": _generate_dummy_music,
    "local": _select_local_music
}

def generate_music(script: VideoScript, project_id: str) -> VideoScript:
    """Aiguilleur principal utilisant le registre pour la musique."""
    engine_name = script.config.music_engine
    engine_func = MUSIC_ENGINES.get(engine_name)
    
    if not engine_func:
        raise ValueError(f"Moteur musical '{engine_name}' non reconnu dans le registre.")

    print(f"Génération de la musique (Moteur: {engine_name}) pour '{project_id}'...")

    audio_dir = WORKSPACE_DIR / project_id / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    output_path = str(audio_dir / "background_music.mp3")
    script.bg_music_path = output_path

    try:
        engine_func(script, output_path)
    except Exception as e:
        print(f"Erreur lors du traitement musical : {e}")

    return script