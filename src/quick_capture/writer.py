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
        if capture_type not in self.TEMPLATES:
            raise ValueError(f"Invalid capture type: {capture_type!r}")

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
        template = self.TEMPLATES[capture_type]
        
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
            
            # Keep original newlines and leave the unchanged prefix on disk.
            with note_path.open("r+", encoding="utf-8", newline="") as note:
                content = note.read()
                new_content = self._insert_in_section(content, entry, section)
                offset = 0
                while offset < len(content) and content[offset] == new_content[offset]:
                    offset += 1
                note.seek(0)
                note.read(offset)
                position = note.tell()
                note.seek(position)
                note.write(new_content[offset:])
    
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
        newline = "\r\n" if "\r\n" in content else "\n"
        lines = content.splitlines(keepends=True)
        section_headers = set(self._section_header_indices(lines))
        offset = 0
        for i, line in enumerate(lines):
            if i in section_headers and self._is_section_header(line.rstrip("\r\n"), section):
                insert_at = offset + len(line)
                cursor = insert_at
                for j, following in enumerate(lines[i + 1 :], start=i + 1):
                    if j in section_headers:
                        break
                    cursor += len(following)
                    if following.strip():
                        insert_at = cursor
                prefix = "" if content[:insert_at].endswith("\n") else newline
                return content[:insert_at] + prefix + entry + newline + content[insert_at:]
            offset += len(line)

        # Add a missing section without stripping existing whitespace or content.
        separator = "" if not content or content.endswith(newline * 2) else newline
        if content and not content.endswith(newline):
            separator += newline
        return content + separator + f"## {section}{newline}{newline}{entry}{newline}"
    
    def _section_header_indices(self, lines):
        """Yield level-two ATX headings outside backtick and tilde fences."""
        fence = None
        for i, line in enumerate(lines):
            line = line.rstrip("\r\n")
            if fence is not None:
                closing = re.fullmatch(r" {0,3}([`~]+)[ \t]*", line)
                if (
                    closing
                    and len(closing[1]) >= len(fence)
                    and set(closing[1]) == {fence[0]}
                ):
                    fence = None
                continue
            opening = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", line)
            if opening and not (opening[1][0] == "`" and "`" in opening[2]):
                fence = opening[1]
                continue
            if re.match(r"^ {0,3}##[ \t]+", line):
                yield i
        if fence is not None:
            raise ValueError("Cannot safely capture into a journal with an unclosed code fence")

    def _is_section_header(self, line: str, section: str) -> bool:
        """Match a complete section name, never a longer name with the same prefix."""
        line = re.sub(r"[ \t]+#+[ \t]*$", "", line).lstrip(" ")
        pattern = self.SECTION_PATTERNS.get(section)
        if pattern:
            return bool(pattern.fullmatch(line.rstrip(" \t")))
        return bool(re.fullmatch(r"##[ \t]+" + re.escape(section) + r"[ \t]*", line))
