import json
import argparse
import asyncio
import sys
from pathlib import Path
import edge_tts
from faster_whisper import WhisperModel

def generate_audio_and_timestamps(input_json_path: str):
    print(f"Démarrage du Module 2 (Audio & Horodatage) à partir de : {input_json_path}")
    
    # 1. Lecture du JSON d'entrée
    input_path = Path(input_json_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Le fichier {input_json_path} est introuvable.")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    project_dir = input_path.parent
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    audio_output_path = audio_dir / "voiceover.mp3"
    timestamps_output_path = audio_dir / "timestamps.json"

    # 2. Extraction du texte complet (Hook + Body)
    hook = data.get("hook", "").strip()
    body = data.get("full_voiceover_text", "").strip()
    full_text = f"{hook} {body}".strip()

    if not full_text:
        raise ValueError("Le texte de la voix off est vide dans le fichier JSON d'entrée.")

    # 3. Génération de l'audio via Edge-TTS
    print("Génération de la voix off (Edge-TTS)...")
    async def _generate_tts():
        communicate = edge_tts.Communicate(full_text, "fr-FR-HenriNeural")
        await communicate.save(str(audio_output_path))

    asyncio.run(_generate_tts())
    print(f"Fichier audio généré : {audio_output_path}")

    # 4. Transcription et extraction des horodatages (faster-whisper)
    print("Analyse de l'audio avec faster-whisper (modèle 'base')...")
    # compute_type="int8" permet de réduire drastiquement l'usage de la mémoire RAM/VRAM
    model = WhisperModel("base", device="auto", compute_type="int8")
    
    segments, _ = model.transcribe(str(audio_output_path), word_timestamps=True, language="fr")
    
    words_data = []
    for segment in segments:
        for word in segment.words:
            words_data.append({
                "word": word.word.strip(),
                "start": round(word.start, 3),
                "end": round(word.end, 3)
            })

    # 5. Sauvegarde des données temporelles
    with open(timestamps_output_path, 'w', encoding='utf-8') as f:
        json.dump(words_data, f, indent=4, ensure_ascii=False)

    print(f"Horodatages sauvegardés : {timestamps_output_path}")

    # 6. Sortie formatée pour l'orchestrateur (n8n)
    result = {
        "status": "success",
        "audio_file": str(audio_output_path.resolve()),
        "timestamps_file": str(timestamps_output_path.resolve())
    }
    
    print("\n--- OUTPUT JSON POUR N8N ---")
    print(json.dumps(result))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 2 : Génération Audio et Horodatage (Edge-TTS + faster-whisper)")
    parser.add_argument(
        "--input-json", 
        type=str, 
        required=True, 
        help="Chemin absolu ou relatif vers le fichier script.json généré par le Module 1"
    )
    
    args = parser.parse_args()
    
    try:
        generate_audio_and_timestamps(args.input_json)
    except Exception as e:
        print(f"Erreur critique dans le module 2 : {e}", file=sys.stderr)
        sys.exit(1)