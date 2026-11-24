import streamlit as st
import yt_dlp
import re
import os
import tempfile
from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Page Configuration
st.set_page_config(page_title="Universal Video Downloader", page_icon="🎬", layout="centered")

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
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        formats_list = []
        raw_formats = info.get('formats', [])

        # Sabse best audio format dhoondhein (HD video ke saath merge karne ke liye)
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

            # Case 1: Already Video + Audio (jaise 360p ya single-stream sites)
            if vcodec != 'none' and acodec != 'none':
                formats_list.append({
                    "format_id": format_id,
                    "label": f"{res_str}{fps_str} | .{ext} | Video + Audio ({size_str})",
                    "type": "Video + Audio",
                    "ext": ext,
                    "resolution": res_str,
                    "url": direct_url,
                    "referer": url,
                    "needs_merge": False
                })

            # Case 2: Video Only (1080p, 1440p, 4K) -> Iske liye BOTH (Video + Audio Merged) aur (Video Only Mute) options banayein
            elif vcodec != 'none' and acodec == 'none':
                # Option A: Video + Audio (Auto-Merged with Best Audio)
                if best_audio:
                    merged_id = f"{format_id}+{best_audio['format_id']}"
                    formats_list.append({
                        "format_id": merged_id,
                        "label": f"{res_str}{fps_str} | .mp4 | Video + Audio (Merged) ({size_str}+)",
                        "type": "Video + Audio",
                        "ext": "mp4",
                        "resolution": res_str,
                        "url": direct_url,
                        "referer": url,
                        "needs_merge": True
                    })

                # Option B: Video Only (Mute)
                formats_list.append({
                    "format_id": format_id,
                    "label": f"{res_str}{fps_str} | .{ext} | Video Only (Mute) ({size_str})",
                    "type": "Video Only (Mute)",
                    "ext": ext,
                    "resolution": res_str,
                    "url": direct_url,
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
    """Video ko fetch karke direct download ke liye bytes return karta hai"""
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
            # Default mein "Video + Audio" upar rakhein taaki user ko seedha audio ke saath options dikhein
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

            if selected_fmt.get("needs_merge"):
                st.caption("ℹ️ Note: Direct Download par click karne par HD Video aur Best Audio automatically merge hokar ek single MP4 file banenge.")

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
                st.link_button(
                    label="▶️ Stream / Play",
                    url=selected_fmt["url"],
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







# import streamlit as st
# import yt_dlp
# import re
# from curl_cffi import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin

# # Page Configuration
# st.set_page_config(page_title="Universal Video Downloader", page_icon="🎬", layout="centered")

# # Session State initialize karna taaki dropdown change karne par data gayab na ho
# if "video_data" not in st.session_state:
#     st.session_state.video_data = None

# def format_filesize(size_bytes):
#     if not size_bytes:
#         return "Unknown Size"
#     for unit in ['B', 'KB', 'MB', 'GB']:
#         if size_bytes < 1024:
#             return f"{size_bytes:.1f} {unit}"
#         size_bytes /= 1024
#     return f"{size_bytes:.1f} TB"

# def extract_hqporner_formats(url):
#     """HQPorner ke liye custom format extractor"""
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
#             "label": f"Video + Audio | {res} (.mp4)",
#             "type": "Video + Audio",
#             "ext": "mp4",
#             "resolution": res,
#             "url": full_link
#         })

#     return {
#         "title": title,
#         "thumbnail": None,
#         "uploader": "HQPorner",
#         "formats": formats
#     }

# def extract_universal_formats(url):
#     """yt-dlp ka use karke kisi bhi site ke saare available formats nikalna"""
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
#             if not direct_url:
#                 continue

#             vcodec = f.get('vcodec', 'none')
#             acodec = f.get('acodec', 'none')
#             ext = f.get('ext', 'mp4')
#             height = f.get('height')
#             fps = f.get('fps')
#             filesize = f.get('filesize') or f.get('filesize_approx')

#             # Stream type categorize karna
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
#                 "label": label,
#                 "type": stream_type,
#                 "ext": ext,
#                 "resolution": res_str,
#                 "url": direct_url
#             })

#         # Agar formats list khali ho toh fallback main URL use karein
#         if not formats_list and info.get('url'):
#             formats_list.append({
#                 "label": f"Default Best Quality (.{info.get('ext', 'mp4')})",
#                 "type": "Video + Audio",
#                 "ext": info.get('ext', 'mp4'),
#                 "resolution": "Best",
#                 "url": info.get('url')
#             })

#         # Latest/Highest quality ko upar dikhane ke liye reverse karein
#         formats_list.reverse()

#         return {
#             "title": info.get('title', 'Extracted Video'),
#             "thumbnail": info.get('thumbnail'),
#             "uploader": info.get('uploader') or info.get('extractor_key', 'Web'),
#             "formats": formats_list
#         }

# # --- UI Layout ---
# st.title("🎬 Universal Video Downloader")
# st.write("YouTube, Instagram, X (Twitter), Reddit, Vimeo, Eporner, HQPorner aur 1000+ sites ke videos fetch karein.")

# url_input = st.text_input("Video URL paste karein:", placeholder="https://www.youtube.com/watch?v=...")

# if st.button("🔍 Fetch Available Formats", type="primary"):
#     if not url_input.strip():
#         st.warning("Kripya pehle ek valid URL paste karein.")
#     else:
#         with st.spinner("Video details aur formats scan kiye ja rahe hain..."):
#             try:
#                 st.session_state.video_data = extract_universal_formats(url_input.strip())
#             except Exception as e:
#                 st.session_state.video_data = None
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
        
#         # Filter Controls (2 Columns mein)
#         f_col1, f_col2 = st.columns(2)
        
#         with f_col1:
#             available_types = ["All"] + sorted(list(set(f["type"] for f in all_formats)))
#             selected_type = st.selectbox("Stream Type chunein:", available_types)
            
#         with f_col2:
#             available_exts = ["All"] + sorted(list(set(f["ext"] for f in all_formats)))
#             selected_ext = st.selectbox("File Format (.ext) chunein:", available_exts)

#         # Filter apply karna
#         filtered_formats = [
#             f for f in all_formats
#             if (selected_type == "All" or f["type"] == selected_type)
#             and (selected_ext == "All" or f["ext"] == selected_ext)
#         ]

#         if not filtered_formats:
#             st.info("Is filter combination ke liye koi format available nahi hai. Filter badal kar dekhein.")
#         else:
#             st.success(f"{len(filtered_formats)} formats available hain:")
            
#             # Final Quality Selection Dropdown
#             format_options = {f["label"]: f["url"] for f in filtered_formats}
#             chosen_label = st.selectbox("Download karne ke liye Quality select karein:", list(format_options.keys()))
            
#             download_link = format_options[chosen_label]
#             st.link_button("⬇️ Download Selected Format", download_link, type="primary", use_container_width=True)





# import streamlit as st
# from curl_cffi import requests
# import re
# import yt_dlp
# from bs4 import BeautifulSoup
# from dataclasses import dataclass
# from urllib.parse import urljoin

# # Page Configuration
# st.set_page_config(page_title="Video Link Extractor & Downloader", page_icon="🎬", layout="centered")

# @dataclass
# class VideoResult:
#     title: str
#     uploader: str
#     download_url: str
#     resolution: str
#     source_url: str

# def extract_hqporner(url):
#     session = requests.Session(impersonate="chrome")

#     # Step 1: Direct URL try karein
#     resp = session.get(url, timeout=15)
#     bs = BeautifulSoup(resp.text, 'html.parser')

#     # Agar 404 aaye toh title se search karein
#     if resp.status_code == 404 or "Oops, page not found!" in resp.text or bs.find_all('section', {'class': 'box highlight'}):
#         slug = url.split("/")[-1].replace(".html", "")
#         clean_query = re.sub(r'^\d+-', '', slug).replace("_", "+").replace("-", "+")
#         search_url = f"https://hqporner.com/?q={clean_query}"
        
#         search_resp = session.get(search_url, timeout=15)
#         search_bs = BeautifulSoup(search_resp.text, 'html.parser')
        
#         # Sirf wahi link uthayein jiske href mein '/hdporn/' ho
#         video_links = search_bs.find_all('a', href=re.compile(r'/hdporn/\d+-'))
#         if not video_links:
#             raise Exception(f"Video delete ho chuka hai, search mein bhi nahi mila ({clean_query}).")
        
#         new_url = urljoin("https://hqporner.com/", video_links[0]['href'])
#         resp = session.get(new_url, timeout=15)
#         bs = BeautifulSoup(resp.text, 'html.parser')
#         url = new_url

#     if resp.status_code != 200:
#         raise Exception(f"Page load nahi hua (Status: {resp.status_code}) -> URL: {url}")

#     # Video title aur model nikalna
#     h1 = bs.find('h1', {'class': 'main-h1'})
#     title = h1.get_text().strip() if h1 else "HQPorner Video"

#     star_li = bs.find('li', {'class': 'icon fa-star-o'})
#     uploader = star_li.get_text().replace("featuring ", "").replace(",", " and").strip() if star_li else "Unknown"

#     # Step 2: mydaddy.cc iframe dhoondhna
#     iframe = bs.find('iframe', {'src': re.compile(r"mydaddy\.cc")})
#     if not iframe:
#         iframe_match = re.search(r'(?:https?:)?//mydaddy\.cc/video/[a-zA-Z0-9_-]+/?', resp.text)
#         if not iframe_match:
#             raise Exception("Video player (mydaddy.cc) nahi mila.")
#         iframe_url = iframe_match.group(0)
#     else:
#         iframe_url = iframe['src']

#     if iframe_url.startswith("//"):
#         iframe_url = "https:" + iframe_url

#     # Step 3: Referer header ke saath mydaddy.cc player fetch karna
#     player_resp = session.get(iframe_url, headers={"Referer": url}, timeout=15)
    
#     if player_resp.status_code != 200:
#         raise Exception(f"Player load nahi hua (Status: {player_resp.status_code})")

#     player_html = player_resp.text

#     # Step 4: MP4 links extract karna
#     mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+/(?:1080|720|480|360)\.mp4(?:\?[^"\'\s<>]*)?', player_html)
    
#     if not mp4_links:
#         mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+\.mp4(?:\?[^"\'\s<>]*)?', player_html)

#     if not mp4_links:
#         raise Exception("Player ke andar MP4 link nahi mila.")

#     best_link = mp4_links[-1]
#     for q in ["1080.mp4", "720.mp4", "480.mp4"]:
#         matched = [link for link in mp4_links if q in link]
#         if matched:
#             best_link = matched[0]
#             break

#     if best_link.startswith("//"):
#         best_link = "https:" + best_link

#     res = "1080p" if "1080" in best_link else ("720p" if "720" in best_link else "HD")
#     return VideoResult(title, uploader, best_link, res, url)

# def extract_generic_ytdlp(url):
#     ydl_opts = {
#         'quiet': True,
#         'no_warnings': True,
#         'format': 'best[ext=mp4]/best',
#     }
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         info = ydl.extract_info(url, download=False)
#         title = info.get('title', 'Video')
#         uploader = info.get('uploader') or "Unknown"
#         download_url = info.get('url')
#         height = info.get('height')
#         resolution = f"{height}p" if height else "HD"
#         if not download_url:
#             raise Exception("Direct MP4 URL nahi mila.")
#         return VideoResult(title, uploader, download_url, resolution, url)

# # --- UI Layout ---
# st.title("🎬 Video Downloader Web App")
# st.write("Neeche diye gaye box mein video URLs paste karein (har line mein ek URL).")

# urls_input = st.text_area("Video URLs:", height=150, placeholder="https://hqporner.com/hdporn/...\nhttps://www.eporner.com/...")

# if st.button("Extract Videos", type="primary"):
#     url_list = [line.strip() for line in urls_input.split("\n") if line.strip()]
    
#     if not url_list:
#         st.warning("Kripya kam se kam ek URL enter karein.")
#     else:
#         results = []
#         errors = []
#         progress_bar = st.progress(0)
#         status_text = st.empty()

#         with st.spinner("Links extract kiye ja rahe hain..."):
#             for idx, url in enumerate(url_list):
#                 status_text.text(f"Processing ({idx + 1}/{len(url_list)}): {url}")
#                 try:
#                     if "hqporner.com" in url:
#                         vid = extract_hqporner(url)
#                     else:
#                         vid = extract_generic_ytdlp(url)
#                     results.append(vid)
#                 except Exception as e:
#                     errors.append(f"{url} -> Error: {str(e)}")
#                 progress_bar.progress((idx + 1) / len(url_list))

#         status_text.text("Process Complete!")

#         if results:
#             st.success(f"{len(results)} videos ready hain!")
#             for vid in results:
#                 with st.container(border=True):
#                     st.subheader(vid.title)
#                     st.caption(f"Model: {vid.uploader} | Quality: {vid.resolution}")
#                     st.link_button(f"⬇️ Download MP4 ({vid.resolution})", vid.download_url)

#         if errors:
#             st.error("Kuch links fail ho gaye:")
#             for err in errors:
#                 st.write(f"- {err}")