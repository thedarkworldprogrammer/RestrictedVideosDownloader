import streamlit as st
import yt_dlp
import re
import os
import tempfile
import urllib.parse
from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Check agar URL mein ?player=1 hai (New Tab Full-Screen Player Mode)
query_params = st.query_params
is_player_mode = query_params.get("player") == "1"

st.set_page_config(
    page_title="HD Stream Player" if is_player_mode else "Universal Video Downloader",
    page_icon="🎬",
    layout="wide" if is_player_mode else "centered"
)

# ==========================================
# 1. FULL-SCREEN THEATER PLAYER MODE (NEW TAB)
# ==========================================
if is_player_mode:
    video_url = query_params.get("v", "")
    audio_url = query_params.get("a", "")
    video_title = query_params.get("t", "HD Stream Player")

    # Streamlit ke default header/padding ko chhupane ke liye CSS
    st.markdown("""
        <style>
            #MainMenu, header, footer {visibility: hidden;}
            .block-container {padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 1100px;}
        </style>
    """, unsafe_allow_html=True)

    st.subheader(f"🎬 {video_title}")

    if not video_url:
        st.error("Invalid stream link. Kripya wapas ja kar dobara Stream button par click karein.")
    else:
        has_audio_track = bool(audio_url)
        audio_tag = f'<audio id="aud" preload="auto"><source src="{audio_url}" type="audio/mp4"></audio>' if has_audio_track else ''

        custom_player_html = f"""
        <div id="player-wrapper" style="background:#0f0f0f; border-radius:12px; overflow:hidden; box-shadow:0 8px 30px rgba(0,0,0,0.6); font-family: sans-serif; color: #fff;">
            <!-- Video Container (Responsive, No Cropping) -->
            <div style="position:relative; width:100%; background:#000; display:flex; justify-content:center; align-items:center;">
                <video id="vid" style="width:100%; max-height:75vh; object-fit:contain; cursor:pointer;" autoplay playsinline>
                    <source src="{video_url}" type="video/mp4">
                </video>
                {audio_tag}
            </div>

            <!-- Custom Controls & Timeline Bar -->
            <div style="padding: 12px 16px; background: #181818;">
                <!-- Timeline Seekbar -->
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                    <span id="curr-time" style="font-size:13px; min-width:45px;">00:00</span>
                    <input type="range" id="seekbar" value="0" min="0" max="100" step="0.1" 
                           style="flex:1; accent-color:#ff4b4b; cursor:pointer; height:6px;">
                    <span id="dur-time" style="font-size:13px; min-width:45px; text-align:right;">00:00</span>
                </div>

                <!-- Buttons Row -->
                <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <button onclick="skip(-10)" style="background:#2a2a2a; color:#fff; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; font-weight:bold;">⏪ 10s</button>
                        <button id="play-btn" onclick="togglePlay()" style="background:#ff4b4b; color:#fff; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold;">⏸ Pause</button>
                        <button onclick="skip(10)" style="background:#2a2a2a; color:#fff; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; font-weight:bold;">10s ⏩</button>
                    </div>

                    <div style="display:flex; align-items:center; gap:12px;">
                        <!-- Volume -->
                        <div style="display:flex; align-items:center; gap:5px;">
                            <span style="font-size:14px;">🔊</span>
                            <input type="range" id="vol-slider" min="0" max="1" step="0.05" value="1" style="width:80px; accent-color:#ff4b4b; cursor:pointer;">
                        </div>

                        <!-- Speed -->
                        <select id="speed-select" onchange="changeSpeed(this.value)" style="background:#2a2a2a; color:#fff; border:none; padding:6px 8px; border-radius:6px; cursor:pointer;">
                            <option value="0.75">0.75x</option>
                            <option value="1" selected>1.0x</option>
                            <option value="1.25">1.25x</option>
                            <option value="1.5">1.5x</option>
                            <option value="2">2.0x</option>
                        </select>

                        <!-- Fullscreen -->
                        <button onclick="toggleFull()" style="background:#2a2a2a; color:#fff; border:none; padding:8px 12px; border-radius:6px; cursor:pointer;">⛶ Fullscreen</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const v = document.getElementById('vid');
            const a = document.getElementById('aud');
            const seekbar = document.getElementById('seekbar');
            const currTimeEl = document.getElementById('curr-time');
            const durTimeEl = document.getElementById('dur-time');
            const playBtn = document.getElementById('play-btn');
            const volSlider = document.getElementById('vol-slider');
            const wrapper = document.getElementById('player-wrapper');

            function formatTime(sec) {{
                if (isNaN(sec)) return "00:00";
                const m = Math.floor(sec / 60);
                const s = Math.floor(sec % 60);
                return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
            }}

            function togglePlay() {{
                if (v.paused) {{
                    v.play();
                }} else {{
                    v.play();
                }}
            }}

            function skip(seconds) {{
                v.currentTime = Math.max(0, Math.min(v.duration || 0, v.currentTime + seconds));
                if (a) a.currentTime = v.currentTime;
            }}

            function changeSpeed(rate) {{
                v.playbackRate = parseFloat(rate);
                if (a) a.playbackRate = parseFloat(rate);
            }}

            function toggleFull() {{
                if (!document.fullscreenElement) {{
                    wrapper.requestFullscreen().catch(err => console.log(err));
                }} else {{
                    document.exitFullscreen();
                }}
            }}

            v.onclick = togglePlay;

            v.onplay = () => {{
                playBtn.innerText = "⏸ Pause";
                if (a) {{
                    a.currentTime = v.currentTime;
                    a.play().catch(e => console.log("Audio autoplay blocked:", e));
                }}
            }};

            v.onpause = () => {{
                playBtn.innerText = "▶️ Play";
                if (a) a.pause();
            }};

            v.onwaiting = () => {{ if (a) a.pause(); }};
            v.onplaying = () => {{ if (a) {{ a.currentTime = v.currentTime; a.play(); }} }};

            v.ontimeupdate = () => {{
                if (v.duration) {{
                    seekbar.max = v.duration;
                    seekbar.value = v.currentTime;
                    currTimeEl.innerText = formatTime(v.currentTime);
                    durTimeEl.innerText = formatTime(v.duration);
                }}
                // Drift correction agar audio 0.3s se zyada aage/peeche ho
                if (a && Math.abs(v.currentTime - a.currentTime) > 0.3) {{
                    a.currentTime = v.currentTime;
                }}
            }};

            seekbar.oninput = () => {{
                v.currentTime = seekbar.value;
                if (a) a.currentTime = seekbar.value;
            }};

            volSlider.oninput = () => {{
                if (a) {{
                    a.volume = volSlider.value;
                    v.muted = true;
                }} else {{
                    v.volume = volSlider.value;
                }}
            }};

            // Keyboard Shortcuts (Space, Left/Right Arrows)
            document.addEventListener('keydown', (e) => {{
                if (e.code === 'Space') {{ e.preventDefault(); togglePlay(); }}
                if (e.code === 'ArrowRight') skip(10);
                if (e.code === 'ArrowLeft') skip(-10);
            }});
        </script>
        """
        st.components.v1.html(custom_player_html, height=720)
    st.stop()


# ==========================================
# 2. MAIN DOWNLOADER & EXTRACTOR PAGE
# ==========================================
if "video_data" not in st.session_state:
    st.session_state.video_data = None
if "prepared_file" not in st.session_state:
    st.session_state.prepared_file = None

def format_filesize(size_bytes):
    if not size_bytes:
        return "Unknown Size"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80] or "video"

def extract_hqporner_formats(url):
    session = requests.Session(impersonate="chrome")
    resp = session.get(url, timeout=15)
    bs = BeautifulSoup(resp.text, 'html.parser')

    if resp.status_code == 404 or "Oops, page not found!" in resp.text or bs.find_all('section', {'class': 'box highlight'}):
        slug = url.split("/")[-1].replace(".html", "")
        clean_query = re.sub(r'^\d+-', '', slug).replace("_", "+").replace("-", "+")
        search_resp = session.get(f"https://hqporner.com/?q={clean_query}", timeout=15)
        search_bs = BeautifulSoup(search_resp.text, 'html.parser')
        video_links = search_bs.find_all('a', href=re.compile(r'/hdporn/\d+-'))
        if not video_links:
            raise Exception("Video nahi mila.")
        url = urljoin("https://hqporner.com/", video_links[0]['href'])
        resp = session.get(url, timeout=15)
        bs = BeautifulSoup(resp.text, 'html.parser')

    h1 = bs.find('h1', {'class': 'main-h1'})
    title = h1.get_text().strip() if h1 else "HQPorner Video"

    iframe = bs.find('iframe', {'src': re.compile(r"mydaddy\.cc")})
    if not iframe:
        raise Exception("Video player nahi mila.")
    
    iframe_url = iframe['src']
    if iframe_url.startswith("//"):
        iframe_url = "https:" + iframe_url

    player_resp = session.get(iframe_url, headers={"Referer": url}, timeout=15)
    mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+/(?:1080|720|480|360)\.mp4(?:\?[^"\'\s<>]*)?', player_resp.text)
    
    if not mp4_links:
        raise Exception("Direct MP4 links nahi mile.")

    formats = []
    seen_urls = set()
    for link in mp4_links:
        full_link = ("https:" + link) if link.startswith("//") else link
        if full_link in seen_urls:
            continue
        seen_urls.add(full_link)
        
        res = "HD"
        for q in ["1080", "720", "480", "360"]:
            if q in full_link:
                res = f"{q}p"
                break
        
        formats.append({
            "format_id": res,
            "label": f"{res} | .mp4 | Video + Audio",
            "type": "Video + Audio",
            "ext": "mp4",
            "resolution": res,
            "url": full_link,
            "audio_url": "",
            "referer": iframe_url,
            "needs_merge": False
        })

    return {
        "title": title,
        "thumbnail": None,
        "uploader": "HQPorner",
        "source_url": url,
        "is_hqporner": True,
        "formats": formats
    }

def extract_universal_formats(url):
    if "hqporner.com" in url:
        return extract_hqporner_formats(url)

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'nocheckcertificate': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        formats_list = []
        raw_formats = info.get('formats', [])

        audio_formats = [f for f in raw_formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('url')]
        best_audio = audio_formats[-1] if audio_formats else None

        for f in reversed(raw_formats):
            direct_url = f.get('url')
            format_id = f.get('format_id')
            if not direct_url or not format_id:
                continue

            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            ext = f.get('ext', 'mp4')
            height = f.get('height')
            fps = f.get('fps')
            filesize = f.get('filesize') or f.get('filesize_approx')

            res_str = f"{height}p" if height else "Unknown"
            fps_str = f" {int(fps)}fps" if fps and fps > 30 else ""
            size_str = format_filesize(filesize)

            # Case 1: Already Video + Audio
            if vcodec != 'none' and acodec != 'none':
                formats_list.append({
                    "format_id": format_id,
                    "label": f"{res_str}{fps_str} | .{ext} | Video + Audio ({size_str})",
                    "type": "Video + Audio",
                    "ext": ext,
                    "resolution": res_str,
                    "url": direct_url,
                    "audio_url": "",
                    "referer": url,
                    "needs_merge": False
                })

            # Case 2: Video Only (HD/4K) -> Merged + Mute dono options
            elif vcodec != 'none' and acodec == 'none':
                if best_audio:
                    merged_id = f"{format_id}+{best_audio['format_id']}"
                    formats_list.append({
                        "format_id": merged_id,
                        "label": f"{res_str}{fps_str} | .mp4 | Video + Audio (Merged) ({size_str}+)",
                        "type": "Video + Audio",
                        "ext": "mp4",
                        "resolution": res_str,
                        "url": direct_url,
                        "audio_url": best_audio['url'],
                        "referer": url,
                        "needs_merge": True
                    })

                formats_list.append({
                    "format_id": format_id,
                    "label": f"{res_str}{fps_str} | .{ext} | Video Only (Mute) ({size_str})",
                    "type": "Video Only (Mute)",
                    "ext": ext,
                    "resolution": res_str,
                    "url": direct_url,
                    "audio_url": "",
                    "referer": url,
                    "needs_merge": False
                })

            # Case 3: Audio Only
            elif vcodec == 'none' and acodec != 'none':
                abr = f.get('abr')
                bitrate_str = f"{int(abr)}kbps" if abr else "Audio"
                formats_list.append({
                    "format_id": format_id,
                    "label": f"{bitrate_str} | .{ext} | Audio Only ({size_str})",
                    "type": "Audio Only",
                    "ext": ext,
                    "resolution": bitrate_str,
                    "url": direct_url,
                    "audio_url": "",
                    "referer": url,
                    "needs_merge": False
                })

        return {
            "title": info.get('title', 'Extracted Video'),
            "thumbnail": info.get('thumbnail'),
            "uploader": info.get('uploader') or info.get('extractor_key', 'Web'),
            "source_url": url,
            "is_hqporner": False,
            "formats": formats_list
        }

def fetch_video_bytes(data, selected_fmt):
    filename = f"{sanitize_filename(data['title'])}_{selected_fmt['resolution']}.{selected_fmt['ext']}"
    
    if data.get("is_hqporner"):
        session = requests.Session(impersonate="chrome")
        resp = session.get(selected_fmt["url"], headers={"Referer": selected_fmt["referer"]}, timeout=120)
        resp.raise_for_status()
        return resp.content, filename
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_template = os.path.join(tmpdir, "download.%(ext)s")
            ydl_opts = {
                'format': selected_fmt['format_id'],
                'outtmpl': out_template,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['tv', 'web_safari', 'android', 'web'],
                    }
                }
            }
            if selected_fmt.get("needs_merge"):
                ydl_opts['merge_output_format'] = 'mp4'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([data["source_url"]])
            
            downloaded_files = os.listdir(tmpdir)
            if not downloaded_files:
                raise Exception("File download nahi ho payi.")
            
            filepath = os.path.join(tmpdir, downloaded_files[0])
            with open(filepath, "rb") as f:
                return f.read(), filename

# --- UI Layout ---
st.title("🎬 Universal Video Downloader")
st.write("YouTube, Instagram, X (Twitter), Reddit, Vimeo, Eporner, HQPorner aur 1000+ sites ke videos **With Audio**, **Mute**, ya **Audio Only** format mein download ya stream karein.")

url_input = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🔍 Fetch Available Formats", type="primary"):
    if not url_input.strip():
        st.warning("Kripya pehle ek valid URL paste karein.")
    else:
        with st.spinner("Video details aur formats scan kiye ja rahe hain..."):
            try:
                st.session_state.video_data = extract_universal_formats(url_input.strip())
                st.session_state.prepared_file = None
            except Exception as e:
                st.session_state.video_data = None
                st.session_state.prepared_file = None
                st.error(f"Error: {str(e)}")

# --- Results & Format Filter Section ---
if st.session_state.video_data:
    data = st.session_state.video_data
    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        if data["thumbnail"]:
            st.image(data["thumbnail"], use_container_width=True)
    with col2:
        st.subheader(data["title"])
        st.caption(f"Source / Uploader: {data['uploader']}")

    all_formats = data["formats"]
    if not all_formats:
        st.warning("Is video ke liye koi direct downloadable format nahi mila.")
    else:
        st.markdown("### 🎛️ Format Filter karein")
        
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            unique_types = list(dict.fromkeys(f["type"] for f in all_formats))
            available_types = ["All"] + unique_types
            default_idx = available_types.index("Video + Audio") if "Video + Audio" in available_types else 0
            selected_type = st.selectbox("Stream Type chunein:", available_types, index=default_idx)
            
        with f_col2:
            available_exts = ["All"] + sorted(list(set(f["ext"] for f in all_formats)))
            selected_ext = st.selectbox("File Format (.ext) chunein:", available_exts)

        filtered_formats = [
            f for f in all_formats
            if (selected_type == "All" or f["type"] == selected_type)
            and (selected_ext == "All" or f["ext"] == selected_ext)
        ]

        if not filtered_formats:
            st.info("Is filter combination ke liye koi format available nahi hai.")
        else:
            st.success(f"{len(filtered_formats)} formats available hain:")
            
            format_map = {f["label"]: f for f in filtered_formats}
            chosen_label = st.selectbox("Quality select karein:", list(format_map.keys()))
            selected_fmt = format_map[chosen_label]

            # --- Side-by-Side Action Buttons ---
            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                if st.session_state.prepared_file and st.session_state.prepared_file["label"] == chosen_label:
                    st.download_button(
                        label=f"⬇️ Save File ({st.session_state.prepared_file['name'][:18]}...)",
                        data=st.session_state.prepared_file["bytes"],
                        file_name=st.session_state.prepared_file["name"],
                        mime="application/octet-stream",
                        type="primary",
                        use_container_width=True
                    )
                else:
                    if st.button("⬇️ Direct Download", type="primary", use_container_width=True):
                        with st.spinner("Video aur Audio fetch/merge ho rahe hain..."):
                            try:
                                file_bytes, file_name = fetch_video_bytes(data, selected_fmt)
                                st.session_state.prepared_file = {
                                    "bytes": file_bytes,
                                    "name": file_name,
                                    "label": chosen_label
                                }
                                st.rerun()
                            except Exception as e:
                                st.error(f"Download error: {str(e)}")

            with btn_col2:
                # New Tab mein Custom Player kholne ke liye URL generate karein
                if selected_fmt.get("needs_merge") and selected_fmt.get("audio_url"):
                    params = urllib.parse.urlencode({
                        "player": "1",
                        "v": selected_fmt["url"],
                        "a": selected_fmt["audio_url"],
                        "t": f"{data['title']} ({selected_fmt['resolution']})"
                    })
                    stream_page_url = f"?{params}"
                else:
                    # HQPorner ya pre-merged formats ke liye bhi custom player ya direct link
                    params = urllib.parse.urlencode({
                        "player": "1",
                        "v": selected_fmt["url"],
                        "t": f"{data['title']} ({selected_fmt['resolution']})"
                    })
                    stream_page_url = f"?{params}"

                st.link_button(
                    label="▶️ Stream in New Tab",
                    url=stream_page_url,
                    use_container_width=True
                )















# import streamlit as st
# import yt_dlp
# import re
# import os
# import tempfile
# from curl_cffi import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin

# # Page Configuration
# st.set_page_config(page_title="Universal Video Downloader", page_icon="🎬", layout="centered")

# # Session State initialization
# if "video_data" not in st.session_state:
#     st.session_state.video_data = None
# if "prepared_file" not in st.session_state:
#     st.session_state.prepared_file = None
# if "stream_active" not in st.session_state:
#     st.session_state.stream_active = False

# def format_filesize(size_bytes):
#     if not size_bytes:
#         return "Unknown Size"
#     for unit in ['B', 'KB', 'MB', 'GB']:
#         if size_bytes < 1024:
#             return f"{size_bytes:.1f} {unit}"
#         size_bytes /= 1024
#     return f"{size_bytes:.1f} TB"

# def sanitize_filename(name):
#     return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80] or "video"

# def extract_hqporner_formats(url):
#     session = requests.Session(impersonate="chrome")
#     resp = session.get(url, timeout=15)
#     bs = BeautifulSoup(resp.text, 'html.parser')

#     if resp.status_code == 404 or "Oops, page not found!" in resp.text or bs.find_all('section', {'class': 'box highlight'}):
#         slug = url.split("/")[-1].replace(".html", "")
#         clean_query = re.sub(r'^\d+-', '', slug).replace("_", "+").replace("-", "+")
#         search_resp = session.get(f"https://hqporner.com/?q={clean_query}", timeout=15)
#         search_bs = BeautifulSoup(search_resp.text, 'html.parser')
#         video_links = search_bs.find_all('a', href=re.compile(r'/hdporn/\d+-'))
#         if not video_links:
#             raise Exception("Video nahi mila.")
#         url = urljoin("https://hqporner.com/", video_links[0]['href'])
#         resp = session.get(url, timeout=15)
#         bs = BeautifulSoup(resp.text, 'html.parser')

#     h1 = bs.find('h1', {'class': 'main-h1'})
#     title = h1.get_text().strip() if h1 else "HQPorner Video"

#     iframe = bs.find('iframe', {'src': re.compile(r"mydaddy\.cc")})
#     if not iframe:
#         raise Exception("Video player nahi mila.")
    
#     iframe_url = iframe['src']
#     if iframe_url.startswith("//"):
#         iframe_url = "https:" + iframe_url

#     player_resp = session.get(iframe_url, headers={"Referer": url}, timeout=15)
#     mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+/(?:1080|720|480|360)\.mp4(?:\?[^"\'\s<>]*)?', player_resp.text)
    
#     if not mp4_links:
#         raise Exception("Direct MP4 links nahi mile.")

#     formats = []
#     seen_urls = set()
#     for link in mp4_links:
#         full_link = ("https:" + link) if link.startswith("//") else link
#         if full_link in seen_urls:
#             continue
#         seen_urls.add(full_link)
        
#         res = "HD"
#         for q in ["1080", "720", "480", "360"]:
#             if q in full_link:
#                 res = f"{q}p"
#                 break
        
#         formats.append({
#             "format_id": res,
#             "label": f"{res} | .mp4 | Video + Audio",
#             "type": "Video + Audio",
#             "ext": "mp4",
#             "resolution": res,
#             "url": full_link,
#             "referer": iframe_url,
#             "needs_merge": False
#         })

#     return {
#         "title": title,
#         "thumbnail": None,
#         "uploader": "HQPorner",
#         "source_url": url,
#         "is_hqporner": True,
#         "formats": formats
#     }

# def extract_universal_formats(url):
#     if "hqporner.com" in url:
#         return extract_hqporner_formats(url)

#     ydl_opts = {
#         'quiet': True,
#         'no_warnings': True,
#         'noplaylist': True,
#         'nocheckcertificate': True,
#     }

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         info = ydl.extract_info(url, download=False)
        
#         formats_list = []
#         raw_formats = info.get('formats', [])

#         audio_formats = [f for f in raw_formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('url')]
#         best_audio = audio_formats[-1] if audio_formats else None

#         for f in reversed(raw_formats):
#             direct_url = f.get('url')
#             format_id = f.get('format_id')
#             if not direct_url or not format_id:
#                 continue

#             vcodec = f.get('vcodec', 'none')
#             acodec = f.get('acodec', 'none')
#             ext = f.get('ext', 'mp4')
#             height = f.get('height')
#             fps = f.get('fps')
#             filesize = f.get('filesize') or f.get('filesize_approx')

#             res_str = f"{height}p" if height else "Unknown"
#             fps_str = f" {int(fps)}fps" if fps and fps > 30 else ""
#             size_str = format_filesize(filesize)

#             # Case 1: Already Video + Audio
#             if vcodec != 'none' and acodec != 'none':
#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{res_str}{fps_str} | .{ext} | Video + Audio ({size_str})",
#                     "type": "Video + Audio",
#                     "ext": ext,
#                     "resolution": res_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#             # Case 2: Video Only (HD/4K) -> Merged + Mute dono options
#             elif vcodec != 'none' and acodec == 'none':
#                 if best_audio:
#                     merged_id = f"{format_id}+{best_audio['format_id']}"
#                     formats_list.append({
#                         "format_id": merged_id,
#                         "label": f"{res_str}{fps_str} | .mp4 | Video + Audio (Merged) ({size_str}+)",
#                         "type": "Video + Audio",
#                         "ext": "mp4",
#                         "resolution": res_str,
#                         "url": direct_url,
#                         "audio_url": best_audio['url'],
#                         "referer": url,
#                         "needs_merge": True
#                     })

#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{res_str}{fps_str} | .{ext} | Video Only (Mute) ({size_str})",
#                     "type": "Video Only (Mute)",
#                     "ext": ext,
#                     "resolution": res_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#             # Case 3: Audio Only
#             elif vcodec == 'none' and acodec != 'none':
#                 abr = f.get('abr')
#                 bitrate_str = f"{int(abr)}kbps" if abr else "Audio"
#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{bitrate_str} | .{ext} | Audio Only ({size_str})",
#                     "type": "Audio Only",
#                     "ext": ext,
#                     "resolution": bitrate_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#         return {
#             "title": info.get('title', 'Extracted Video'),
#             "thumbnail": info.get('thumbnail'),
#             "uploader": info.get('uploader') or info.get('extractor_key', 'Web'),
#             "source_url": url,
#             "is_hqporner": False,
#             "formats": formats_list
#         }

# def fetch_video_bytes(data, selected_fmt):
#     """Video ko fetch karke direct download ke liye bytes return karta hai"""
#     filename = f"{sanitize_filename(data['title'])}_{selected_fmt['resolution']}.{selected_fmt['ext']}"
    
#     if data.get("is_hqporner"):
#         session = requests.Session(impersonate="chrome")
#         resp = session.get(selected_fmt["url"], headers={"Referer": selected_fmt["referer"]}, timeout=120)
#         resp.raise_for_status()
#         return resp.content, filename
#     else:
#         with tempfile.TemporaryDirectory() as tmpdir:
#             out_template = os.path.join(tmpdir, "download.%(ext)s")
#             ydl_opts = {
#                 'format': selected_fmt['format_id'],
#                 'outtmpl': out_template,
#                 'quiet': True,
#                 'no_warnings': True,
#                 'nocheckcertificate': True,
#                 'extractor_args': {
#                     'youtube': {
#                         'player_client': ['tv', 'web_safari', 'android', 'web'],
#                     }
#                 }
#             }
#             if selected_fmt.get("needs_merge"):
#                 ydl_opts['merge_output_format'] = 'mp4'

#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 ydl.download([data["source_url"]])
            
#             downloaded_files = os.listdir(tmpdir)
#             if not downloaded_files:
#                 raise Exception("File download nahi ho payi.")
            
#             filepath = os.path.join(tmpdir, downloaded_files[0])
#             with open(filepath, "rb") as f:
#                 return f.read(), filename

# # --- UI Layout ---
# st.title("🎬 Universal Video Downloader")
# st.write("YouTube, Instagram, X (Twitter), Reddit, Vimeo, Eporner, HQPorner aur 1000+ sites ke videos **With Audio**, **Mute**, ya **Audio Only** format mein download ya stream karein.")

# url_input = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

# if st.button("🔍 Fetch Available Formats", type="primary"):
#     if not url_input.strip():
#         st.warning("Kripya pehle ek valid URL paste karein.")
#     else:
#         with st.spinner("Video details aur formats scan kiye ja rahe hain..."):
#             try:
#                 st.session_state.video_data = extract_universal_formats(url_input.strip())
#                 st.session_state.prepared_file = None
#                 st.session_state.stream_active = False
#             except Exception as e:
#                 st.session_state.video_data = None
#                 st.session_state.prepared_file = None
#                 st.session_state.stream_active = False
#                 st.error(f"Error: {str(e)}")

# # --- Results & Format Filter Section ---
# if st.session_state.video_data:
#     data = st.session_state.video_data
#     st.divider()

#     col1, col2 = st.columns([1, 2])
#     with col1:
#         if data["thumbnail"]:
#             st.image(data["thumbnail"], use_container_width=True)
#     with col2:
#         st.subheader(data["title"])
#         st.caption(f"Source / Uploader: {data['uploader']}")

#     all_formats = data["formats"]
#     if not all_formats:
#         st.warning("Is video ke liye koi direct downloadable format nahi mila.")
#     else:
#         st.markdown("### 🎛️ Format Filter karein")
        
#         f_col1, f_col2 = st.columns(2)
#         with f_col1:
#             unique_types = list(dict.fromkeys(f["type"] for f in all_formats))
#             available_types = ["All"] + unique_types
#             default_idx = available_types.index("Video + Audio") if "Video + Audio" in available_types else 0
#             selected_type = st.selectbox("Stream Type chunein:", available_types, index=default_idx)
            
#         with f_col2:
#             available_exts = ["All"] + sorted(list(set(f["ext"] for f in all_formats)))
#             selected_ext = st.selectbox("File Format (.ext) chunein:", available_exts)

#         filtered_formats = [
#             f for f in all_formats
#             if (selected_type == "All" or f["type"] == selected_type)
#             and (selected_ext == "All" or f["ext"] == selected_ext)
#         ]

#         if not filtered_formats:
#             st.info("Is filter combination ke liye koi format available nahi hai.")
#         else:
#             st.success(f"{len(filtered_formats)} formats available hain:")
            
#             format_map = {f["label"]: f for f in filtered_formats}
#             chosen_label = st.selectbox("Quality select karein:", list(format_map.keys()))
#             selected_fmt = format_map[chosen_label]

#             if selected_fmt.get("needs_merge"):
#                 st.caption("ℹ️ Note: Direct Download par click karne par HD Video aur Best Audio automatically merge hokar ek single MP4 file banenge.")

#             # --- Side-by-Side Action Buttons ---
#             btn_col1, btn_col2 = st.columns(2)

#             with btn_col1:
#                 if st.session_state.prepared_file and st.session_state.prepared_file["label"] == chosen_label:
#                     st.download_button(
#                         label=f"⬇️ Save File ({st.session_state.prepared_file['name'][:18]}...)",
#                         data=st.session_state.prepared_file["bytes"],
#                         file_name=st.session_state.prepared_file["name"],
#                         mime="application/octet-stream",
#                         type="primary",
#                         use_container_width=True
#                     )
#                 else:
#                     if st.button("⬇️ Direct Download", type="primary", use_container_width=True):
#                         with st.spinner("Video aur Audio fetch/merge ho rahe hain..."):
#                             try:
#                                 file_bytes, file_name = fetch_video_bytes(data, selected_fmt)
#                                 st.session_state.prepared_file = {
#                                     "bytes": file_bytes,
#                                     "name": file_name,
#                                     "label": chosen_label
#                                 }
#                                 st.rerun()
#                             except Exception as e:
#                                 st.error(f"Download error: {str(e)}")

#             with btn_col2:
#                 if selected_fmt.get("needs_merge") and selected_fmt.get("audio_url"):
#                     if st.button("▶️ Stream HD (With Audio)", use_container_width=True):
#                         st.session_state.stream_active = True
#                 else:
#                     st.link_button(
#                         label="▶️ Stream / Play",
#                         url=selected_fmt["url"],
#                         use_container_width=True
#                     )

#             # --- Synced Video + Audio Player (For HD Streams) ---
#             if st.session_state.get("stream_active") and selected_fmt.get("needs_merge"):
#                 st.markdown("#### 🎬 HD Stream Player (Video + Audio Synced)")
#                 player_html = f"""
#                 <div style="background:#000; border-radius:10px; overflow:hidden;">
#                     <video id="vid" width="100%" controls autoplay playsinline>
#                         <source src="{selected_fmt['url']}" type="video/mp4">
#                     </video>
#                     <audio id="aud" preload="auto">
#                         <source src="{selected_fmt['audio_url']}" type="audio/mp4">
#                     </audio>
#                 </div>
#                 <script>
#                     const v = document.getElementById('vid');
#                     const a = document.getElementById('aud');
#                     v.onplay = () => {{ a.currentTime = v.currentTime; a.play(); }};
#                     v.onpause = () => a.pause();
#                     v.onseeking = () => {{ a.currentTime = v.currentTime; }};
#                     v.onvolumechange = () => {{ a.volume = v.volume; a.muted = v.muted; }};
#                     v.onratechange = () => {{ a.playbackRate = v.playbackRate; }};
#                 </script>
#                 """
#                 st.components.v1.html(player_html, height=420)














# import streamlit as st
# import yt_dlp
# import re
# import os
# import tempfile
# from curl_cffi import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin

# # Page Configuration
# st.set_page_config(page_title="Universal Video Downloader", page_icon="🎬", layout="centered")

# if "video_data" not in st.session_state:
#     st.session_state.video_data = None
# if "prepared_file" not in st.session_state:
#     st.session_state.prepared_file = None

# def format_filesize(size_bytes):
#     if not size_bytes:
#         return "Unknown Size"
#     for unit in ['B', 'KB', 'MB', 'GB']:
#         if size_bytes < 1024:
#             return f"{size_bytes:.1f} {unit}"
#         size_bytes /= 1024
#     return f"{size_bytes:.1f} TB"

# def sanitize_filename(name):
#     return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80] or "video"

# def extract_hqporner_formats(url):
#     session = requests.Session(impersonate="chrome")
#     resp = session.get(url, timeout=15)
#     bs = BeautifulSoup(resp.text, 'html.parser')

#     if resp.status_code == 404 or "Oops, page not found!" in resp.text or bs.find_all('section', {'class': 'box highlight'}):
#         slug = url.split("/")[-1].replace(".html", "")
#         clean_query = re.sub(r'^\d+-', '', slug).replace("_", "+").replace("-", "+")
#         search_resp = session.get(f"https://hqporner.com/?q={clean_query}", timeout=15)
#         search_bs = BeautifulSoup(search_resp.text, 'html.parser')
#         video_links = search_bs.find_all('a', href=re.compile(r'/hdporn/\d+-'))
#         if not video_links:
#             raise Exception("Video nahi mila.")
#         url = urljoin("https://hqporner.com/", video_links[0]['href'])
#         resp = session.get(url, timeout=15)
#         bs = BeautifulSoup(resp.text, 'html.parser')

#     h1 = bs.find('h1', {'class': 'main-h1'})
#     title = h1.get_text().strip() if h1 else "HQPorner Video"

#     iframe = bs.find('iframe', {'src': re.compile(r"mydaddy\.cc")})
#     if not iframe:
#         raise Exception("Video player nahi mila.")
    
#     iframe_url = iframe['src']
#     if iframe_url.startswith("//"):
#         iframe_url = "https:" + iframe_url

#     player_resp = session.get(iframe_url, headers={"Referer": url}, timeout=15)
#     mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+/(?:1080|720|480|360)\.mp4(?:\?[^"\'\s<>]*)?', player_resp.text)
    
#     if not mp4_links:
#         raise Exception("Direct MP4 links nahi mile.")

#     formats = []
#     seen_urls = set()
#     for link in mp4_links:
#         full_link = ("https:" + link) if link.startswith("//") else link
#         if full_link in seen_urls:
#             continue
#         seen_urls.add(full_link)
        
#         res = "HD"
#         for q in ["1080", "720", "480", "360"]:
#             if q in full_link:
#                 res = f"{q}p"
#                 break
        
#         formats.append({
#             "format_id": res,
#             "label": f"{res} | .mp4 | Video + Audio",
#             "type": "Video + Audio",
#             "ext": "mp4",
#             "resolution": res,
#             "url": full_link,
#             "referer": iframe_url,
#             "needs_merge": False
#         })

#     return {
#         "title": title,
#         "thumbnail": None,
#         "uploader": "HQPorner",
#         "source_url": url,
#         "is_hqporner": True,
#         "formats": formats
#     }

# def extract_universal_formats(url):
#     if "hqporner.com" in url:
#         return extract_hqporner_formats(url)

#     # Scan ke time default clients use karein taaki saare 4K, 1080p, 720p, Audio formats aayein
#     ydl_opts = {
#         'quiet': True,
#         'no_warnings': True,
#         'noplaylist': True,
#         'nocheckcertificate': True,
#     }

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         info = ydl.extract_info(url, download=False)
        
#         formats_list = []
#         raw_formats = info.get('formats', [])

#         audio_formats = [f for f in raw_formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('url')]
#         best_audio = audio_formats[-1] if audio_formats else None

#         for f in reversed(raw_formats):
#             direct_url = f.get('url')
#             format_id = f.get('format_id')
#             if not direct_url or not format_id:
#                 continue

#             vcodec = f.get('vcodec', 'none')
#             acodec = f.get('acodec', 'none')
#             ext = f.get('ext', 'mp4')
#             height = f.get('height')
#             fps = f.get('fps')
#             filesize = f.get('filesize') or f.get('filesize_approx')

#             res_str = f"{height}p" if height else "Unknown"
#             fps_str = f" {int(fps)}fps" if fps and fps > 30 else ""
#             size_str = format_filesize(filesize)

#             # Case 1: Already Video + Audio
#             if vcodec != 'none' and acodec != 'none':
#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{res_str}{fps_str} | .{ext} | Video + Audio ({size_str})",
#                     "type": "Video + Audio",
#                     "ext": ext,
#                     "resolution": res_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#             # Case 2: Video Only (HD/4K) -> Merged + Mute dono options
#             elif vcodec != 'none' and acodec == 'none':
#                 if best_audio:
#                     merged_id = f"{format_id}+{best_audio['format_id']}"
#                     formats_list.append({
#                         "format_id": merged_id,
#                         "label": f"{res_str}{fps_str} | .mp4 | Video + Audio (Merged) ({size_str}+)",
#                         "type": "Video + Audio",
#                         "ext": "mp4",
#                         "resolution": res_str,
#                         "url": direct_url,
#                         "referer": url,
#                         "needs_merge": True
#                     })

#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{res_str}{fps_str} | .{ext} | Video Only (Mute) ({size_str})",
#                     "type": "Video Only (Mute)",
#                     "ext": ext,
#                     "resolution": res_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#             # Case 3: Audio Only
#             elif vcodec == 'none' and acodec != 'none':
#                 abr = f.get('abr')
#                 bitrate_str = f"{int(abr)}kbps" if abr else "Audio"
#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{bitrate_str} | .{ext} | Audio Only ({size_str})",
#                     "type": "Audio Only",
#                     "ext": ext,
#                     "resolution": bitrate_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#         return {
#             "title": info.get('title', 'Extracted Video'),
#             "thumbnail": info.get('thumbnail'),
#             "uploader": info.get('uploader') or info.get('extractor_key', 'Web'),
#             "source_url": url,
#             "is_hqporner": False,
#             "formats": formats_list
#         }

# def fetch_video_bytes(data, selected_fmt):
#     """Video ko fetch karke direct download ke liye bytes return karta hai"""
#     filename = f"{sanitize_filename(data['title'])}_{selected_fmt['resolution']}.{selected_fmt['ext']}"
    
#     if data.get("is_hqporner"):
#         session = requests.Session(impersonate="chrome")
#         resp = session.get(selected_fmt["url"], headers={"Referer": selected_fmt["referer"]}, timeout=120)
#         resp.raise_for_status()
#         return resp.content, filename
#     else:
#         with tempfile.TemporaryDirectory() as tmpdir:
#             out_template = os.path.join(tmpdir, "download.%(ext)s")
#             ydl_opts = {
#                 'format': selected_fmt['format_id'],
#                 'outtmpl': out_template,
#                 'quiet': True,
#                 'no_warnings': True,
#                 'nocheckcertificate': True,
#                 # Download ke time tv/web_safari/android clients use karein taaki 403 error na aaye aur saare formats milein
#                 'extractor_args': {
#                     'youtube': {
#                         'player_client': ['tv', 'web_safari', 'android', 'web'],
#                     }
#                 }
#             }
#             if selected_fmt.get("needs_merge"):
#                 ydl_opts['merge_output_format'] = 'mp4'

#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 ydl.download([data["source_url"]])
            
#             downloaded_files = os.listdir(tmpdir)
#             if not downloaded_files:
#                 raise Exception("File download nahi ho payi.")
            
#             filepath = os.path.join(tmpdir, downloaded_files[0])
#             with open(filepath, "rb") as f:
#                 return f.read(), filename

# # --- UI Layout ---
# st.title("🎬 Universal Video Downloader")
# st.write("YouTube, Instagram, X (Twitter), Reddit, Vimeo, Eporner, HQPorner aur 1000+ sites ke videos **With Audio**, **Mute**, ya **Audio Only** format mein download ya stream karein.")

# url_input = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

# if st.button("🔍 Fetch Available Formats", type="primary"):
#     if not url_input.strip():
#         st.warning("Kripya pehle ek valid URL paste karein.")
#     else:
#         with st.spinner("Video details aur formats scan kiye ja rahe hain..."):
#             try:
#                 st.session_state.video_data = extract_universal_formats(url_input.strip())
#                 st.session_state.prepared_file = None
#             except Exception as e:
#                 st.session_state.video_data = None
#                 st.session_state.prepared_file = None
#                 st.error(f"Error: {str(e)}")

# # --- Results & Format Filter Section ---
# if st.session_state.video_data:
#     data = st.session_state.video_data
#     st.divider()

#     col1, col2 = st.columns([1, 2])
#     with col1:
#         if data["thumbnail"]:
#             st.image(data["thumbnail"], use_container_width=True)
#     with col2:
#         st.subheader(data["title"])
#         st.caption(f"Source / Uploader: {data['uploader']}")

#     all_formats = data["formats"]
#     if not all_formats:
#         st.warning("Is video ke liye koi direct downloadable format nahi mila.")
#     else:
#         st.markdown("### 🎛️ Format Filter karein")
        
#         f_col1, f_col2 = st.columns(2)
#         with f_col1:
#             unique_types = list(dict.fromkeys(f["type"] for f in all_formats))
#             available_types = ["All"] + unique_types
#             default_idx = available_types.index("Video + Audio") if "Video + Audio" in available_types else 0
#             selected_type = st.selectbox("Stream Type chunein:", available_types, index=default_idx)
            
#         with f_col2:
#             available_exts = ["All"] + sorted(list(set(f["ext"] for f in all_formats)))
#             selected_ext = st.selectbox("File Format (.ext) chunein:", available_exts)

#         filtered_formats = [
#             f for f in all_formats
#             if (selected_type == "All" or f["type"] == selected_type)
#             and (selected_ext == "All" or f["ext"] == selected_ext)
#         ]

#         if not filtered_formats:
#             st.info("Is filter combination ke liye koi format available nahi hai.")
#         else:
#             st.success(f"{len(filtered_formats)} formats available hain:")
            
#             format_map = {f["label"]: f for f in filtered_formats}
#             chosen_label = st.selectbox("Quality select karein:", list(format_map.keys()))
#             selected_fmt = format_map[chosen_label]

#             if selected_fmt.get("needs_merge"):
#                 st.caption("ℹ️ Note: Direct Download par click karne par HD Video aur Best Audio automatically merge hokar ek single MP4 file banenge.")

#             # --- Side-by-Side Action Buttons ---
#             btn_col1, btn_col2 = st.columns(2)

#             with btn_col1:
#                 if st.session_state.prepared_file and st.session_state.prepared_file["label"] == chosen_label:
#                     st.download_button(
#                         label=f"⬇️ Save File ({st.session_state.prepared_file['name'][:18]}...)",
#                         data=st.session_state.prepared_file["bytes"],
#                         file_name=st.session_state.prepared_file["name"],
#                         mime="application/octet-stream",
#                         type="primary",
#                         use_container_width=True
#                     )
#                 else:
#                     if st.button("⬇️ Direct Download", type="primary", use_container_width=True):
#                         with st.spinner("Video aur Audio fetch/merge ho rahe hain..."):
#                             try:
#                                 file_bytes, file_name = fetch_video_bytes(data, selected_fmt)
#                                 st.session_state.prepared_file = {
#                                     "bytes": file_bytes,
#                                     "name": file_name,
#                                     "label": chosen_label
#                                 }
#                                 st.rerun()
#                             except Exception as e:
#                                 st.error(f"Download error: {str(e)}")

#             with btn_col2:
#                 st.link_button(
#                     label="▶️ Stream / Play",
#                     url=selected_fmt["url"],
#                     use_container_width=True
#                 )












# import streamlit as st
# import yt_dlp
# import re
# import os
# import tempfile
# from curl_cffi import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin

# # Page Configuration
# st.set_page_config(page_title="Universal Video Downloader", page_icon="🎬", layout="centered")

# if "video_data" not in st.session_state:
#     st.session_state.video_data = None
# if "prepared_file" not in st.session_state:
#     st.session_state.prepared_file = None

# def format_filesize(size_bytes):
#     if not size_bytes:
#         return "Unknown Size"
#     for unit in ['B', 'KB', 'MB', 'GB']:
#         if size_bytes < 1024:
#             return f"{size_bytes:.1f} {unit}"
#         size_bytes /= 1024
#     return f"{size_bytes:.1f} TB"

# def sanitize_filename(name):
#     return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80] or "video"

# def get_ydl_opts(extra_opts=None):
#     opts = {
#         'quiet': True,
#         'no_warnings': True,
#         'noplaylist': True,
#         'nocheckcertificate': True,
#         'geo_bypass': True,
#         'extractor_args': {
#             'youtube': {
#                 'player_client': ['android', 'ios', 'web'],
#             }
#         },
#         'http_headers': {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
#         }
#     }
#     if extra_opts:
#         opts.update(extra_opts)
#     return opts

# def extract_hqporner_formats(url):
#     session = requests.Session(impersonate="chrome")
#     resp = session.get(url, timeout=15)
#     bs = BeautifulSoup(resp.text, 'html.parser')

#     if resp.status_code == 404 or "Oops, page not found!" in resp.text or bs.find_all('section', {'class': 'box highlight'}):
#         slug = url.split("/")[-1].replace(".html", "")
#         clean_query = re.sub(r'^\d+-', '', slug).replace("_", "+").replace("-", "+")
#         search_resp = session.get(f"https://hqporner.com/?q={clean_query}", timeout=15)
#         search_bs = BeautifulSoup(search_resp.text, 'html.parser')
#         video_links = search_bs.find_all('a', href=re.compile(r'/hdporn/\d+-'))
#         if not video_links:
#             raise Exception("Video nahi mila.")
#         url = urljoin("https://hqporner.com/", video_links[0]['href'])
#         resp = session.get(url, timeout=15)
#         bs = BeautifulSoup(resp.text, 'html.parser')

#     h1 = bs.find('h1', {'class': 'main-h1'})
#     title = h1.get_text().strip() if h1 else "HQPorner Video"

#     iframe = bs.find('iframe', {'src': re.compile(r"mydaddy\.cc")})
#     if not iframe:
#         raise Exception("Video player nahi mila.")
    
#     iframe_url = iframe['src']
#     if iframe_url.startswith("//"):
#         iframe_url = "https:" + iframe_url

#     player_resp = session.get(iframe_url, headers={"Referer": url}, timeout=15)
#     mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+/(?:1080|720|480|360)\.mp4(?:\?[^"\'\s<>]*)?', player_resp.text)
    
#     if not mp4_links:
#         raise Exception("Direct MP4 links nahi mile.")

#     formats = []
#     seen_urls = set()
#     for link in mp4_links:
#         full_link = ("https:" + link) if link.startswith("//") else link
#         if full_link in seen_urls:
#             continue
#         seen_urls.add(full_link)
        
#         res = "HD"
#         for q in ["1080", "720", "480", "360"]:
#             if q in full_link:
#                 res = f"{q}p"
#                 break
        
#         formats.append({
#             "format_id": res,
#             "label": f"{res} | .mp4 | Video + Audio",
#             "type": "Video + Audio",
#             "ext": "mp4",
#             "resolution": res,
#             "url": full_link,
#             "referer": iframe_url,
#             "needs_merge": False
#         })

#     return {
#         "title": title,
#         "thumbnail": None,
#         "uploader": "HQPorner",
#         "source_url": url,
#         "is_hqporner": True,
#         "formats": formats
#     }

# def extract_universal_formats(url):
#     if "hqporner.com" in url:
#         return extract_hqporner_formats(url)

#     ydl_opts = get_ydl_opts()

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         info = ydl.extract_info(url, download=False)
        
#         formats_list = []
#         raw_formats = info.get('formats', [])

#         audio_formats = [f for f in raw_formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('url')]
#         best_audio = audio_formats[-1] if audio_formats else None

#         for f in reversed(raw_formats):
#             direct_url = f.get('url')
#             format_id = f.get('format_id')
#             if not direct_url or not format_id:
#                 continue

#             vcodec = f.get('vcodec', 'none')
#             acodec = f.get('acodec', 'none')
#             ext = f.get('ext', 'mp4')
#             height = f.get('height')
#             fps = f.get('fps')
#             filesize = f.get('filesize') or f.get('filesize_approx')

#             res_str = f"{height}p" if height else "Unknown"
#             fps_str = f" {int(fps)}fps" if fps and fps > 30 else ""
#             size_str = format_filesize(filesize)

#             # Case 1: Already Video + Audio
#             if vcodec != 'none' and acodec != 'none':
#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{res_str}{fps_str} | .{ext} | Video + Audio ({size_str})",
#                     "type": "Video + Audio",
#                     "ext": ext,
#                     "resolution": res_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#             # Case 2: Video Only (HD/4K) -> Merged + Mute dono options
#             elif vcodec != 'none' and acodec == 'none':
#                 if best_audio:
#                     merged_id = f"{format_id}+{best_audio['format_id']}"
#                     formats_list.append({
#                         "format_id": merged_id,
#                         "label": f"{res_str}{fps_str} | .mp4 | Video + Audio (Merged) ({size_str}+)",
#                         "type": "Video + Audio",
#                         "ext": "mp4",
#                         "resolution": res_str,
#                         "url": direct_url,
#                         "referer": url,
#                         "needs_merge": True
#                     })

#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{res_str}{fps_str} | .{ext} | Video Only (Mute) ({size_str})",
#                     "type": "Video Only (Mute)",
#                     "ext": ext,
#                     "resolution": res_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#             # Case 3: Audio Only
#             elif vcodec == 'none' and acodec != 'none':
#                 abr = f.get('abr')
#                 bitrate_str = f"{int(abr)}kbps" if abr else "Audio"
#                 formats_list.append({
#                     "format_id": format_id,
#                     "label": f"{bitrate_str} | .{ext} | Audio Only ({size_str})",
#                     "type": "Audio Only",
#                     "ext": ext,
#                     "resolution": bitrate_str,
#                     "url": direct_url,
#                     "referer": url,
#                     "needs_merge": False
#                 })

#         return {
#             "title": info.get('title', 'Extracted Video'),
#             "thumbnail": info.get('thumbnail'),
#             "uploader": info.get('uploader') or info.get('extractor_key', 'Web'),
#             "source_url": url,
#             "is_hqporner": False,
#             "formats": formats_list
#         }

# def fetch_video_bytes(data, selected_fmt):
#     """Video ko fetch karke direct download ke liye bytes return karta hai"""
#     filename = f"{sanitize_filename(data['title'])}_{selected_fmt['resolution']}.{selected_fmt['ext']}"
    
#     if data.get("is_hqporner"):
#         session = requests.Session(impersonate="chrome")
#         resp = session.get(selected_fmt["url"], headers={"Referer": selected_fmt["referer"]}, timeout=120)
#         resp.raise_for_status()
#         return resp.content, filename
#     else:
#         with tempfile.TemporaryDirectory() as tmpdir:
#             out_template = os.path.join(tmpdir, "download.%(ext)s")
#             extra = {
#                 'format': selected_fmt['format_id'],
#                 'outtmpl': out_template,
#             }
#             if selected_fmt.get("needs_merge"):
#                 extra['merge_output_format'] = 'mp4'

#             ydl_opts = get_ydl_opts(extra)
#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 ydl.download([data["source_url"]])
            
#             downloaded_files = os.listdir(tmpdir)
#             if not downloaded_files:
#                 raise Exception("File download nahi ho payi.")
            
#             filepath = os.path.join(tmpdir, downloaded_files[0])
#             with open(filepath, "rb") as f:
#                 return f.read(), filename

# # --- UI Layout ---
# st.title("🎬 Universal Video Downloader")
# st.write("YouTube, Instagram, X (Twitter), Reddit, Vimeo, Eporner, HQPorner aur 1000+ sites ke videos **With Audio**, **Mute**, ya **Audio Only** format mein download ya stream karein.")

# url_input = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

# if st.button("🔍 Fetch Available Formats", type="primary"):
#     if not url_input.strip():
#         st.warning("Kripya pehle ek valid URL paste karein.")
#     else:
#         with st.spinner("Video details aur formats scan kiye ja rahe hain..."):
#             try:
#                 st.session_state.video_data = extract_universal_formats(url_input.strip())
#                 st.session_state.prepared_file = None
#             except Exception as e:
#                 st.session_state.video_data = None
#                 st.session_state.prepared_file = None
#                 st.error(f"Error: {str(e)}")

# # --- Results & Format Filter Section ---
# if st.session_state.video_data:
#     data = st.session_state.video_data
#     st.divider()

#     col1, col2 = st.columns([1, 2])
#     with col1:
#         if data["thumbnail"]:
#             st.image(data["thumbnail"], use_container_width=True)
#     with col2:
#         st.subheader(data["title"])
#         st.caption(f"Source / Uploader: {data['uploader']}")

#     all_formats = data["formats"]
#     if not all_formats:
#         st.warning("Is video ke liye koi direct downloadable format nahi mila.")
#     else:
#         st.markdown("### 🎛️ Format Filter karein")
        
#         f_col1, f_col2 = st.columns(2)
#         with f_col1:
#             unique_types = list(dict.fromkeys(f["type"] for f in all_formats))
#             available_types = ["All"] + unique_types
#             default_idx = available_types.index("Video + Audio") if "Video + Audio" in available_types else 0
#             selected_type = st.selectbox("Stream Type chunein:", available_types, index=default_idx)
            
#         with f_col2:
#             available_exts = ["All"] + sorted(list(set(f["ext"] for f in all_formats)))
#             selected_ext = st.selectbox("File Format (.ext) chunein:", available_exts)

#         filtered_formats = [
#             f for f in all_formats
#             if (selected_type == "All" or f["type"] == selected_type)
#             and (selected_ext == "All" or f["ext"] == selected_ext)
#         ]

#         if not filtered_formats:
#             st.info("Is filter combination ke liye koi format available nahi hai.")
#         else:
#             st.success(f"{len(filtered_formats)} formats available hain:")
            
#             format_map = {f["label"]: f for f in filtered_formats}
#             chosen_label = st.selectbox("Quality select karein:", list(format_map.keys()))
#             selected_fmt = format_map[chosen_label]

#             if selected_fmt.get("needs_merge"):
#                 st.caption("ℹ️ Note: Direct Download par click karne par HD Video aur Best Audio automatically merge hokar ek single MP4 file banenge.")

#             # --- Side-by-Side Action Buttons ---
#             btn_col1, btn_col2 = st.columns(2)

#             with btn_col1:
#                 if st.session_state.prepared_file and st.session_state.prepared_file["label"] == chosen_label:
#                     st.download_button(
#                         label=f"⬇️ Save File ({st.session_state.prepared_file['name'][:18]}...)",
#                         data=st.session_state.prepared_file["bytes"],
#                         file_name=st.session_state.prepared_file["name"],
#                         mime="application/octet-stream",
#                         type="primary",
#                         use_container_width=True
#                     )
#                 else:
#                     if st.button("⬇️ Direct Download", type="primary", use_container_width=True):
#                         with st.spinner("Video aur Audio fetch/merge ho rahe hain..."):
#                             try:
#                                 file_bytes, file_name = fetch_video_bytes(data, selected_fmt)
#                                 st.session_state.prepared_file = {
#                                     "bytes": file_bytes,
#                                     "name": file_name,
#                                     "label": chosen_label
#                                 }
#                                 st.rerun()
#                             except Exception as e:
#                                 st.error(f"Download error: {str(e)}")

#             with btn_col2:
#                 st.link_button(
#                     label="▶️ Stream / Play",
#                     url=selected_fmt["url"],
#                     use_container_width=True
#                 )










# import streamlit as st
# import yt_dlp
# import re
# import os
# import tempfile
# from curl_cffi import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin

# # Page Configuration
# st.set_page_config(page_title="Universal Video Downloader", page_icon="🎬", layout="centered")

# if "video_data" not in st.session_state:
#     st.session_state.video_data = None
# if "prepared_file" not in st.session_state:
#     st.session_state.prepared_file = None

# def format_filesize(size_bytes):
#     if not size_bytes:
#         return "Unknown Size"
#     for unit in ['B', 'KB', 'MB', 'GB']:
#         if size_bytes < 1024:
#             return f"{size_bytes:.1f} {unit}"
#         size_bytes /= 1024
#     return f"{size_bytes:.1f} TB"

# def sanitize_filename(name):
#     return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80] or "video"

# def extract_hqporner_formats(url):
#     session = requests.Session(impersonate="chrome")
#     resp = session.get(url, timeout=15)
#     bs = BeautifulSoup(resp.text, 'html.parser')

#     if resp.status_code == 404 or "Oops, page not found!" in resp.text or bs.find_all('section', {'class': 'box highlight'}):
#         slug = url.split("/")[-1].replace(".html", "")
#         clean_query = re.sub(r'^\d+-', '', slug).replace("_", "+").replace("-", "+")
#         search_resp = session.get(f"https://hqporner.com/?q={clean_query}", timeout=15)
#         search_bs = BeautifulSoup(search_resp.text, 'html.parser')
#         video_links = search_bs.find_all('a', href=re.compile(r'/hdporn/\d+-'))
#         if not video_links:
#             raise Exception("Video nahi mila.")
#         url = urljoin("https://hqporner.com/", video_links[0]['href'])
#         resp = session.get(url, timeout=15)
#         bs = BeautifulSoup(resp.text, 'html.parser')

#     h1 = bs.find('h1', {'class': 'main-h1'})
#     title = h1.get_text().strip() if h1 else "HQPorner Video"

#     iframe = bs.find('iframe', {'src': re.compile(r"mydaddy\.cc")})
#     if not iframe:
#         raise Exception("Video player nahi mila.")
    
#     iframe_url = iframe['src']
#     if iframe_url.startswith("//"):
#         iframe_url = "https:" + iframe_url

#     player_resp = session.get(iframe_url, headers={"Referer": url}, timeout=15)
#     mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+/(?:1080|720|480|360)\.mp4(?:\?[^"\'\s<>]*)?', player_resp.text)
    
#     if not mp4_links:
#         raise Exception("Direct MP4 links nahi mile.")

#     formats = []
#     seen_urls = set()
#     for link in mp4_links:
#         full_link = ("https:" + link) if link.startswith("//") else link
#         if full_link in seen_urls:
#             continue
#         seen_urls.add(full_link)
        
#         res = "HD"
#         for q in ["1080", "720", "480", "360"]:
#             if q in full_link:
#                 res = f"{q}p"
#                 break
        
#         formats.append({
#             "format_id": res,
#             "label": f"Video + Audio | {res} (.mp4)",
#             "type": "Video + Audio",
#             "ext": "mp4",
#             "resolution": res,
#             "url": full_link,
#             "referer": iframe_url
#         })

#     return {
#         "title": title,
#         "thumbnail": None,
#         "uploader": "HQPorner",
#         "source_url": url,
#         "is_hqporner": True,
#         "formats": formats
#     }

# def extract_universal_formats(url):
#     if "hqporner.com" in url:
#         return extract_hqporner_formats(url)

#     ydl_opts = {
#         'quiet': True,
#         'no_warnings': True,
#         'noplaylist': True,
#     }

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         info = ydl.extract_info(url, download=False)
        
#         formats_list = []
#         raw_formats = info.get('formats', [])

#         for f in raw_formats:
#             direct_url = f.get('url')
#             format_id = f.get('format_id')
#             if not direct_url or not format_id:
#                 continue

#             vcodec = f.get('vcodec', 'none')
#             acodec = f.get('acodec', 'none')
#             ext = f.get('ext', 'mp4')
#             height = f.get('height')
#             fps = f.get('fps')
#             filesize = f.get('filesize') or f.get('filesize_approx')

#             if vcodec != 'none' and acodec != 'none':
#                 stream_type = "Video + Audio"
#             elif vcodec != 'none' and acodec == 'none':
#                 stream_type = "Video Only (Mute)"
#             elif vcodec == 'none' and acodec != 'none':
#                 stream_type = "Audio Only"
#             else:
#                 continue

#             res_str = f"{height}p" if height else ("Audio" if stream_type == "Audio Only" else "Unknown")
#             fps_str = f" {int(fps)}fps" if fps and fps > 30 else ""
#             size_str = format_filesize(filesize)

#             label = f"{res_str}{fps_str} | .{ext} | {stream_type} ({size_str})"
            
#             formats_list.append({
#                 "format_id": format_id,
#                 "label": label,
#                 "type": stream_type,
#                 "ext": ext,
#                 "resolution": res_str,
#                 "url": direct_url,
#                 "referer": url
#             })

#         formats_list.reverse()

#         return {
#             "title": info.get('title', 'Extracted Video'),
#             "thumbnail": info.get('thumbnail'),
#             "uploader": info.get('uploader') or info.get('extractor_key', 'Web'),
#             "source_url": url,
#             "is_hqporner": False,
#             "formats": formats_list
#         }

# def fetch_video_bytes(data, selected_fmt):
#     """Video ko fetch karke direct download ke liye bytes return karta hai"""
#     filename = f"{sanitize_filename(data['title'])}_{selected_fmt['resolution']}.{selected_fmt['ext']}"
    
#     if data.get("is_hqporner"):
#         session = requests.Session(impersonate="chrome")
#         resp = session.get(selected_fmt["url"], headers={"Referer": selected_fmt["referer"]}, timeout=120)
#         resp.raise_for_status()
#         return resp.content, filename
#     else:
#         with tempfile.TemporaryDirectory() as tmpdir:
#             out_template = os.path.join(tmpdir, "download.%(ext)s")
#             ydl_opts = {
#                 'format': selected_fmt['format_id'],
#                 'outtmpl': out_template,
#                 'quiet': True,
#                 'no_warnings': True,
#             }
#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 ydl.download([data["source_url"]])
            
#             downloaded_files = os.listdir(tmpdir)
#             if not downloaded_files:
#                 raise Exception("File download nahi ho payi.")
            
#             filepath = os.path.join(tmpdir, downloaded_files[0])
#             with open(filepath, "rb") as f:
#                 return f.read(), filename

# # --- UI Layout ---
# st.title("🎬 Universal Video Downloader")
# st.write("YouTube, Instagram, X (Twitter), Reddit, Vimeo, Eporner, HQPorner aur 1000+ sites ke videos direct download ya stream karein.")

# url_input = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

# if st.button("🔍 Fetch Available Formats", type="primary"):
#     if not url_input.strip():
#         st.warning("Kripya pehle ek valid URL paste karein.")
#     else:
#         with st.spinner("Video details aur formats scan kiye ja rahe hain..."):
#             try:
#                 st.session_state.video_data = extract_universal_formats(url_input.strip())
#                 st.session_state.prepared_file = None
#             except Exception as e:
#                 st.session_state.video_data = None
#                 st.session_state.prepared_file = None
#                 st.error(f"Error: {str(e)}")

# # --- Results & Format Filter Section ---
# if st.session_state.video_data:
#     data = st.session_state.video_data
#     st.divider()

#     col1, col2 = st.columns([1, 2])
#     with col1:
#         if data["thumbnail"]:
#             st.image(data["thumbnail"], use_container_width=True)
#     with col2:
#         st.subheader(data["title"])
#         st.caption(f"Source / Uploader: {data['uploader']}")

#     all_formats = data["formats"]
#     if not all_formats:
#         st.warning("Is video ke liye koi direct downloadable format nahi mila.")
#     else:
#         st.markdown("### 🎛️ Format Filter karein")
        
#         f_col1, f_col2 = st.columns(2)
#         with f_col1:
#             available_types = ["All"] + sorted(list(set(f["type"] for f in all_formats)))
#             selected_type = st.selectbox("Stream Type chunein:", available_types)
            
#         with f_col2:
#             available_exts = ["All"] + sorted(list(set(f["ext"] for f in all_formats)))
#             selected_ext = st.selectbox("File Format (.ext) chunein:", available_exts)

#         filtered_formats = [
#             f for f in all_formats
#             if (selected_type == "All" or f["type"] == selected_type)
#             and (selected_ext == "All" or f["ext"] == selected_ext)
#         ]

#         if not filtered_formats:
#             st.info("Is filter combination ke liye koi format available nahi hai.")
#         else:
#             st.success(f"{len(filtered_formats)} formats available hain:")
            
#             format_map = {f["label"]: f for f in filtered_formats}
#             chosen_label = st.selectbox("Quality select karein:", list(format_map.keys()))
#             selected_fmt = format_map[chosen_label]

#             # --- Side-by-Side Action Buttons ---
#             btn_col1, btn_col2 = st.columns(2)

#             with btn_col1:
#                 # Left Button: Direct Download
#                 if st.session_state.prepared_file and st.session_state.prepared_file["label"] == chosen_label:
#                     st.download_button(
#                         label=f"⬇️ Save File ({st.session_state.prepared_file['name'][:20]}...)",
#                         data=st.session_state.prepared_file["bytes"],
#                         file_name=st.session_state.prepared_file["name"],
#                         mime="application/octet-stream",
#                         type="primary",
#                         use_container_width=True
#                     )
#                 else:
#                     if st.button("⬇️ Direct Download", type="primary", use_container_width=True):
#                         with st.spinner("File fetch ki ja rahi hai..."):
#                             try:
#                                 file_bytes, file_name = fetch_video_bytes(data, selected_fmt)
#                                 st.session_state.prepared_file = {
#                                     "bytes": file_bytes,
#                                     "name": file_name,
#                                     "label": chosen_label
#                                 }
#                                 st.rerun()
#                             except Exception as e:
#                                 st.error(f"Download error: {str(e)}")

#             with btn_col2:
#                 # Right Button: Stream in Browser
#                 st.link_button(
#                     label="▶️ Stream / Play",
#                     url=selected_fmt["url"],
#                     use_container_width=True
#                 )