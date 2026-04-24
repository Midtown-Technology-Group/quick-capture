"""
Core capture functionality for Quick Capture.

Handles appending captures to daily notes with proper formatting and section awareness.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from filelock import FileLock

from .config import AppConfig


class CaptureWriter:
    """Writes captures to daily notes with proper formatting."""
    
    # Section patterns for detection
    SECTION_PATTERNS = {
        "Work Log": re.compile(r'^##\s+Work\s*Log', re.IGNORECASE),
        "Notes": re.compile(r'^##\s+Notes', re.IGNORECASE),
        "Next Actions": re.compile(r'^##\s+Next\s*Actions', re.IGNORECASE),
        "Inbox": re.compile(r'^##\s+Inbox', re.IGNORECASE),
    }
    
    # Entry templates by type
    TEMPLATES = {
        "task": "- LATER {time} {content}",
        "idea": "- 💡 {time} {content}",
        "note": "- {time} {content}",
        "log": "- {time} {content}",
    }
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def capture(
        self,
        content: str,
        capture_type: str = "note",
        section: Optional[str] = None,
        date_str: Optional[str] = None,
    ) -> Tuple[Path, str]:
        """Capture content to daily note.
        
        Args:
            content: The content to capture
            capture_type: Type of capture (task/idea/note/log)
            section: Target section (if None, uses type mapping)
            date_str: Date in YYYY-MM-DD format (if None, uses today)
        
        Returns:
            Tuple of (file_path, formatted_entry)
        """
        # Determine section
        if section is None:
            section = self.config.qcapture.section_mappings.get(capture_type, "Work Log")
        
        # Format entry
        entry = self._format_entry(content, capture_type)
        
        # Get target file
        note_path = self.config.get_today_note_path(date_str)
        
        # Write entry
        self._write_to_note(note_path, entry, section)
        
        return note_path, entry
    
    def _format_entry(self, content: str, capture_type: str) -> str:
        """Format entry with timestamp and aliases applied."""
        # Get current time
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        
        # Apply aliases
        content = self._apply_aliases(content)
        
        # Get template
        template = self.TEMPLATES.get(capture_type, self.TEMPLATES["note"])
        
        return template.format(time=time_str, content=content)
    
    def _apply_aliases(self, content: str) -> str:
        """Apply alias substitutions to content."""
        aliases = self.config.qcapture.aliases
        
        # Sort by length (longest first) to avoid partial matches
        for alias, replacement in sorted(aliases.items(), key=lambda x: -len(x[0])):
            # Match whole words only
            pattern = rf'\b{re.escape(alias)}\b'
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        return content
    
    def _write_to_note(self, note_path: Path, entry: str, section: str):
        """Write entry to note, creating if needed and finding section."""
        # Ensure directory exists
        note_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Acquire file lock for safe concurrent writes
        lock_path = note_path.with_suffix(note_path.suffix + ".lock")
        lock = FileLock(lock_path, timeout=10)
        
        with lock:
            if not note_path.exists():
                # Create new daily note
                self._create_new_note(note_path)
            
            # Read existing content
            content = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
            
            # Find or create section
            new_content = self._insert_in_section(content, entry, section)
            
            # Write back
            note_path.write_text(new_content, encoding="utf-8")
    
    def _create_new_note(self, note_path: Path):
        """Create a new daily note with standard template."""
        date_str = note_path.stem  # YYYY-MM-DD
        
        template = f"""# {date_str}

## Today's Focus


## Next Actions


## Work Log


## Notes


## Links

"""
        note_path.write_text(template, encoding="utf-8")
    
    def _insert_in_section(self, content: str, entry: str, section: str) -> str:
        """Insert entry into specified section.
        
        If section doesn't exist, creates it.
        If section exists, appends entry at end of section.
        """
        lines = content.split('\n')
        
        # Find section
        section_idx = -1
        next_section_idx = len(lines)
        
        for i, line in enumerate(lines):
            if self._is_section_header(line, section):
                section_idx = i
                # Find next section
                for j in range(i + 1, len(lines)):
                    if line.startswith("## "):
                        next_section_idx = j
                        break
                break
        
        if section_idx == -1:
            # Section doesn't exist, create it at end
            content = content.rstrip()
            if content:
                content += "\n\n"
            content += f"## {section}\n\n{entry}"
            return content
        
        # Find last non-empty line in section
        insert_idx = section_idx + 1
        for i in range(section_idx + 1, next_section_idx):
            if lines[i].strip():
                insert_idx = i + 1
        
        # Insert entry
        lines.insert(insert_idx, entry)
        return '\n'.join(lines)
    
    def _is_section_header(self, line: str, section: str) -> bool:
        """Check if line is a section header."""
        pattern = self.SECTION_PATTERNS.get(section)
        if pattern:
            return bool(pattern.match(line))
        # Generic check for ## Section Name
        return line.startswith(f"## {section}")
