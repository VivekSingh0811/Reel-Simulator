# utils.py
import re


def time_to_seconds(t: str) -> int | None:
    """Convert HH:MM:SS to seconds"""
    if not t:
        return None
    parts = t.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(parts[0])


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def escape_text_for_ffmpeg(text: str) -> str:
    """Escape text for ffmpeg drawtext filter"""
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("'", "'\\''").replace(":", "\\:").replace("%", "\\%")


def parse_markdown_bold(text: str) -> tuple[str, set]:
    """Parse text with **bold** markers, returns (clean_text, bold_word_set)"""
    if not text:
        return "", set()
    bold_words = set()
    pattern = r'\*\*([^*]+)\*\*'
    for match in re.finditer(pattern, text):
        for word in match.group(1).split():
            bold_words.add(word.strip('.,!?"'))
    clean_text = re.sub(pattern, r'\1', text)
    return clean_text, bold_words
