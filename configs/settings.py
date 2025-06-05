import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseConfig:
    db_path: str = "data/music_app.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24

@dataclass
class LLMConfig:
    openai_api_key: str = ""
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.3
    max_tokens: int = 1000
    context_window: int = 4000

@dataclass
class ReinforcementLearningConfig:
    min_training_samples: int = 5
    learning_rate: float = 0.01
    exploration_rate: float = 0.1
    discount_factor: float = 0.95
    update_frequency: int = 10

@dataclass
class MusicAPIConfig:
    lastfm_api_key: str = ""
    deezer_enabled: bool = True
    itunes_enabled: bool = True
    musicbrainz_enabled: bool = True
    rate_limit_per_minute: int = 100

@dataclass
class UIConfig:
    theme: str = "dark"
    max_recommendations: int = 10
    enable_audio_preview: bool = True
    auto_refresh_interval: int = 300

class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.database = DatabaseConfig(
            db_path=os.getenv("DB_PATH", "data/music_app.db"),
            backup_enabled=os.getenv("DB_BACKUP_ENABLED", "true").lower() == "true"
        )
        
        self.llm = LLMConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            model_name=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3"))
        )
        
        self.rl = ReinforcementLearningConfig(
            min_training_samples=int(os.getenv("RL_MIN_SAMPLES", "5")),
            learning_rate=float(os.getenv("RL_LEARNING_RATE", "0.01"))
        )
        
        self.music_api = MusicAPIConfig(
            lastfm_api_key=os.getenv("LASTFM_API_KEY", "")
        )
        
        self.ui = UIConfig(
            theme=os.getenv("UI_THEME", "dark"),
            max_recommendations=int(os.getenv("UI_MAX_RECOMMENDATIONS", "10"))
        )
        
        self.validate()
    
    def validate(self):
        """Validate configuration"""
        if not self.llm.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        if self.rl.min_training_samples < 3:
            raise ValueError("RL_MIN_SAMPLES must be at least 3")
