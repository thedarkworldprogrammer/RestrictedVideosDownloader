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



# ,jsddddddddddddddddd

import streamlit as st
import requests
import re
import time
import shutil
from dataclasses import dataclass
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

# Page Configuration
st.set_page_config(page_title="Video Link Extractor & Downloader", page_icon="🎬", layout="centered")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://hqporner.com/"
}

@dataclass
class VideoResult:
    title: str
    model: str
    download_url: str
    source_url: str

def get_firefox_driver():
    options = Options()
    options.add_argument("--headless")
    options.set_preference("browser.privatebrowsing.autostart", True)
    options.set_preference("general.useragent.override", HEADERS["User-Agent"])
    
    firefox_bin = shutil.which("firefox-esr") or shutil.which("firefox")
    if firefox_bin:
        options.binary_location = firefox_bin
        
    return webdriver.Firefox(options=options)

def extract_video_info(urls):
    results = []
    errors = []
    
    browser_needed = any("hqporner" in u for u in urls)
    ff_driver = None

    if browser_needed:
        try:
            ff_driver = get_firefox_driver()
        except Exception as e:
            st.error(f"Browser start nahi ho paya: {e}")
            return results, urls

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, url in enumerate(urls):
        url = url.strip()
        if not url:
            continue
            
        status_text.text(f"Processing ({idx + 1}/{len(urls)}): {url}")
        
        try:
            html = requests.get(url, headers=HEADERS, timeout=15)
            if html.status_code != 200:
                raise Exception(f"Website ne access block kiya (Status Code: {html.status_code})")
                
            bs = BeautifulSoup(html.text, 'html.parser')

            # 1. Eporner Logic
            if "eporner.com" in url:
                videos = bs.find_all('a', {'href': re.compile('1440p.mp4')})
                if not videos:
                    videos = bs.find_all('a', {'href': re.compile('1080p.mp4')})
                if not videos:
                    videos = bs.find_all('a', {'href': re.compile('.mp4')})
                
                if not videos:
                    raise Exception("Koi bhi MP4 download link nahi mila.")

                pornstars = bs.find_all('li', {'class': re.compile('vit-pornstar starw')})
                pornstar_names = pornstars[0].get_text().strip() if pornstars else "Unknown"

                download_url = "https://eporner.com" + videos[0].attrs['href']
                video_info = bs.find_all('div', {'id': 'video-info'})
                if video_info and video_info[0].find_all('h1'):
                    video_title_arr = video_info[0].find_all('h1')[0].get_text().split(" ")
                    video_title = " ".join(video_title_arr[:-1]).strip()
                else:
                    video_title = "Eporner Video"

                results.append(VideoResult(video_title, pornstar_names, download_url, url))

            # 2. HQPorner Logic
            elif "hqporner.com" in url:
                error_section = bs.find_all('section', {'class': 'box highlight'})
                
                if len(error_section) > 0:
                    search_query = url.replace("https://hqporner.com/hdporn/", "")
                    search_query = search_query[6:-5].replace("_", "+").replace("-", "+")
                    ff_driver.get("https://hqporner.com/?q=" + search_query)
                    time.sleep(2)
                    links = ff_driver.find_elements(By.CLASS_NAME, "non-overlay")
                    if not links:
                        raise Exception("Search results nahi mile.")
                    links[0].click()
                    time.sleep(2)
                    page_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
                else:
                    page_bs = bs

                iframe = page_bs.find_all('iframe', {'src': re.compile("mydaddy.cc")})
                if not iframe:
                    ff_driver.get(url)
                    time.sleep(3)
                    page_bs = BeautifulSoup(ff_driver.page_source, 'html.parser')
                    iframe = page_bs.find_all('iframe', {'src': re.compile("mydaddy.cc")})

                if not iframe:
                    raise Exception("Video player (iframe) nahi mila.")

                h1_tags = page_bs.find_all('h1', {'class': 'main-h1'})
                video_title = h1_tags[0].get_text().strip() if h1_tags else "HQPorner Video"
                
                pornstars = page_bs.find_all('li', {'class': 'icon fa-star-o'})
                pornstar_names = pornstars[0].getText().replace("featuring ", "").replace(",", " and").strip() if pornstars else "Unknown"

                source = iframe[0].attrs['src']
                if source.startswith("//"):
                    source = "https:" + source

                ff_driver.get(source)
                time.sleep(4)
                
                page_html = ff_driver.page_source
                iframe_bs = BeautifulSoup(page_html, 'html.parser')
                
                videos = iframe_bs.find_all("source", {'src': re.compile(r"\.mp4")})
                if not videos:
                    videos = iframe_bs.find_all("video", {'src': re.compile(r"\.mp4")})

                if videos:
                    vid_src = videos[-1]['src']
                else:
                    mp4_matches = re.findall(r'(?:https?:)?//[a-zA-Z0-9./_-]+\.mp4(?:\?[^"\'\s<>]*)?', page_html)
                    if not mp4_matches:
                        raise Exception("Player ke andar MP4 source file nahi mili (Bot protection ya JS block).")
                    vid_src = mp4_matches[-1]

                download_url = ("https:" + vid_src) if vid_src.startswith("//") else vid_src

                results.append(VideoResult(video_title, pornstar_names, download_url, url))

            else:
                errors.append(f"Unsupported URL: {url}")

        except Exception as e:
            errors.append(f"{url} -> Error: {str(e)}")

        progress_bar.progress((idx + 1) / len(urls))

    if ff_driver:
        ff_driver.quit()
        
    status_text.text("Process Complete!")
    return results, errors

# --- UI Layout ---
st.title("🎬 Video Downloader Web App")
st.write("Neeche diye gaye box mein video URLs paste karein (har line mein ek URL).")

urls_input = st.text_area("Video URLs:", height=150, placeholder="https://www.eporner.com/...\nhttps://hqporner.com/...")

if st.button("Extract Videos", type="primary"):
    url_list = [line.strip() for line in urls_input.split("\n") if line.strip()]
    
    if not url_list:
        st.warning("Kripya kam se kam ek URL enter karein.")
    else:
        with st.spinner("Links fetch kiye ja rahe hain..."):
            extracted_videos, failed_urls = extract_video_info(url_list)

        if extracted_videos:
            st.success(f"{len(extracted_videos)} videos ready hain!")
            for vid in extracted_videos:
                with st.container(border=True):
                    st.subheader(vid.title)
                    st.caption(f"Model: {vid.model}")
                    st.link_button("⬇️ Download MP4 (HD)", vid.download_url)

        if failed_urls:
            st.error("Kuch links fail ho gaye:")
            for err in failed_urls:
                st.write(f"- {err}")