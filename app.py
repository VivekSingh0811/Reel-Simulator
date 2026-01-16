# app.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
import yt_dlp
import uuid
import os
import subprocess
import shlex

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UniDownloader</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2.5rem; background: linear-gradient(90deg, #e94560, #0f3460); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; }
        input[type="text"], textarea { flex: 1; padding: 15px; border: none; border-radius: 10px; font-size: 16px; background: rgba(255,255,255,0.1); color: #fff; }
        input[type="text"]::placeholder, textarea::placeholder { color: rgba(255,255,255,0.5); }
        textarea { resize: vertical; min-height: 80px; font-family: inherit; }
        button { padding: 15px 30px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; transition: all 0.3s; }
        .btn-primary { background: linear-gradient(90deg, #e94560, #0f3460); color: #fff; }
        .btn-primary:hover { transform: scale(1.05); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .preview-section { display: none; background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-top: 20px; }
        .preview-section.active { display: block; }
        .video-info { display: flex; gap: 20px; margin-bottom: 20px; }
        .thumbnail { width: 320px; height: 180px; border-radius: 10px; object-fit: cover; }
        .info { flex: 1; }
        .info h3 { margin-bottom: 10px; color: #e94560; }
        .info p { color: rgba(255,255,255,0.7); margin-bottom: 5px; }
        .time-controls { display: flex; gap: 20px; align-items: center; flex-wrap: wrap; margin: 20px 0; }
        .time-input { display: flex; flex-direction: column; gap: 5px; }
        .time-input label { font-size: 14px; color: rgba(255,255,255,0.7); }
        .time-input input { padding: 10px; border: none; border-radius: 8px; background: rgba(255,255,255,0.1); color: #fff; width: 120px; }
        .template-section { margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); }
        .template-section h4 { margin-bottom: 15px; color: #e94560; }
        .template-input { display: flex; flex-direction: column; gap: 5px; margin-bottom: 15px; }
        .template-input label { font-size: 14px; color: rgba(255,255,255,0.7); }
        .template-input input, .template-input textarea { width: 100%; }
        .platform-select { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        .platform-btn { padding: 8px 16px; border-radius: 20px; background: rgba(255,255,255,0.1); color: #fff; border: 2px solid transparent; cursor: pointer; transition: all 0.3s; }
        .platform-btn.active { border-color: #e94560; background: rgba(233, 69, 96, 0.2); }
        .platform-btn:hover { background: rgba(255,255,255,0.2); }
        .status { margin-top: 20px; padding: 15px; border-radius: 10px; text-align: center; }
        .status.loading { background: rgba(233, 69, 96, 0.2); }
        .status.success { background: rgba(0, 255, 136, 0.2); }
        .status.error { background: rgba(255, 0, 0, 0.2); }
        .download-link { display: inline-block; margin-top: 10px; padding: 10px 20px; background: #00ff88; color: #1a1a2e; border-radius: 8px; text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 UniDownloader</h1>
        <div class="input-group">
            <input type="text" id="url" placeholder="Paste video URL here (YouTube, Instagram, etc.)...">
            <button class="btn-primary" onclick="fetchInfo()">Preview</button>
        </div>
        
        <div id="preview" class="preview-section">
            <div class="video-info">
                <img id="thumbnail" class="thumbnail" src="" alt="Thumbnail">
                <div class="info">
                    <h3 id="title"></h3>
                    <p id="duration"></p>
                    <p id="channel"></p>
                </div>
            </div>
            
            <div class="time-controls">
                <div class="time-input">
                    <label>Start Time (HH:MM:SS)</label>
                    <input type="text" id="start_time" placeholder="00:00:00" value="00:00:00">
                </div>
                <div class="time-input">
                    <label>End Time (HH:MM:SS)</label>
                    <input type="text" id="end_time" placeholder="00:00:00">
                </div>
            </div>
            
            <div class="template-section">
                <h4>📝 Template Options</h4>
                
                <div class="template-input">
                    <label>Text (appears at top of video)</label>
                    <textarea id="overlay_text" placeholder="Enter your text here..."></textarea>
                </div>
                
                <div class="template-input">
                    <label>Platform</label>
                    <div class="platform-select">
                        <button class="platform-btn active" data-platform="instagram" onclick="selectPlatform(this)">📸 Instagram</button>
                        <button class="platform-btn" data-platform="twitter" onclick="selectPlatform(this)">𝕏 X/Twitter</button>
                        <button class="platform-btn" data-platform="facebook" onclick="selectPlatform(this)">📘 Facebook</button>
                        <button class="platform-btn" data-platform="youtube" onclick="selectPlatform(this)">▶️ YouTube</button>
                    </div>
                </div>
                
                <div class="template-input">
                    <label>Username (appears at bottom)</label>
                    <input type="text" id="username" placeholder="@username">
                </div>
                
                <button class="btn-primary" onclick="downloadVideo()" style="width: 100%; margin-top: 10px;">🎬 Download with Template</button>
            </div>
        </div>
        
        <div id="status" class="status" style="display:none;"></div>
    </div>

    <script>
        let videoInfo = null;
        let selectedPlatform = 'instagram';
        
        function selectPlatform(btn) {
            document.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedPlatform = btn.dataset.platform;
        }
        
        function formatDuration(seconds) {
            seconds = Math.floor(seconds);
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
        }
        
        async function fetchInfo() {
            const url = document.getElementById('url').value;
            if (!url) return alert('Please enter a URL');
            
            showStatus('Fetching video info...', 'loading');
            
            try {
                const res = await fetch(`/info?url=${encodeURIComponent(url)}`);
                if (!res.ok) throw new Error('Failed to fetch info');
                videoInfo = await res.json();
                
                document.getElementById('thumbnail').src = videoInfo.thumbnail;
                document.getElementById('title').textContent = videoInfo.title;
                document.getElementById('duration').textContent = `Duration: ${formatDuration(videoInfo.duration)}`;
                document.getElementById('channel').textContent = `Channel: ${videoInfo.channel}`;
                document.getElementById('end_time').value = formatDuration(videoInfo.duration);
                
                document.getElementById('preview').classList.add('active');
                hideStatus();
            } catch (e) {
                showStatus('Error: ' + e.message, 'error');
            }
        }
        
        async function downloadVideo() {
            const url = document.getElementById('url').value;
            const startTime = document.getElementById('start_time').value;
            const endTime = document.getElementById('end_time').value;
            const overlayText = document.getElementById('overlay_text').value;
            const username = document.getElementById('username').value;
            
            showStatus('Processing video with template... This may take a while.', 'loading');
            
            try {
                const params = new URLSearchParams({ 
                    url, 
                    start_time: startTime, 
                    end_time: endTime,
                    overlay_text: overlayText,
                    username: username,
                    platform: selectedPlatform
                });
                const res = await fetch(`/download?${params}`, { method: 'POST' });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Download failed');
                }
                const data = await res.json();
                showStatus(`Processed: ${data.title}`, 'success');
                document.getElementById('status').innerHTML += `<br><a class="download-link" href="/file/${data.file}" download>⬇️ Download File</a>`;
            } catch (e) {
                showStatus('Error: ' + e.message, 'error');
            }
        }
        
        function showStatus(msg, type) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.className = 'status ' + type;
            el.style.display = 'block';
        }
        
        function hideStatus() {
            document.getElementById('status').style.display = 'none';
        }
    </script>
</body>
</html>
"""


@app.get("/info")
def get_video_info(url: str):
    """Fetch video metadata without downloading"""
    ydl_opts = {
        "noplaylist": True,
        "skip_download": True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title"),
                "duration": int(info.get("duration", 0) or 0),
                "thumbnail": info.get("thumbnail"),
                "channel": info.get("channel") or info.get("uploader"),
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def time_to_seconds(t):
    """Convert HH:MM:SS to seconds"""
    if not t:
        return None
    parts = t.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(parts[0])


def create_template_video(input_path: str, output_path: str, overlay_text: str, username: str, platform: str):
    """Create a video with text overlay at top and username at bottom using ffmpeg"""
    
    # Get video info using ffprobe
    probe_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
                 '-show_entries', 'stream=width,height,duration', '-of', 'csv=p=0', input_path]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    parts = result.stdout.strip().split(',')
    width, height = int(parts[0]), int(parts[1])
    
    # Calculate template dimensions (9:16 aspect ratio for vertical video)
    template_width = 1080
    template_height = 1920
    
    # Calculate section heights
    text_section_height = int(template_height * 0.30)   # 30% for top text
    video_section_height = int(template_height * 0.55)  # 55% for video
    username_section_height = int(template_height * 0.15)  # 15% for username
    
    # Scale video to fit the video section while maintaining aspect ratio
    scale_factor = min(template_width / width, video_section_height / height)
    scaled_width = int(width * scale_factor)
    scaled_height = int(height * scale_factor)
    
    # Center the video
    video_x = (template_width - scaled_width) // 2
    video_y = text_section_height + (video_section_height - scaled_height) // 2
    
    # Escape text for ffmpeg drawtext filter
    def escape_text(text):
        # Escape special characters for ffmpeg drawtext
        return text.replace("\\", "\\\\").replace("'", "'\\''").replace(":", "\\:").replace("%", "\\%")
    
    safe_text = escape_text(overlay_text) if overlay_text else ""
    safe_username = escape_text(username) if username else ""
    
    # Platform prefix
    platform_prefix = {
        "instagram": "@",
        "twitter": "@", 
        "facebook": "",
        "youtube": "@"
    }
    prefix = platform_prefix.get(platform, "@")
    if safe_username and not safe_username.startswith("@"):
        safe_username = f"{prefix}{safe_username}"
    
    # Calculate auto font size based on text length
    # For top text: auto-adjust based on character count and available width
    text_len = len(overlay_text) if overlay_text else 0
    max_width = template_width - 60  # 30px padding on each side
    
    # Calculate font size - larger for short text, smaller for long text
    if text_len <= 20:
        text_fontsize = 72
    elif text_len <= 50:
        text_fontsize = 56
    elif text_len <= 100:
        text_fontsize = 44
    elif text_len <= 200:
        text_fontsize = 36
    else:
        text_fontsize = 28
    
    # Calculate how many characters fit per line (approximate)
    chars_per_line = int(max_width / (text_fontsize * 0.5))
    
    # Split text into multiple lines if needed
    if overlay_text and len(overlay_text) > chars_per_line:
        words = overlay_text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= chars_per_line:
                current_line = f"{current_line} {word}".strip()
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        # Limit to max lines that fit in text section
        max_lines = int(text_section_height / (text_fontsize * 1.3))
        lines = lines[:max(max_lines, 3)]
        
        # If still too many lines, reduce font size further
        if len(lines) > max_lines:
            text_fontsize = max(24, int(text_fontsize * 0.8))
    else:
        lines = [overlay_text] if overlay_text else [""]
    
    # Build drawtext filters for each line
    line_height = int(text_fontsize * 1.3)
    total_text_height = len(lines) * line_height
    start_y = (text_section_height - total_text_height) // 2
    
    # Build filter complex with multiple text lines
    filter_parts = [
        f"color=black:{template_width}x{template_height}:d=999[bg]",
        f"[0:v]scale={scaled_width}:{scaled_height}[scaled]",
        f"[bg][scaled]overlay={video_x}:{video_y}:shortest=1[v1]"
    ]
    
    current_input = "v1"
    for i, line in enumerate(lines):
        safe_line = escape_text(line)
        y_pos = start_y + (i * line_height)
        output_label = f"vtext{i}"
        filter_parts.append(
            f"[{current_input}]drawtext=text='{safe_line}':fontsize={text_fontsize}:fontcolor=white:x=(w-text_w)/2:y={y_pos}:font=Sans[{output_label}]"
        )
        current_input = output_label
    
    # Add username at bottom
    username_y = text_section_height + video_section_height + (username_section_height // 3)
    filter_parts.append(
        f"[{current_input}]drawtext=text='{safe_username}':fontsize=44:fontcolor=white:x=(w-text_w)/2:y={username_y}:font=Sans[vout]"
    )
    
    filter_complex = ";".join(filter_parts)
    
    # Build ffmpeg command
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-filter_complex', filter_complex,
        '-map', '[vout]',
        '-map', '0:a?',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ]
    
    # Run ffmpeg
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")
    
    return output_path


@app.post("/download")
def download_video(
    url: str,
    start_time: str = Query(default="00:00:00"),
    end_time: str = Query(default=None),
    overlay_text: str = Query(default=""),
    username: str = Query(default=""),
    platform: str = Query(default="instagram")
):
    """Download video with optional time range and template overlay"""
    file_id = str(uuid.uuid4())
    raw_file = os.path.join(DOWNLOAD_DIR, f"{file_id}_raw.mp4")
    final_file = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

    ydl_opts = {
        "outtmpl": raw_file.replace('.mp4', '.%(ext)s'),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "noplaylist": True,
        "merge_output_format": "mp4",
    }
    
    start_sec = time_to_seconds(start_time)
    end_sec = time_to_seconds(end_time)
    
    # Add time range if specified
    if start_sec > 0 or end_sec:
        ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)])
        ydl_opts["force_keyframes_at_cuts"] = True

    try:
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")
        
        # Find the downloaded file
        raw_file = raw_file.replace('.mp4', f'.{info.get("ext", "mp4")}')
        if not os.path.exists(raw_file):
            # Try to find the file
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(f"{file_id}_raw"):
                    raw_file = os.path.join(DOWNLOAD_DIR, f)
                    break
        
        # Apply template if text or username provided
        if overlay_text or username:
            create_template_video(raw_file, final_file, overlay_text, username, platform)
            # Clean up raw file
            if os.path.exists(raw_file):
                os.remove(raw_file)
            return {"file": f"{file_id}.mp4", "title": title}
        else:
            # Just rename the file
            os.rename(raw_file, final_file)
            return {"file": f"{file_id}.mp4", "title": title}
            
    except Exception as e:
        # Clean up on error
        for f in [raw_file, final_file]:
            if os.path.exists(f):
                os.remove(f)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/file/{name}")
def get_file(name: str):
    # Prevent path traversal
    if ".." in name or "/" in name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = os.path.join(DOWNLOAD_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=name)
