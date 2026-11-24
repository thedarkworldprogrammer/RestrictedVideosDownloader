import streamlit as st
import requests
import re
import yt_dlp
from bs4 import BeautifulSoup
from dataclasses import dataclass

# Page Configuration
st.set_page_config(page_title="Video Link Extractor & Downloader", page_icon="🎬", layout="centered")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

@dataclass
class VideoResult:
    title: str
    uploader: str
    download_url: str
    resolution: str
    source_url: str

def extract_hqporner(url):
    session = requests.Session()
    session.headers.update(HEADERS)

    # Step 1: Direct URL try karein
    resp = session.get(url, timeout=15)
    bs = BeautifulSoup(resp.text, 'html.parser')

    # Agar 404 aaye ya "box highlight" error section dikhe, toh title se search karein (purane main.py wala logic)
    if resp.status_code == 404 or bs.find_all('section', {'class': 'box highlight'}):
        slug = url.split("/")[-1].replace(".html", "")
        # Shuru ke numbers (jaise 116280-) hata kar words nikalein
        clean_query = re.sub(r'^\d+-', '', slug).replace("_", "+").replace("-", "+")
        search_url = f"https://hqporner.com/?q={clean_query}"
        
        search_resp = session.get(search_url, timeout=15)
        search_bs = BeautifulSoup(search_resp.text, 'html.parser')
        
        # Search results mein pehla video link dhoondhein
        result_link = search_bs.find('a', {'class': 'non-overlay'})
        if not result_link or not result_link.get('href'):
            raise Exception(f"Page 404 tha aur search mein bhi video nahi mila ({clean_query}).")
        
        new_url = "https://hqporner.com" + result_link['href']
        resp = session.get(new_url, timeout=15)
        bs = BeautifulSoup(resp.text, 'html.parser')
        url = new_url

    if resp.status_code != 200:
        raise Exception(f"HQPorner page load nahi hua (Status: {resp.status_code})")

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
    player_headers = HEADERS.copy()
    player_headers["Referer"] = url
    player_resp = session.get(iframe_url, headers=player_headers, timeout=15)
    
    if player_resp.status_code != 200:
        raise Exception(f"Player load nahi hua (Status: {player_resp.status_code})")

    player_html = player_resp.text

    # Step 4: MP4 links extract karna
    mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+/(?:1080|720|480|360)\.mp4(?:\?[^"\'\s<>]*)?', player_html)
    
    if not mp4_links:
        mp4_links = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+\.mp4(?:\?[^"\'\s<>]*)?', player_html)

    if not mp4_links:
        raise Exception("Player ke andar MP4 link nahi mila (JS/Bot protection).")

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
        'http_headers': HEADERS
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








# import streamlit as st
# import yt_dlp
# from dataclasses import dataclass

# # Page Configuration
# st.set_page_config(page_title="Video Link Extractor & Downloader", page_icon="🎬", layout="centered")

# @dataclass
# class VideoResult:
#     title: str
#     uploader: str
#     download_url: str
#     resolution: str
#     source_url: str

# def extract_with_ytdlp(urls):
#     results = []
#     errors = []

#     ydl_opts = {
#         'quiet': True,
#         'no_warnings': True,
#         'format': 'best[ext=mp4]/best',  # Best MP4 quality select karne ke liye
#         'http_headers': {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
#             'Referer': 'https://hqporner.com/'
#         }
#     }

#     progress_bar = st.progress(0)
#     status_text = st.empty()

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         for idx, url in enumerate(urls):
#             url = url.strip()
#             if not url:
#                 continue

#             status_text.text(f"Extracting ({idx + 1}/{len(urls)}): {url}")

#             try:
#                 info = ydl.extract_info(url, download=False)
                
#                 title = info.get('title', 'Video')
#                 uploader = info.get('uploader') or info.get('creator') or "Unknown"
#                 download_url = info.get('url')
#                 height = info.get('height')
#                 resolution = f"{height}p" if height else "HD"

#                 if not download_url:
#                     raise Exception("Direct MP4 URL extract nahi ho paya (Cloud IP block ho sakta hai).")

#                 results.append(VideoResult(title, uploader, download_url, resolution, url))

#             except Exception as e:
#                 errors.append(f"{url} -> Error: {str(e)}")

#             progress_bar.progress((idx + 1) / len(urls))

#     status_text.text("Process Complete!")
#     return results, errors

# # --- UI Layout ---
# st.title("🎬 Video Downloader Web App")
# st.write("Neeche diye gaye box mein video URLs paste karein (har line mein ek URL).")

# urls_input = st.text_area("Video URLs:", height=150, placeholder="https://hqporner.com/hdporn/...\nhttps://www.eporner.com/...")

# if st.button("Extract Videos", type="primary"):
#     url_list = [line.strip() for line in urls_input.split("\n") if line.strip()]
    
#     if not url_list:
#         st.warning("Kripya kam se kam ek URL enter karein.")
#     else:
#         with st.spinner("Links extract kiye ja rahe hain..."):
#             extracted_videos, failed_urls = extract_with_ytdlp(url_list)

#         if extracted_videos:
#             st.success(f"{len(extracted_videos)} videos ready hain!")
#             for vid in extracted_videos:
#                 with st.container(border=True):
#                     st.subheader(vid.title)
#                     st.caption(f"Uploader/Model: {vid.uploader} | Quality: {vid.resolution}")
#                     st.link_button(f"⬇️ Download MP4 ({vid.resolution})", vid.download_url)

#         if failed_urls:
#             st.error("Kuch links fail ho gaye:")
#             for err in failed_urls:
#                 st.write(f"- {err}")








# import streamlit as st
# import requests
# import shutil
# import ssl
# import re
# from dataclasses import dataclass
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.firefox.options import Options

# # Page Configuration
# st.set_page_config(page_title="Video Link Extractor & Downloader", page_icon="🎬", layout="centered")

# @dataclass
# class VideoResult:
#     title: str
#     model: str
#     download_url: str
#     source_url: str

# def format_name(file_name: str) -> str:
#     filter_chars = [',', '/', ';', '-']
#     filter_expressions = ['\\', '?', '!', ':', '\'']
#     file_name = file_name.lower()
#     file_name = file_name.translate(str.maketrans({char: ' ' for char in filter_chars}))
#     file_name = file_name.translate(str.maketrans({char: '' for char in filter_expressions}))
#     words = file_name.split()
#     return "-".join(words) if words else "video"

# def get_firefox_driver():
#     options = Options()
#     options.add_argument("--headless")
#     options.set_preference("browser.privatebrowsing.autostart", True)
    
#     # Linux server par firefox-esr ka exact path dhoondhne ke liye
#     firefox_bin = shutil.which("firefox-esr") or shutil.which("firefox")
#     if firefox_bin:
#         options.binary_location = firefox_bin
        
#     return webdriver.Firefox(options=options)
# def extract_video_info(urls):
#     results = []
#     errors = []
    
#     browser_needed = any("hqporner" in u for u in urls)
#     ff_driver = None

#     if browser_needed:
#         try:
#             ff_driver = get_firefox_driver()
#         except Exception as e:
#             st.error(f"Browser start nahi ho paya (Server par Firefox/Geckodriver check karein): {e}")
#             return results, urls

#     progress_bar = st.progress(0)
#     status_text = st.empty()

#     for idx, url in enumerate(urls):
#         url = url.strip()
#         if not url:
#             continue
            
#         status_text.text(f"Processing ({idx + 1}/{len(urls)}): {url}")
        
#         try:
#             html = requests.get(url, timeout=15)
#             bs = BeautifulSoup(html.text, 'html.parser')

#             # 1. Eporner Logic
#             if "eporner.com" in url:
#                 videos = bs.find_all('a', {'href': re.compile('1440p.mp4')})
#                 if not videos:
#                     videos = bs.find_all('a', {'href': re.compile('1080p.mp4')})
                
#                 if not videos:
#                     raise Exception("1440p ya 1080p video link nahi mila.")

#                 pornstars = bs.find_all('li', {'class': re.compile('vit-pornstar starw')})
#                 pornstar_names = pornstars[0].get_text().strip() if pornstars else "Unknown"

#                 download_url = "https://eporner.com" + videos[0].attrs['href']
#                 video_info = bs.find_all('div', {'id': 'video-info'})[0]
#                 video_title_arr = video_info.find_all('h1')[0].get_text().split(" ")
#                 video_title = " ".join(video_title_arr[:-1]).strip()

#                 results.append(VideoResult(video_title, pornstar_names, download_url, url))

#             # 2. HQPorner Logic
#             elif "hqporner.com" in url:
#                 error_section = bs.find_all('section', {'class': 'box highlight'})
                
#                 if len(error_section) > 0:
#                     search_query = url.replace("https://hqporner.com/hdporn/", "")
#                     search_query = search_query[6:-5].replace("_", "+").replace("-", "+")
#                     ff_driver.get("https://hqporner.com/?q=" + search_query)
#                     ff_driver.find_element(By.CLASS_NAME, "non-overlay").click()
#                     ff_driver.implicitly_wait(2)
#                     page_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
#                 else:
#                     page_bs = bs

#                 iframe = page_bs.find_all('iframe', {'src': re.compile("mydaddy.cc")})
#                 video_title = page_bs.find_all('h1', {'class': 'main-h1'})[0].get_text().strip()
#                 pornstars = page_bs.find_all('li', {'class': 'icon fa-star-o'})
#                 pornstar_names = pornstars[0].getText().replace("featuring ", "").replace(",", " and").strip() if pornstars else "Unknown"

#                 source = "https:" + iframe[0].attrs['src']
#                 ff_driver.get(source)
#                 ff_driver.implicitly_wait(2)
                
#                 iframe_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
#                 videos = iframe_bs.find_all("source", {'src': re.compile("1080.mp4")})
#                 download_url = "https:" + videos[-1]['src']

#                 results.append(VideoResult(video_title, pornstar_names, download_url, url))

#             else:
#                 errors.append(f"Unsupported URL: {url}")

#         except Exception as e:
#             errors.append(f"{url} -> Error: {str(e)}")

#         progress_bar.progress((idx + 1) / len(urls))

#     if ff_driver:
#         ff_driver.quit()
        
#     status_text.text("Process Complete!")
#     return results, errors

# # --- UI Layout ---
# st.title("🎬 Video Downloader Web App")
# st.write("Neeche diye gaye box mein video URLs paste karein (har line mein ek URL).")

# urls_input = st.text_area("Video URLs:", height=150, placeholder="https://www.eporner.com/...\nhttps://hqporner.com/...")

# if st.button("Extract Videos", type="primary"):
#     url_list = [line.strip() for line in urls_input.split("\n") if line.strip()]
    
#     if not url_list:
#         st.warning("Kripya kam se kam ek URL enter karein.")
#     else:
#         with st.spinner("Links fetch kiye ja rahe hain..."):
#             extracted_videos, failed_urls = extract_video_info(url_list)

#         if extracted_videos:
#             st.success(f"{len(extracted_videos)} videos ready hain!")
#             for vid in extracted_videos:
#                 with st.container(border=True):
#                     st.subheader(vid.title)
#                     st.caption(f"Model: {vid.model}")
#                     # Direct Download Button
#                     st.link_button("⬇️ Download MP4 (HD)", vid.download_url)

#         if failed_urls:
#             st.error("Kuch links fail ho gaye:")
#             for err in failed_urls:
#                 st.write(f"- {err}")




# caklllllllllllllllllllllllll

# import streamlit as st
# import requests
# import re
# import time
# import shutil
# from dataclasses import dataclass
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.firefox.options import Options

# # Page Configuration
# st.set_page_config(page_title="Video Link Extractor & Downloader", page_icon="🎬", layout="centered")

# HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
#     "Accept-Language": "en-US,en;q=0.5",
#     "Referer": "https://hqporner.com/"
# }

# @dataclass
# class VideoResult:
#     title: str
#     model: str
#     download_url: str
#     source_url: str

# def get_firefox_driver():
#     options = Options()
#     options.add_argument("--headless")
#     options.set_preference("browser.privatebrowsing.autostart", True)
#     options.set_preference("general.useragent.override", HEADERS["User-Agent"])
    
#     firefox_bin = shutil.which("firefox-esr") or shutil.which("firefox")
#     if firefox_bin:
#         options.binary_location = firefox_bin
        
#     return webdriver.Firefox(options=options)

# def extract_video_info(urls):
#     results = []
#     errors = []
    
#     browser_needed = any("hqporner" in u for u in urls)
#     ff_driver = None

#     if browser_needed:
#         try:
#             ff_driver = get_firefox_driver()
#         except Exception as e:
#             st.error(f"Browser start nahi ho paya: {e}")
#             return results, urls

#     progress_bar = st.progress(0)
#     status_text = st.empty()

#     for idx, url in enumerate(urls):
#         url = url.strip()
#         if not url:
#             continue
            
#         status_text.text(f"Processing ({idx + 1}/{len(urls)}): {url}")
        
#         try:
#             html = requests.get(url, headers=HEADERS, timeout=15)
#             if html.status_code != 200:
#                 raise Exception(f"Website ne access block kiya (Status Code: {html.status_code})")
                
#             bs = BeautifulSoup(html.text, 'html.parser')

#             # 1. Eporner Logic
#             if "eporner.com" in url:
#                 videos = bs.find_all('a', {'href': re.compile('1440p.mp4')})
#                 if not videos:
#                     videos = bs.find_all('a', {'href': re.compile('1080p.mp4')})
#                 if not videos:
#                     videos = bs.find_all('a', {'href': re.compile('.mp4')})
                
#                 if not videos:
#                     raise Exception("Koi bhi MP4 download link nahi mila (Cloud IP block ho sakta hai).")

#                 pornstars = bs.find_all('li', {'class': re.compile('vit-pornstar starw')})
#                 pornstar_names = pornstars[0].get_text().strip() if pornstars else "Unknown"

#                 download_url = "https://eporner.com" + videos[0].attrs['href']
#                 video_info = bs.find_all('div', {'id': 'video-info'})
#                 if video_info and video_info[0].find_all('h1'):
#                     video_title_arr = video_info[0].find_all('h1')[0].get_text().split(" ")
#                     video_title = " ".join(video_title_arr[:-1]).strip()
#                 else:
#                     video_title = "Eporner Video"

#                 results.append(VideoResult(video_title, pornstar_names, download_url, url))

#             # 2. HQPorner Logic
#             elif "hqporner.com" in url:
#                 error_section = bs.find_all('section', {'class': 'box highlight'})
                
#                 if len(error_section) > 0:
#                     search_query = url.replace("https://hqporner.com/hdporn/", "")
#                     search_query = search_query[6:-5].replace("_", "+").replace("-", "+")
#                     ff_driver.get("https://hqporner.com/?q=" + search_query)
#                     time.sleep(2)
#                     links = ff_driver.find_elements(By.CLASS_NAME, "non-overlay")
#                     if not links:
#                         raise Exception("Search results nahi mile.")
#                     links[0].click()
#                     time.sleep(2)
#                     page_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
#                 else:
#                     page_bs = bs

#                 iframe = page_bs.find_all('iframe', {'src': re.compile("mydaddy.cc")})
#                 if not iframe:
#                     # Agar requests se iframe nahi mila toh Selenium se page load karke try karein
#                     ff_driver.get(url)
#                     time.sleep(3)
#                     page_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
#                     iframe = page_bs.find_all('iframe', {'src': re.compile("mydaddy.cc")})

#                 if not iframe:
#                     raise Exception("Video player (iframe) nahi mila. Server IP block ho sakti hai.")

#                 h1_tags = page_bs.find_all('h1', {'class': 'main-h1'})
#                 video_title = h1_tags[0].get_text().strip() if h1_tags else "HQPorner Video"
                
#                 pornstars = page_bs.find_all('li', {'class': 'icon fa-star-o'})
#                 pornstar_names = pornstars[0].getText().replace("featuring ", "").replace(",", " and").strip() if pornstars else "Unknown"

#                 source = iframe[0].attrs['src']
#                 if source.startswith("//"):
#                     source = "https:" + source

#                 ff_driver.get(source)
#                 time.sleep(3)  # Video player load hone ka wait
                
#                 iframe_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
#                 videos = iframe_bs.find_all("source", {'src': re.compile("1080.mp4")})
#                 if not videos:
#                     videos = iframe_bs.find_all("source", {'src': re.compile(".mp4")})
                
#                 if not videos:
#                     raise Exception("Player ke andar MP4 source file nahi mili.")

#                 vid_src = videos[-1]['src']
#                 download_url = ("https:" + vid_src) if vid_src.startswith("//") else vid_src

#                 results.append(VideoResult(video_title, pornstar_names, download_url, url))

#             else:
#                 errors.append(f"Unsupported URL: {url}")

#         except Exception as e:
#             errors.append(f"{url} -> Error: {str(e)}")

#         progress_bar.progress((idx + 1) / len(urls))

#     if ff_driver:
#         ff_driver.quit()
        
#     status_text.text("Process Complete!")
#     return results, errors

# # --- UI Layout ---
# st.title("🎬 Video Downloader Web App")
# st.write("Neeche diye gaye box mein video URLs paste karein (har line mein ek URL).")

# urls_input = st.text_area("Video URLs:", height=150, placeholder="https://www.eporner.com/...\nhttps://hqporner.com/...")

# if st.button("Extract Videos", type="primary"):
#     url_list = [line.strip() for line in urls_input.split("\n") if line.strip()]
    
#     if not url_list:
#         st.warning("Kripya kam se kam ek URL enter karein.")
#     else:
#         with st.spinner("Links fetch kiye ja rahe hain..."):
#             extracted_videos, failed_urls = extract_video_info(url_list)

#         if extracted_videos:
#             st.success(f"{len(extracted_videos)} videos ready hain!")
#             for vid in extracted_videos:
#                 with st.container(border=True):
#                     st.subheader(vid.title)
#                     st.caption(f"Model: {vid.model}")
#                     st.link_button("⬇️ Download MP4 (HD)", vid.download_url)

#         if failed_urls:
#             st.error("Kuch links fail ho gaye:")
#             for err in failed_urls:
#                 st.write(f"- {err}")



# # ,jsddddddddddddddddd

# import streamlit as st
# import requests
# import re
# import time
# import shutil
# from dataclasses import dataclass
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.firefox.options import Options

# # Page Configuration
# st.set_page_config(page_title="Video Link Extractor & Downloader", page_icon="🎬", layout="centered")

# HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
#     "Accept-Language": "en-US,en;q=0.5",
#     "Referer": "https://hqporner.com/"
# }

# @dataclass
# class VideoResult:
#     title: str
#     model: str
#     download_url: str
#     source_url: str

# def get_firefox_driver():
#     options = Options()
#     options.add_argument("--headless")
#     options.set_preference("browser.privatebrowsing.autostart", True)
#     options.set_preference("general.useragent.override", HEADERS["User-Agent"])
    
#     firefox_bin = shutil.which("firefox-esr") or shutil.which("firefox")
#     if firefox_bin:
#         options.binary_location = firefox_bin
        
#     return webdriver.Firefox(options=options)

# def extract_video_info(urls):
#     results = []
#     errors = []
    
#     browser_needed = any("hqporner" in u for u in urls)
#     ff_driver = None

#     if browser_needed:
#         try:
#             ff_driver = get_firefox_driver()
#         except Exception as e:
#             st.error(f"Browser start nahi ho paya: {e}")
#             return results, urls

#     progress_bar = st.progress(0)
#     status_text = st.empty()

#     for idx, url in enumerate(urls):
#         url = url.strip()
#         if not url:
#             continue
            
#         status_text.text(f"Processing ({idx + 1}/{len(urls)}): {url}")
        
#         try:
#             html = requests.get(url, headers=HEADERS, timeout=15)
#             if html.status_code != 200:
#                 raise Exception(f"Website ne access block kiya (Status Code: {html.status_code})")
                
#             bs = BeautifulSoup(html.text, 'html.parser')

#             # 1. Eporner Logic
#             if "eporner.com" in url:
#                 videos = bs.find_all('a', {'href': re.compile('1440p.mp4')})
#                 if not videos:
#                     videos = bs.find_all('a', {'href': re.compile('1080p.mp4')})
#                 if not videos:
#                     videos = bs.find_all('a', {'href': re.compile('.mp4')})
                
#                 if not videos:
#                     raise Exception("Koi bhi MP4 download link nahi mila.")

#                 pornstars = bs.find_all('li', {'class': re.compile('vit-pornstar starw')})
#                 pornstar_names = pornstars[0].get_text().strip() if pornstars else "Unknown"

#                 download_url = "https://eporner.com" + videos[0].attrs['href']
#                 video_info = bs.find_all('div', {'id': 'video-info'})
#                 if video_info and video_info[0].find_all('h1'):
#                     video_title_arr = video_info[0].find_all('h1')[0].get_text().split(" ")
#                     video_title = " ".join(video_title_arr[:-1]).strip()
#                 else:
#                     video_title = "Eporner Video"

#                 results.append(VideoResult(video_title, pornstar_names, download_url, url))

#             # 2. HQPorner Logic
#             elif "hqporner.com" in url:
#                 error_section = bs.find_all('section', {'class': 'box highlight'})
                
#                 if len(error_section) > 0:
#                     search_query = url.replace("https://hqporner.com/hdporn/", "")
#                     search_query = search_query[6:-5].replace("_", "+").replace("-", "+")
#                     ff_driver.get("https://hqporner.com/?q=" + search_query)
#                     time.sleep(2)
#                     links = ff_driver.find_elements(By.CLASS_NAME, "non-overlay")
#                     if not links:
#                         raise Exception("Search results nahi mile.")
#                     links[0].click()
#                     time.sleep(2)
#                     page_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
#                 else:
#                     page_bs = bs

#                 iframe = page_bs.find_all('iframe', {'src': re.compile("mydaddy.cc")})
#                 if not iframe:
#                     ff_driver.get(url)
#                     time.sleep(3)
#                     page_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
#                     iframe = page_bs.find_all('iframe', {'src': re.compile("mydaddy.cc")})

#                 if not iframe:
#                     raise Exception("Video player (iframe) nahi mila.")

#                 h1_tags = page_bs.find_all('h1', {'class': 'main-h1'})
#                 video_title = h1_tags[0].get_text().strip() if h1_tags else "HQPorner Video"
                
#                 pornstars = page_bs.find_all('li', {'class': 'icon fa-star-o'})
#                 pornstar_names = pornstars[0].getText().replace("featuring ", "").replace(",", " and").strip() if pornstars else "Unknown"

#                 source = iframe[0].attrs['src']
#                 if source.startswith("//"):
#                     source = "https:" + source

#                 ff_driver.get(source)
#                 time.sleep(4)
                
#                 page_html = ff_driver.page_source
#                 iframe_bs = BeautifulSoup(page_html, 'html.parser')
                
#                 videos = iframe_bs.find_all("source", {'src': re.compile(r"\.mp4")})
#                 if not videos:
#                     videos = iframe_bs.find_all("video", {'src': re.compile(r"\.mp4")})

#                 if videos:
#                     vid_src = videos[-1]['src']
#                 else:
#                     mp4_matches = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+\.mp4(?:\?[^"\'\s<>]*)?', page_html)
#                     if not mp4_matches:
#                         raise Exception("Player ke andar MP4 source file nahi mili (Bot protection ya JS block).")
#                     vid_src = mp4_matches[-1]

#                 download_url = ("https:" + vid_src) if vid_src.startswith("//") else vid_src

#                 results.append(VideoResult(video_title, pornstar_names, download_url, url))

#             else:
#                 errors.append(f"Unsupported URL: {url}")

#         except Exception as e:
#             errors.append(f"{url} -> Error: {str(e)}")

#         progress_bar.progress((idx + 1) / len(urls))

#     if ff_driver:
#         ff_driver.quit()
        
#     status_text.text("Process Complete!")
#     return results, errors

# # --- UI Layout ---
# st.title("🎬 Video Downloader Web App")
# st.write("Neeche diye gaye box mein video URLs paste karein (har line mein ek URL).")

# urls_input = st.text_area("Video URLs:", height=150, placeholder="https://www.eporner.com/...\nhttps://hqporner.com/...")

# if st.button("Extract Videos", type="primary"):
#     url_list = [line.strip() for line in urls_input.split("\n") if line.strip()]
    
#     if not url_list:
#         st.warning("Kripya kam se kam ek URL enter karein.")
#     else:
#         with st.spinner("Links fetch kiye ja rahe hain..."):
#             extracted_videos, failed_urls = extract_video_info(url_list)

#         if extracted_videos:
#             st.success(f"{len(extracted_videos)} videos ready hain!")
#             for vid in extracted_videos:
#                 with st.container(border=True):
#                     st.subheader(vid.title)
#                     st.caption(f"Model: {vid.model}")
#                     st.link_button("⬇️ Download MP4 (HD)", vid.download_url)

#         if failed_urls:
#             st.error("Kuch links fail ho gaye:")
#             for err in failed_urls:
#                 st.write(f"- {err}")