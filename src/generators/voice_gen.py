import os
import asyncio
import edge_tts
from src.models import VideoScript
from config import WORKSPACE_DIR

async def _generate_edge_tts(text: str, output_path: str):
    """Génère l'audio via Edge TTS."""
    communicate = edge_tts.Communicate(text, "fr-FR-HenriNeural")
    await communicate.save(output_path)

def generate_voices(script: VideoScript, project_id: str) -> VideoScript:
    print(f"Génération de la piste vocale unique pour '{project_id}'...")
    
    audio_dir = WORKSPACE_DIR / project_id / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = str(audio_dir / "full_voiceover.mp3")
    
    # Concaténation logique de l'accroche et du développement pour une seule prise de voix
    full_text = f"{script.hook} {script.full_voiceover_text}"
    
    try:
        asyncio.run(_generate_edge_tts(full_text, output_path))
        script.full_audio_path = output_path
        print(f"Voix off continue générée : {output_path}")
    except Exception as e:
        print(f"Erreur lors de la génération vocale : {e}")
        
    return script