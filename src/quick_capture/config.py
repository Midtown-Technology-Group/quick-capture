"""
Configuration models for Quick Capture CLI.

Shares config file with work-context-sync for vault path and timezone.
"""

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class QCaptureConfig(BaseModel):
    """Quick-capture specific configuration."""
    
    aliases: Dict[str, str] = Field(default_factory=dict)
    default_section: str = "Work Log"
    section_mappings: Dict[str, str] = Field(default_factory=lambda: {
        "task": "Work Log",
        "idea": "Notes",
        "note": "Notes", 
        "log": "Work Log",
    })


class AppConfig(BaseSettings):
    """Main application configuration.
    
    Reads from ~/.work-context-sync/config.yaml (shared with work-context-sync)
    or ~/.quick-capture/config.yaml for qcapture-specific settings.
    """
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        yaml_file='~/.work-context-sync/config.yaml',
        yaml_file_encoding='utf-8',
        extra='ignore',
    )
    
    # Shared with work-context-sync
    vault_path: Path = Field(default=Path.home() / "Knowledge")
    timezone: str = Field(default="America/New_York")
    
    # Quick-capture specific
    qcapture: QCaptureConfig = Field(default_factory=QCaptureConfig)
    
    @field_validator('vault_path')
    @classmethod
    def expand_vault_path(cls, v: Path) -> Path:
        """Expand user home directory in vault path."""
        return v.expanduser().resolve()
    
    @property
    def daily_notes_path(self) -> Path:
        """Path to daily notes folder."""
        return self.vault_path / "daily"
    
    def get_today_note_path(self, date_str: Optional[str] = None) -> Path:
        """Get path to today's (or specified) daily note.
        
        Args:
            date_str: Date in YYYY-MM-DD format. If None, uses today.
        
        Returns:
            Path to the daily note file.
        """
        from datetime import datetime
        
        if date_str:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            date_obj = datetime.now()
        
        return self.daily_notes_path / f"{date_obj.strftime('%Y-%m-%d')}.md"


def load_config() -> AppConfig:
    """Load configuration from file."""
    try:
        return AppConfig()
    except Exception:
        # Return default config if file doesn't exist or is invalid
        return AppConfig()
