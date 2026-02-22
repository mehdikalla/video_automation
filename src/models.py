from pydantic import BaseModel, Field
from typing import List, Optional

class PipelineConfig(BaseModel):
    script_engine: str = "gemini"
    voice_engine: str = "edge_tts"
    image_engine: str = "dummy"
    video_engine: str = "moviepy"
    music_engine: str = "local"
    num_scenes: int = 12
    target_duration: int = 20
    angle: Optional[str] = None

class Scene(BaseModel):
    id: int
    visual_prompt: str
    image_path: Optional[str] = None
    video_path: Optional[str] = None

class VideoScript(BaseModel):
    theme: str
    hook: str
    full_voiceover_text: str
    full_audio_path: Optional[str] = None
    scenes: List[Scene]
    bg_music_path: Optional[str] = None
    config: PipelineConfig = Field(default_factory=PipelineConfig)