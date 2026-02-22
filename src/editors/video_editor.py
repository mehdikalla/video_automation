import os
import subprocess
import imageio_ffmpeg
from moviepy import AudioFileClip
from src.models import VideoScript
from config import WORKSPACE_DIR

def assemble_video(script: VideoScript, project_id: str) -> str:
    print(f"Assemblage découplé (synchronisation par durée globale) pour '{project_id}'...")
    
    project_dir = WORKSPACE_DIR / project_id
    output_path = project_dir / "final_video.mp4"
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    if not script.full_audio_path or not os.path.exists(script.full_audio_path):
        raise FileNotFoundError("Piste vocale globale introuvable.")

    # 1. Extraction de la durée totale de la voix off
    audio = AudioFileClip(script.full_audio_path)
    total_audio_duration = audio.duration
    audio.close()

    valid_images = [s.image_path for s in script.scenes if s.image_path and os.path.exists(s.image_path)]
    if not valid_images:
        raise ValueError("Aucune image valide trouvée pour l'assemblage.")

    # 2. Calcul mathématique de la durée par image
    num_images = len(valid_images)
    time_per_image = total_audio_duration / num_images
    crossfade_dur = 0.5

    inputs = []
    filter_chains = []

    # 3. Préparation des flux vidéo
    for i, img_path in enumerate(valid_images):
        inputs.extend(["-i", str(img_path)])
        
        # Allongement de la durée pour permettre le fondu croisé (sauf la dernière image)
        v_dur = time_per_image + crossfade_dur if i < num_images - 1 else time_per_image
        frames = int(v_dur * 24)

        zoom_expr = f"1.0+0.3*(1-pow(1-min(on/{frames},1),3))"
        chain_v = f"[{i}:v]format=yuv420p,scale=1024x1792,zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1024x1792:fps=24[v{i}]"
        filter_chains.append(chain_v)

    # 4. Transitions
    if num_images > 1:
        current_offset = 0.0
        last_v = "[v0]"
        for i in range(1, num_images):
            current_offset += time_per_image
            v_out = f"[v_xfade{i}]" if i < num_images - 1 else "[v_final]"
            xfade = f"{last_v}[v{i}]xfade=transition=fade:duration={crossfade_dur}:offset={current_offset}{v_out}"
            filter_chains.append(xfade)
            last_v = v_out
    else:
        filter_chains.append("[v0]copy[v_final]")

    # 5. Mixage audio (Voix off continue + Musique)
    inputs.extend(["-i", str(script.full_audio_path)])
    voice_idx = num_images

    bg_input = []
    if script.bg_music_path and os.path.exists(script.bg_music_path):
        bg_idx = num_images + 1
        bg_input = ["-stream_loop", "-1", "-i", str(script.bg_music_path)]
        chain_bg = f"[{voice_idx}:a]aresample=44100,aformat=sample_rates=44100:channel_layouts=stereo[voice];[{bg_idx}:a]aresample=44100,aformat=sample_rates=44100:channel_layouts=stereo,volume=0.15[bg_vol];[voice][bg_vol]amix=inputs=2:duration=first:dropout_transition=2[a_final]"
        filter_chains.append(chain_bg)
    else:
        filter_chains.append(f"[{voice_idx}:a]aresample=44100,aformat=sample_rates=44100:channel_layouts=stereo[a_final]")

    complex_filter = ";".join(filter_chains)

    command = [ffmpeg_exe, "-y"] + inputs + bg_input + [
        "-filter_complex", complex_filter,
        "-map", "[v_final]",
        "-map", "[a_final]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_path)
    ]

    print("Rendu FFmpeg avec audio continu...")
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if process.returncode != 0:
        raise RuntimeError(f"Erreur de rendu :\n{process.stderr}")

    return str(output_path)