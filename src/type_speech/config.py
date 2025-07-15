import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, List
from type_speech.logger import logger


class AppConfig(BaseModel):
    """Application configuration"""
    file_log_level: str = "debug"
    console_log_level: str = "info"

class HotkeyConfig(BaseModel):
    """Hotkey configuration"""
    start_recording: str = "f7"  # f7, ctrl+shift+m, ctrl+alt+r, etc.
    stop_recording: str = "f8"
    exit_app: str = "f9"


class AudioConfig(BaseModel):
    """Audio configuration"""
    rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    chunk: int = 1600


class SpeechConfig(BaseModel):
    """Speech recognition configuration"""
    language_code: str = "ru-RU"
    alternative_language_codes: List[str] = ["en-US"]
    model: str = "default"
    enable_automatic_punctuation: bool = True
    use_enhanced: bool = True
    accuracy_threshold: float = Field(default=0.7, ge=0.0, le=1.0)  
    enable_interim_phrases: bool = True
    speech_contexts: list[dict[str, Any]] = []


class KeyboardConfig(BaseModel):
    """Keyboard configuration"""
    clipboard_delay: float = 0.05
    key_interval: float = 0.01
    post_hotkey_delay: float = 0.05


class CredentialsConfig(BaseModel):
    """Credentials configuration"""
    google_cloud_path: str = "credentials/google-credentials.json"


class Config(BaseModel):
    """Main application configuration"""
    app: AppConfig = AppConfig()
    hotkeys: HotkeyConfig = HotkeyConfig()
    audio: AudioConfig = AudioConfig()
    speech: SpeechConfig = SpeechConfig()
    keyboard: KeyboardConfig = KeyboardConfig()
    credentials: CredentialsConfig = CredentialsConfig()

    @classmethod
    def load(cls, config_dir: str = "config") -> "Config":
        """Load configuration from YAML files"""
        config_path = Path(config_dir)
        default_path = config_path / "default.yaml"
        user_path = config_path / "user.yaml"
        
        # Load default config
        if default_path.exists():
            with open(default_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        else:
            logger.warning(f"Default config not found: {default_path}")
            config_data = {}
        
        # Override with user config
        if user_path.exists():
            with open(user_path, 'r', encoding='utf-8') as f:
                user_data = yaml.safe_load(f)
                _merge_dicts(config_data, user_data)
                logger.info(f"Loaded user config: {user_path}")
        
        return cls(**config_data)


def _merge_dicts(base: dict, override: dict) -> None:
    """Merge override dict into base dict"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _merge_dicts(base[key], value)
        else:
            base[key] = value


# Global config instance
config = Config.load() 