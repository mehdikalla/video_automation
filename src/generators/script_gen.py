import json
from google import genai
from src.models import VideoScript

def generate_script(theme: str, num_scenes: int = 12, target_duration: int = 20, angle: str = None) -> VideoScript:
    print(f"Génération du script narratif continu pour : '{theme}'...")
    
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
    2. Ce texte DOIT être un seul paragraphe continu, avec des phrases longues, naturelles et fluides. Ne hache pas le texte.
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
    
    # Désactivation des filtres de sécurité pour permettre la génération de textes controversés
    safety_settings = [
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    ]
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "safety_settings": safety_settings
        }
    )
    
    try:
        script_data = json.loads(response.text)
        script_obj = VideoScript(**script_data)
        print("Script narratif continu généré avec succès.")
        return script_obj
    except Exception as e:
        raise RuntimeError(f"Erreur de génération : {e}\nRéponse : {response.text}")