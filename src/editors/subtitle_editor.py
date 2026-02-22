import os
import subprocess
import whisper
import imageio_ffmpeg
from src.models import VideoScript
from config import WORKSPACE_DIR

def _format_timestamp_ass(seconds: float) -> str:
    """Convertit les secondes au format ASS (H:MM:SS.cs)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

def apply_subtitles(script: VideoScript, project_id: str) -> str:
    print(f"Début de la génération des sous-titres dynamiques (ASS) pour '{project_id}'...")
    
    project_dir = WORKSPACE_DIR / project_id
    input_video = project_dir / "final_video.mp4"
    ass_path = project_dir / "subtitles.ass"
    output_video = project_dir / "final_video_subtitled.mp4"
    
    if not os.path.exists(input_video):
        raise FileNotFoundError(f"Vidéo source introuvable : {input_video}")
        
    print("Transcription de l'audio (Whisper) avec horodatage par mot...")
    model = whisper.load_model("base")
    
    # condition_on_previous_text=False empêche l'IA de répéter la première phrase
    result = model.transcribe(
        str(input_video), 
        language="fr", 
        word_timestamps=True,
        condition_on_previous_text=False
    )
    
    print("Génération du fichier de sous-titres avancé (.ass)...")
    
    # Regroupement dynamique (max 2 mots pour le style TikTok)
    tiktok_segments = []
    
    for segment in result.get("segments", []):
        if "words" in segment:
            current_words = []
            current_start = None
            
            for word_info in segment["words"]:
                if current_start is None:
                    current_start = word_info["start"]
                
                clean_word = word_info["word"].strip().upper()
                current_words.append(clean_word)
                
                if len(current_words) >= 2:
                    tiktok_segments.append({
                        "start": current_start,
                        "end": word_info["end"],
                        "text": "\\N".join(current_words) # Saut de ligne en ASS
                    })
                    current_words = []
                    current_start = None
            
            if current_words:
                tiktok_segments.append({
                    "start": current_start,
                    "end": segment["words"][-1]["end"],
                    "text": "\\N".join(current_words)
                })

    # Écriture de l'en-tête du fichier ASS
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1024
PlayResY: 1792

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Tiktok,Arial,90,&H0000FFFF,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,4,2,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    with open(ass_path, "w", encoding="utf-8") as ass_file:
        ass_file.write(ass_header)
        for seg in tiktok_segments:
            start_time = _format_timestamp_ass(seg["start"])
            end_time = _format_timestamp_ass(seg["end"])
            text = seg["text"]
            ass_file.write(f"Dialogue: 0,{start_time},{end_time},Tiktok,,0,0,0,,{text}\n")
            
    print("Incrustation des sous-titres sur la vidéo...")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    escaped_ass_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
    
    command = [
        ffmpeg_exe, "-y",
        "-i", str(input_video),
        "-vf", f"ass='{escaped_ass_path}'",
        "-c:a", "copy",
        str(output_video)
    ]
    
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if process.returncode != 0:
        raise RuntimeError(f"L'incrustation a échoué :\n{process.stderr}")
        
    print(f"Sous-titrage terminé : {output_video}")
    return str(output_video)