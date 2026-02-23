import json
import time
import argparse
import sys
import os
from pathlib import Path
from google import genai

# Ajout du chemin racine au système pour permettre l'exécution autonome du script
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import WORKSPACE_DIR
from src.models import VideoScript

def generate_script(theme: str, project_id: str = "default_project", num_scenes: int = 12, target_duration: int = 20, angle: str = None) -> VideoScript:
    print(f"Génération du script narratif continu pour : '{theme}' (Projet: {project_id})...")
    
    max_words = int(target_duration * 2.5)
    client = genai.Client()
    
    angle_instruction = ""
    if angle:
        angle_instruction = f"\nDIRECTIVE SPÉCIFIQUE (ANGLE / TON) :\n{angle}\nApplique strictement cette ligne directrice dans la narration."
    
    prompt = f"""
    Tu es un scénariste expert en documentaires courts.
    Génère un script sur le thème : "{theme}".
    {angle_instruction}
    
    DIRECTIVES DE CONTENU (SANS FILTRE) :
    Tu es autorisé et encouragé à aborder des idées controversées, non censurées, ou politiquement incorrectes si le thème ou l'angle le demande. Adopte le ton requis sans appliquer de lissage moralisateur ou de précautions oratoires.

    NOUVELLE STRUCTURE (DÉCOUPLAGE AUDIO/VIDÉO) :
    1. Rédige l'intégralité du texte de la vidéo dans le champ "full_voiceover_text".
    2. Ce texte DOIT être un seul paragraphe continu, avec des phrases naturelles et fluides. Ne hache pas le texte.
    3. La longueur totale du texte (hook + full_voiceover_text) doit avoisiner {max_words} mots pour durer {target_duration} secondes.
    4. Indépendamment du texte, fournis EXACTEMENT {num_scenes} descriptions visuelles dans le tableau "scenes". Ces images illustreront le texte global.
    
    Le format de sortie doit être un JSON strictement valide correspondant à cette structure :
    {{
        "theme": "Le thème",
        "hook": "La phrase d'accroche captivante.",
        "full_voiceover_text": "L'intégralité de la narration en un seul bloc fluide et continu, faisant suite à l'accroche...",
        "scenes": [
            {{
                "id": 1,
                "visual_prompt": "Description visuelle de la première image."
            }}
        ]
    }}
    """
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    ]
    
    max_retries = 3
    retry_delay = 15
    response = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "safety_settings": safety_settings
                }
            )
            break
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print(f"Limite de quota API atteinte (Tentative {attempt + 1}/{max_retries}). Pause de {retry_delay} secondes...")
                time.sleep(retry_delay)
                if attempt == max_retries - 1:
                    raise RuntimeError("Échec définitif : Limites de quota API dépassées après plusieurs tentatives.")
            else:
                raise e
    
    try:
        script_data = json.loads(response.text)
        
        # Sauvegarde physique du JSON (Architecture n8n / Modulaire)
        project_dir = WORKSPACE_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "script.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=4, ensure_ascii=False)
            
        print(f"Script JSON sauvegardé avec succès : {output_path}")
        
        # Retourne l'objet pour maintenir la compatibilité avec l'ancien main.py
        script_obj = VideoScript(**script_data)
        return script_obj
        
    except Exception as e:
        raise RuntimeError(f"Erreur de génération : {e}\nRéponse : {response.text if response else 'Aucune réponse'}")

# --- Point d'entrée pour l'exécution modulaire (CLI) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 1 : Scénarisation et Structuration (Gemini)")
    parser.add_argument("--theme", type=str, required=True, help="Le thème principal de la vidéo")
    parser.add_argument("--project-id", type=str, required=True, help="L'identifiant du projet (ex: projet_n8n_01)")
    parser.add_argument("--num-scenes", type=int, default=12, help="Nombre de scènes à générer")
    parser.add_argument("--duration", type=int, default=20, help="Durée cible en secondes")
    parser.add_argument("--angle", type=str, default=None, help="Angle spécifique ou consigne de ton")
    
    args = parser.parse_args()
    
    try:
        generate_script(
            theme=args.theme,
            project_id=args.project_id,
            num_scenes=args.num_scenes,
            target_duration=args.duration,
            angle=args.angle
        )
    except Exception as e:
        print(f"Erreur d'exécution du module : {e}")
        sys.exit(1)