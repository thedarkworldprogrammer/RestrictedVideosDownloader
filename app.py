import streamlit as st
from curl_cffi import requests
import re
import yt_dlp
from bs4 import BeautifulSoup
from dataclasses import dataclass
from urllib.parse import urljoin

# Page Configuration
st.set_page_config(page_title="Video Link Extractor & Downloader", page_icon="🎬", layout="centered")

@dataclass
class VideoResult:
    title: str
    uploader: str
    download_url: str
    resolution: str
    source_url: str

def extract_hqporner(url):
    # impersonate="chrome" asli Chrome browser ka TLS fingerprint bhejta hai
    session = requests.Session(impersonate="chrome")

    # Step 1: HQPorner page fetch karein
    resp = session.get(url, timeout=15)
    bs = BeautifulSoup(resp.text, 'html.parser')

    # Agar 404 aaye toh title se search karein
    if resp.status_code == 404 or bs.find_all('section', {'class': 'box highlight'}):
        slug = url.split("/")[-1].replace(".html", "")
        clean_query = re.sub(r'^\d+-', '', slug).replace("_", "+").replace("-", "+")
        search_url = f"https://hqporner.com/?q={clean_query}"
        
        search_resp = session.get(search_url, timeout=15)
        search_bs = BeautifulSoup(search_resp.text, 'html.parser')
        
        result_link = search_bs.find('a', {'class': 'non-overlay'})
        if not result_link or not result_link.get('href'):
            raise Exception(f"Search mein bhi video nahi mila ({clean_query}).")
        
        new_url = urljoin("https://hqporner.com/", result_link['href'])
        resp = session.get(new_url, timeout=15)
        bs = BeautifulSoup(resp.text, 'html.parser')
        url = new_url

    if resp.status_code != 200:
        raise Exception(f"Page load nahi hua (Status: {resp.status_code}) -> URL: {url}")

    # Video title aur model nikalna
    h1 = bs.find('h1', {'class': 'main-h1'})
    title = h1.get_text().strip() if h1 else "HQPorner Video"

    star_li = bs.find('li', {'class': 'icon fa-star-o'})
    uploader = star_li.get_text().replace("featuring ", "").replace(",", " and").strip() if star_li else "Unknown"

    # Step 2: mydaddy.cc iframe dhoondhna
    iframe = bs.find('iframe', {'src': re.compile(r"mydaddy\.cc")})
    if not iframe:
        iframe_match = re.search(r'(?:https?:)?//mydaddy\.cc/video/[a-zA-Z0-9_-]+/?', resp.text)
        if not iframe_match:
            raise Exception("Video player (mydaddy.cc) nahi mila.")
        iframe_url = iframe_match.group(0)
    else:
        iframe_url = iframe['src']

    if iframe_url.startswith("//"):
        iframe_url = "https:" + iframe_url

    # Step 3: Referer header ke saath mydaddy.cc player fetch karna
    player_resp = session.get(iframe_url, headers={"Referer": url}, timeout=15)
    
    if player_resp.status_code != 200:
        raise Exception(f"Player load nahi hua (Status: {player_resp.status_code})")

    player_html = player_resp.text

    # Step 4: MP4 links extract karna
    mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+/(?:1080|720|480|360)\.mp4(?:\?[^"\'\s<>]*)?', player_html)
    
    if not mp4_links:
        mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+\.mp4(?:\?[^"\'\s<>]*)?', player_html)

    if not mp4_links:
        raise Exception("Player ke andar MP4 link nahi mila.")

    best_link = mp4_links[-1]
    for q in ["1080.mp4", "720.mp4", "480.mp4"]:
        matched = [link for link in mp4_links if q in link]
        if matched:
            best_link = matched[0]
            break

    if best_link.startswith("//"):
        best_link = "https:" + best_link

    res = "1080p" if "1080" in best_link else ("720p" if "720" in best_link else "HD")
    return VideoResult(title, uploader, best_link, res, url)

def extract_generic_ytdlp(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'Video')
        uploader = info.get('uploader') or "Unknown"
        download_url = info.get('url')
        height = info.get('height')
        resolution = f"{height}p" if height else "HD"
        if not download_url:
            raise Exception("Direct MP4 URL nahi mila.")
        return VideoResult(title, uploader, download_url, resolution, url)

# --- UI Layout ---
st.title("🎬 Video Downloader Web App")
st.write("Neeche diye gaye box mein video URLs paste karein (har line mein ek URL).")

urls_input = st.text_area("Video URLs:", height=150, placeholder="https://hqporner.com/hdporn/...\nhttps://www.eporner.com/...")

if st.button("Extract Videos", type="primary"):
    url_list = [line.strip() for line in urls_input.split("\n") if line.strip()]
    
    if not url_list:
        st.warning("Kripya kam se kam ek URL enter karein.")
    else:
        results = []
        errors = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        with st.spinner("Links extract kiye ja rahe hain..."):
            for idx, url in enumerate(url_list):
                status_text.text(f"Processing ({idx + 1}/{len(url_list)}): {url}")
                try:
                    if "hqporner.com" in url:
                        vid = extract_hqporner(url)
                    else:
                        vid = extract_generic_ytdlp(url)
                    results.append(vid)
                except Exception as e:
                    errors.append(f"{url} -> Error: {str(e)}")
                progress_bar.progress((idx + 1) / len(url_list))

        status_text.text("Process Complete!")

        if results:
            st.success(f"{len(results)} videos ready hain!")
            for vid in results:
                with st.container(border=True):
                    st.subheader(vid.title)
                    st.caption(f"Model: {vid.uploader} | Quality: {vid.resolution}")
                    st.link_button(f"⬇️ Download MP4 ({vid.resolution})", vid.download_url)

        if errors:
            st.error("Kuch links fail ho gaye:")
            for err in errors:
                st.write(f"- {err}")