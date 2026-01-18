# services/video.py
import os
import subprocess
import re
import urllib.request
from pathlib import Path

import yt_dlp
from PIL import Image, ImageDraw, ImageFont

from config import DOWNLOAD_DIR, TEMPLATE_WIDTH, TEMPLATE_HEIGHT, DEFAULT_COLOR1, DEFAULT_COLOR2
from utils import parse_markdown_bold

# Font paths
ASSETS_DIR = Path(__file__).parent.parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
FONT_REGULAR = FONTS_DIR / "Poppins-SemiBold.ttf"
FONT_BOLD = FONTS_DIR / "Poppins-Bold.ttf"
LOGO_PATH = FONTS_DIR / "logo.png"

FONT_URLS = {
    "Poppins-SemiBold.ttf": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-SemiBold.ttf",
    "Poppins-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf",
}


def ensure_fonts():
    """Download fonts if not present"""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in FONT_URLS.items():
        filepath = FONTS_DIR / filename
        if not filepath.exists():
            print(f"[FONTS] Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, filepath)
            except Exception as e:
                print(f"[FONTS] Failed: {e}")


def get_video_info(url: str) -> dict:
    ydl_opts = {"noplaylist": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title"),
            "duration": int(info.get("duration", 0) or 0),
            "thumbnail": info.get("thumbnail"),
            "channel": info.get("channel") or info.get("uploader"),
        }


def download_video(url: str, output_path: str, start_sec: int = None, end_sec: int = None) -> dict:
    ydl_opts = {
        "outtmpl": output_path.replace('.mp4', '.%(ext)s'),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "noplaylist": True,
        "merge_output_format": "mp4",
    }
    if start_sec and start_sec > 0 or end_sec:
        ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(start_sec or 0, end_sec)])
        ydl_opts["force_keyframes_at_cuts"] = True
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=True)


def extract_preview_frame(video_path: str, output_path: str) -> tuple:
    """Extract a frame from video for preview and return dimensions"""
    # Get video dimensions
    probe_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=width,height', '-of', 'csv=p=0', video_path]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    parts = result.stdout.strip().split(',')
    width, height = int(parts[0]), int(parts[1])
    
    # Extract frame at 1 second (or first frame)
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-ss', '00:00:01',
        '-vframes', '1',
        '-q:v', '2',
        output_path
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True)
    
    # If first attempt failed, try frame 0
    if not os.path.exists(output_path):
        ffmpeg_cmd[4] = '00:00:00'
        subprocess.run(ffmpeg_cmd, capture_output=True)
    
    return width, height


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def strip_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55"
        "\u200d\u23cf\u23e9\u231a\ufe0f\u3030"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip()


def draw_rounded_rectangle(draw: ImageDraw, xy: tuple, radius: int, 
                           fill: tuple = None, outline: tuple = None, width: int = 1):
    """Draw a proper rounded rectangle with corners"""
    x1, y1, x2, y2 = xy
    
    if fill:
        # Fill the rounded rectangle
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
        draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
        draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
        draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)
    
    if outline:
        # Draw the outline/border
        # Top line
        draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
        # Bottom line
        draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
        # Left line
        draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
        # Right line
        draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)
        # Corner arcs
        draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=outline, width=width)
        draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=outline, width=width)
        draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=outline, width=width)
        draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=outline, width=width)


def get_gradient_color(c1: tuple, c2: tuple, ratio: float) -> tuple:
    return tuple(int(a + (b - a) * ratio) for a, b in zip(c1, c2))


def draw_gradient_text(draw: ImageDraw, text: str, pos: tuple, font: ImageFont, c1: tuple, c2: tuple):
    """Draw text with gradient color (2 colors)"""
    x, y = pos
    for i, char in enumerate(text):
        ratio = i / max(len(text) - 1, 1)
        color = get_gradient_color(c1, c2, ratio)
        draw.text((x, y), char, font=font, fill=color)
        bbox = font.getbbox(char)
        x += bbox[2] - bbox[0]


def draw_3color_gradient_text(draw: ImageDraw, text: str, pos: tuple, font: ImageFont, c1: tuple, c2: tuple, c3: tuple):
    """Draw text with 3-color gradient (cyan → middle → purple)"""
    x, y = pos
    length = len(text)
    for i, char in enumerate(text):
        ratio = i / max(length - 1, 1)
        # First half: c1 → c2, Second half: c2 → c3
        if ratio <= 0.5:
            local_ratio = ratio * 2
            color = get_gradient_color(c1, c2, local_ratio)
        else:
            local_ratio = (ratio - 0.5) * 2
            color = get_gradient_color(c2, c3, local_ratio)
        draw.text((x, y), char, font=font, fill=color)
        bbox = font.getbbox(char)
        x += bbox[2] - bbox[0]


def create_text_overlay(
    title: str,
    body_text: str,
    username: str,
    platform: str,
    color1: str,
    color2: str,
    output_path: str
) -> str:
    """Create text overlay with title and body"""
    
    ensure_fonts()
    
    primary_rgb = hex_to_rgb(color1)
    secondary_rgb = hex_to_rgb(color2)
    
    # Title gradient colors: cyan → light blue → purple
    cyan_rgb = (0, 235, 255)  # Bright cyan
    mid_rgb = (100, 180, 255)  # Light blue middle
    purple_rgb = (218, 94, 255)  # #DA5EFF
    
    # Body highlight color: solid aqua
    highlight_rgb = (14, 235, 234)  # #0EEBEA
    
    # Clean text
    clean_title = strip_emojis(title) if title else ""
    clean_body, bold_words = parse_markdown_bold(strip_emojis(body_text) if body_text else "")
    
    # Username
    platform_prefix = {"instagram": "@", "twitter": "@", "facebook": "", "youtube": "@"}
    prefix = platform_prefix.get(platform, "@")
    display_username = strip_emojis(username) if username else ""
    if display_username and not display_username.startswith("@"):
        display_username = f"{prefix}{display_username}"
    
    # Create overlay
    overlay = Image.new('RGBA', (TEMPLATE_WIDTH, TEMPLATE_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Load fonts
    try:
        font_title = ImageFont.truetype(str(FONT_BOLD), 48)
        font_body = ImageFont.truetype(str(FONT_REGULAR), 42)
        font_username = ImageFont.truetype(str(FONT_REGULAR), 35)
    except:
        font_title = font_body = font_username = ImageFont.load_default()
    
    # === TEXT BOX ===
    box_margin = 36
    box_padding_x = 44
    box_padding_y = 36
    box_radius = 24
    
    # Calculate title height
    title_height = 0
    if clean_title:
        title_bbox = font_title.getbbox(clean_title)
        title_height = title_bbox[3] - title_bbox[1] + 24  # + spacing
    
    # Word wrap body
    max_width = TEMPLATE_WIDTH - (box_margin * 2) - (box_padding_x * 2)
    body_lines = []
    
    if clean_body:
        words = clean_body.split()
        current_line = []
        current_width = 0
        
        for word in words:
            word_bbox = font_body.getbbox(word + " ")
            word_width = word_bbox[2] - word_bbox[0]
            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width
            else:
                if current_line:
                    body_lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_width
        if current_line:
            body_lines.append(" ".join(current_line))
    
    body_lines = body_lines[:5]
    
    # Calculate box dimensions
    line_height = 64
    body_height = len(body_lines) * line_height if body_lines else 0
    
    box_x1 = box_margin
    box_y1 = 180
    box_x2 = TEMPLATE_WIDTH - box_margin
    box_y2 = box_y1 + title_height + body_height + (box_padding_y * 2)
    
    # Draw box - translucent primary color background
    bg_color = (*primary_rgb, 200)  # 78% opacity
    draw_rounded_rectangle(draw, (box_x1, box_y1, box_x2, box_y2), box_radius, fill=bg_color)
    
    # Draw border - gradient colors
    border_color = (*secondary_rgb, 255)
    draw_rounded_rectangle(draw, (box_x1, box_y1, box_x2, box_y2), box_radius, outline=border_color, width=3)
    
    # Draw title (3-color gradient: cyan → light blue → purple)
    if clean_title:
        title_bbox = font_title.getbbox(clean_title)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (TEMPLATE_WIDTH - title_width) // 2
        title_y = box_y1 + box_padding_y
        
        draw_3color_gradient_text(draw, clean_title, (title_x, title_y), font_title, cyan_rgb, mid_rgb, purple_rgb)
    
    # Draw body text
    if body_lines:
        text_y = box_y1 + box_padding_y + title_height
        
        for line in body_lines:
            # Calculate line width for centering
            line_bbox = font_body.getbbox(line)
            line_width = line_bbox[2] - line_bbox[0]
            current_x = (TEMPLATE_WIDTH - line_width) // 2
            
            # Draw word by word
            for word in line.split():
                clean_word = word.strip('.,!?"\':;()[]')
                is_highlighted = clean_word in bold_words
                
                if is_highlighted:
                    # Solid aqua color for highlighted
                    draw.text((current_x, text_y), word + " ", font=font_body, fill=(*highlight_rgb, 255))
                else:
                    # White for regular
                    draw.text((current_x, text_y), word + " ", font=font_body, fill=(255, 255, 255, 255))
                
                word_bbox = font_body.getbbox(word + " ")
                current_x += word_bbox[2] - word_bbox[0]
            
            text_y += line_height
    
    # Username
    if display_username:
        username_y = TEMPLATE_HEIGHT - 75
        username_bbox = font_username.getbbox(display_username)
        username_x = (TEMPLATE_WIDTH - (username_bbox[2] - username_bbox[0])) // 2
        draw.text((username_x, username_y), display_username, font=font_username, fill=(255, 255, 255, 130))
    
    # Add logo in top-right corner
    try:
        if LOGO_PATH.exists():
            logo = Image.open(LOGO_PATH).convert('RGBA')
            # Scale logo to fit nicely (max 150px height)
            logo_max_height = 240
            if logo.height > logo_max_height:
                ratio = logo_max_height / logo.height
                logo = logo.resize((int(logo.width * ratio), logo_max_height), Image.LANCZOS)
            # Position: top-right with padding
            logo_x = TEMPLATE_WIDTH - logo.width - 30
            logo_y = 20
            overlay.paste(logo, (logo_x, logo_y), logo)
    except Exception as e:
        print(f"[LOGO] Failed to load logo: {e}")
    
    overlay.save(output_path, 'PNG')
    return output_path


def create_gradient_background(color1: str, color2: str, angle: str, output_path: str):
    """Create a static gradient background image using Pillow"""
    c1 = hex_to_rgb(color1)
    c2 = hex_to_rgb(color2)
    
    img = Image.new('RGB', (TEMPLATE_WIDTH, TEMPLATE_HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # Determine gradient direction
    if angle in ['top-bottom', 'bottom-top']:
        for y in range(TEMPLATE_HEIGHT):
            ratio = y / TEMPLATE_HEIGHT
            if angle == 'bottom-top':
                ratio = 1 - ratio
            color = get_gradient_color(c1, c2, ratio)
            draw.line([(0, y), (TEMPLATE_WIDTH, y)], fill=color)
    elif angle in ['left-right', 'right-left']:
        for x in range(TEMPLATE_WIDTH):
            ratio = x / TEMPLATE_WIDTH
            if angle == 'right-left':
                ratio = 1 - ratio
            color = get_gradient_color(c1, c2, ratio)
            draw.line([(x, 0), (x, TEMPLATE_HEIGHT)], fill=color)
    else:
        # Diagonal gradients
        for y in range(TEMPLATE_HEIGHT):
            for x in range(TEMPLATE_WIDTH):
                if angle == 'diagonal-br':
                    ratio = (x + y) / (TEMPLATE_WIDTH + TEMPLATE_HEIGHT)
                elif angle == 'diagonal-bl':
                    ratio = ((TEMPLATE_WIDTH - x) + y) / (TEMPLATE_WIDTH + TEMPLATE_HEIGHT)
                elif angle == 'diagonal-tr':
                    ratio = (x + (TEMPLATE_HEIGHT - y)) / (TEMPLATE_WIDTH + TEMPLATE_HEIGHT)
                else:  # diagonal-tl
                    ratio = ((TEMPLATE_WIDTH - x) + (TEMPLATE_HEIGHT - y)) / (TEMPLATE_WIDTH + TEMPLATE_HEIGHT)
                color = get_gradient_color(c1, c2, ratio)
                img.putpixel((x, y), color)
    
    img.save(output_path, 'PNG')
    return output_path


def get_gradient_coords(angle: str, w: int, h: int) -> tuple:
    presets = {
        "top-bottom": (w//2, 0, w//2, h),
        "bottom-top": (w//2, h, w//2, 0),
        "left-right": (0, h//2, w, h//2),
        "right-left": (w, h//2, 0, h//2),
        "diagonal-br": (0, 0, w, h),
        "diagonal-bl": (w, 0, 0, h),
        "diagonal-tr": (0, h, w, 0),
        "diagonal-tl": (w, h, 0, 0),
    }
    return presets.get(angle, presets["diagonal-br"])


def create_template_video(
    input_path: str, 
    output_path: str, 
    title: str,
    body_text: str, 
    username: str, 
    platform: str,
    color1: str = DEFAULT_COLOR1,
    color2: str = DEFAULT_COLOR2,
    bg_image_path: str = None,
    gradient_angle: str = "diagonal-br",
    crop_params: dict = None
):
    """Create professional video template with optional cropping"""
    
    # Get video dimensions
    probe_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
                 '-show_entries', 'stream=width,height', '-of', 'csv=p=0', input_path]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    parts = result.stdout.strip().split(',')
    src_w, src_h = int(parts[0]), int(parts[1])
    
    # Apply crop if specified (percentages to pixels)
    crop_filter = ""
    if crop_params and (crop_params.get('w', 100) < 100 or crop_params.get('h', 100) < 100 
                        or crop_params.get('x', 0) > 0 or crop_params.get('y', 0) > 0):
        crop_x = int(src_w * crop_params.get('x', 0) / 100)
        crop_y = int(src_h * crop_params.get('y', 0) / 100)
        crop_w = int(src_w * crop_params.get('w', 100) / 100)
        crop_h = int(src_h * crop_params.get('h', 100) / 100)
        crop_filter = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
        # Update source dimensions after crop
        src_w, src_h = crop_w, crop_h
    
    # Create overlay
    overlay_path = output_path.replace('.mp4', '_overlay.png')
    create_text_overlay(title, body_text, username, platform, color1, color2, overlay_path)
    
    # Create gradient background if not using image
    bg_path = bg_image_path
    created_bg = False
    if not bg_image_path or not os.path.exists(bg_image_path):
        bg_path = output_path.replace('.mp4', '_bg.png')
        create_gradient_background(color1, color2, gradient_angle, bg_path)
        created_bg = True
    
    # Video scaling - FULL WIDTH
    scale = TEMPLATE_WIDTH / src_w
    scaled_w = TEMPLATE_WIDTH
    scaled_h = int(src_h * scale)
    
    video_top = 480
    footer = 100
    video_area = TEMPLATE_HEIGHT - video_top - footer
    
    if scaled_h > video_area:
        scale = video_area / src_h
        scaled_h = int(src_h * scale)
        scaled_w = int(src_w * scale)
    
    video_x = (TEMPLATE_WIDTH - scaled_w) // 2
    video_y = video_top + (video_area - scaled_h) // 2
    
    # FFmpeg filter with optional crop
    filter_complex = (
        f"[1:v]scale={TEMPLATE_WIDTH}:{TEMPLATE_HEIGHT}[bg];"
        f"[0:v]{crop_filter}scale={scaled_w}:{scaled_h}[scaled];"
        f"[bg][scaled]overlay={video_x}:{video_y}[v1];"
        f"[v1][2:v]overlay=0:0:format=auto[vout]"
    )
    
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-loop', '1', '-i', bg_path,
        '-loop', '1', '-i', overlay_path,
        '-filter_complex', filter_complex,
        '-map', '[vout]',
        '-map', '0:a?',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ]
    
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    
    # Cleanup
    if os.path.exists(overlay_path):
        os.remove(overlay_path)
    if created_bg and os.path.exists(bg_path):
        os.remove(bg_path)
    
    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")
    
    return output_path
