import os
import re
import logging
import requests
import base64
import json
import tempfile
from urllib.parse import quote
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8842926054:AAGPZJzcMB9AU8DNKHQMW1z_mxZGUpA7E6E"

GOOGLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "aerial-ceremony-497109-n6",
    "private_key_id": "7337c4ee7bb7ca10d3a5e587ecdfbf7a28a93136",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC5vGsJJW6Z+AIf\nKIUkMZKs5fKcjZnQHlPbOIcHIsacHglEg8Zf6t0dQFlpxVUzR/Ns5cmuozj4do7r\np5nP1KOfSDomBCvEphdNwDakTU6TqFSnbKDN8l2ff8kF9oRMDHjbMLrH565sMIn2\nt1jwBEwG0TPNcB01566l4j8x3yYgA5yeNn2pHi/cZA49Q1ZO0nIpCydSyg+NdoyK\nLPEKaMNmWBnVBUbIETZNtY77T7/6Bvobhfc5Gf0UCkDCJqJ9SQM5J/8PrSfD+b5U\ntUh5YBqc7qoEm4YyV3M6XKmYMS8IbVf2QQZ9u13HTi44kBPks+RLXP/s6ZT/laYg\nmuTq3pC7AgMBAAECggEAMqisfQMjpoUZdwwjPFr1CYlyYbbRdA1Bi/JgCdc3Wo9q\nsbBLZA/4HSlW+d1jvqfqQhJurt5ABKy5kJbXAfOaaTBXA9VxZqJyirdZb/jR7L4l\n0MB1H5byaDV/S8wQC3n/YLFq0GlljoayqoMZk+VoIxfeTDM/FFvLq90IpX6atHIw\nvssdLp6X2S42wX1y+XQ57osJFZGiUjdVSyAxowsK6QMvx8jgK3n1+zTSmVhZO02O\nBUHxZXsQW73p+YhyjpB27oinpe1JP2AxBW/PKy/ESUXt3hLLOgozwbP15qHyt4fx\nPKbDpYFFVi2ut7cwEjr17bKLr/A3h8SvlYuAvXMDqQKBgQDgaVSHd7mmnn84Arry\n/65OnHEd85f3MhM6x9iqKmBEgDbmbCrodzVEbSbRNEQWcKxzrTNqc20iDHqTZlM9\n31anqZRPw0vSJTxAS4J5AoHq9FiCdgvmZv64qS6hfqyT+p29toVHKL3kjJtmT9CK\nHsv6lZ3/IrcaJvpu1wLVRv+n5QKBgQDT4Wr96ohDEZxBZumnc/zrq1nPKO9UPPHt\nZoja6jhyAjaOskVWcr4MhwVxMnV6FFk7RgHo02rdFI+5ZZZLo8omTG2vzjxeIcql\n9K2NhwJmH5Fl0Cxp49DypvPrgU8x9GFqNJ6n4jBRWe8E9O/y0Qw3UvLI5lOKuqRr\ndUJxKDiMHwKBgBtoQc6ZrK7QxLDOhI6Q83TeXmJOEc067GZNagS+UCuNjSbvJv5l\nMLg+rHL4cyhacnVePd1OY5G4/G9sG9Z+pFKtv1NOgsATlBw2HKUyzTMozHaCfEmT\nYqCi6PMISYN5JDK7S+O48hgro/8G2G1F/ZuJElbKoporEILg95OcrDSRAoGAeK2I\nMcz2BTUviTSjWiO+5z+2LD6FabY4mN1wjzceJRlLl6TDx0QdKKdymxGBRaH3XMI3\n7jMUR40hexf4LWbBiWS4iIxvZ7HZaQJeIyDFZgMO3i1eToVaCgq7HOSOhcZKAaKs\nxrQWjw8pCuqzC9qzGYOeEnzVEkvRv/6OdELTSkMCgYEA3aAIahSbCNyiZEhkxv/y\nL/FwHSMJ9mwLAQCJL6Y667YyNiytp8ceD3G4F3Wt+JeJi4ymPeczndd3VL3LhvDk\nLYONga1LM2dx5uFD5ajjYpKab3TulU+ELYPVhxIJdTLEuRW9YLaUqSlFbhX9QNlQ\nM7C25N6J8RppAE5yPtbdvWg=\n-----END PRIVATE KEY-----\n",
    "client_email": "ayub-747@aerial-ceremony-497109-n6.iam.gserviceaccount.com",
    "client_id": "106810173149680129885",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/ayub-747%40aerial-ceremony-497109-n6.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# ─────────────────────────────────────────
# GOOGLE ACCESS TOKEN OLISH
# ─────────────────────────────────────────
def get_google_token():
    try:
        import jwt
        import time
        now = int(time.time())
        payload = {
            "iss": GOOGLE_CREDENTIALS["client_email"],
            "scope": "https://www.googleapis.com/auth/cloud-vision",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600
        }
        private_key = GOOGLE_CREDENTIALS["private_key"]
        token = jwt.encode(payload, private_key, algorithm="RS256")
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": token
        })
        return resp.json().get("access_token")
    except Exception as e:
        logger.error(f"Token error: {e}")
        return None

# ─────────────────────────────────────────
# VIDEO DAN KADR OLISH
# ─────────────────────────────────────────
def get_video_frame(url):
    """Videodan birinchi kadrni oladi"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'writethumbnail': True,
        'outtmpl': '/tmp/frame',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', '')
            description = info.get('description', '')
            # Thumbnail faylini topish
            for ext in ['jpg', 'jpeg', 'png', 'webp']:
                thumb_path = f'/tmp/frame.{ext}'
                if os.path.exists(thumb_path):
                    return thumb_path, title, description
        return None, title, description
    except Exception as e:
        logger.error(f"Frame error: {e}")
        return None, None, None

# ─────────────────────────────────────────
# GOOGLE VISION - RASM TAHLIL
# ─────────────────────────────────────────
def analyze_image_with_vision(image_path):
    """Google Vision API orqali rasmdan matn va ob'ektlarni aniqlaydi"""
    try:
        access_token = get_google_token()
        if not access_token:
            return None

        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        request_body = {
            "requests": [{
                "image": {"content": image_data},
                "features": [
                    {"type": "TEXT_DETECTION", "maxResults": 10},
                    {"type": "LABEL_DETECTION", "maxResults": 10},
                    {"type": "WEB_DETECTION", "maxResults": 5}
                ]
            }]
        }

        resp = requests.post(
            "https://vision.googleapis.com/v1/images:annotate",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=request_body,
            timeout=15
        )

        result = resp.json()
        if "responses" not in result:
            return None

        response = result["responses"][0]
        detected_info = []

        # Veb qidiruvdan kino nomi
        web = response.get("webDetection", {})
        for entity in web.get("webEntities", []):
            desc = entity.get("description", "")
            score = entity.get("score", 0)
            if score > 0.5 and len(desc) > 2:
                detected_info.append(desc)

        # Rasmdan matn
        text_annotations = response.get("textAnnotations", [])
        if text_annotations:
            full_text = text_annotations[0].get("description", "")
            detected_info.append(full_text[:100])

        return detected_info if detected_info else None

    except Exception as e:
        logger.error(f"Vision error: {e}")
        return None

def extract_movie_from_vision(vision_data, fallback_title=""):
    """Vision natijasidan kino nomini ajratib oladi"""
    if not vision_data:
        return clean_title(fallback_title)

    # Birinchi web entity odatda eng aniq natija
    for item in vision_data[:3]:
        cleaned = clean_title(item)
        if cleaned and len(cleaned) > 2:
            return cleaned

    return clean_title(fallback_title)

def clean_title(title):
    """Sarlavhadan keraksiz narsalarni o'chiradi"""
    if not title:
        return ""
    # Hashtagdan oldingi qismni ol
    title = re.split(r'#', title)[0].strip()
    # Emoji va maxsus belgilarni o'chir
    title = re.sub(r'[^\w\s\-:]', ' ', title)
    # Keraksiz so'zlar
    stop_words = ['kino', 'film', 'movie', 'uzbek', 'tilida', 'tarjima',
                  'review', 'top', 'yangi', 'full', 'hd', 'trailer',
                  'tiktok', 'instagram', 'youtube', 'qism', 'serial']
    words = [w for w in title.split() if w.lower() not in stop_words and len(w) > 1]
    return ' '.join(words[:5]).strip()

# ─────────────────────────────────────────
# ASILMEDIA
# ─────────────────────────────────────────
def search_asilmedia(query):
    try:
        clean_query = re.sub(r'[^\w\s]', ' ', query)[:50].strip()
        search_url = f"https://www.google.com/search?q=site:asilmedia.org+{quote(clean_query)}&num=5"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/url?q=" in href:
                href = href.split("/url?q=")[1].split("&")[0]
            if "asilmedia.org" in href and ".html" in href and href.startswith("http"):
                title = a.get_text(strip=True)
                if len(title) > 5 and href not in [r["url"] for r in results]:
                    results.append({"title": title[:100], "url": href})
                if len(results) >= 5:
                    break
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def get_movie_links(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        title_el = soup.select_one("h1")
        raw_title = title_el.get_text(strip=True) if title_el else "Kino"
        clean = re.sub(
            r'\s*(Uzbek tilida|tarjima|Full HD|tas-ix|skachat|HD|kino).*',
            '', raw_title, flags=re.IGNORECASE
        ).strip()
        desc = ""
        for sel in [".full-text", ".short-text", "[itemprop='description']"]:
            el = soup.select_one(sel)
            if el:
                desc = el.get_text(strip=True)[:250]
                break
        if not desc:
            for p in soup.find_all("p"):
                t = p.get_text(strip=True)
                if len(t) > 60:
                    desc = t[:250]
                    break
        img_el = soup.select_one("img[src*='/uploads/']")
        img_url = ""
        if img_el:
            img_url = img_el.get("src", "")
            if not img_url.startswith("http"):
                img_url = "https://asilmedia.org" + img_url
        watch_720 = url
        download_720 = url
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True).lower()
            if not href.startswith("http"):
                href = "https://asilmedia.org" + href
            if "720" in text:
                if any(w in text for w in ["ko'rish", "watch", "onlayn"]):
                    watch_720 = href
                if any(w in text for w in ["skachat", "yuklab", "download"]):
                    download_720 = href
        return {
            "title": clean or raw_title[:60],
            "desc": desc,
            "img": img_url,
            "watch_url": watch_720,
            "download_url": download_720,
            "page_url": url
        }
    except Exception as e:
        logger.error(f"Links error: {e}")
        return None

def detect_platform(url):
    if "tiktok.com" in url:
        return "tiktok"
    elif "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    return None

async def send_movie(update, movie, extra_results=None):
    btns = [
        [InlineKeyboardButton("▶️ 720p Onlayn Ko'rish", url=movie["watch_url"])],
        [InlineKeyboardButton("⬇️ 720p Yuklab Olish", url=movie["download_url"])],
        [InlineKeyboardButton("🌐 AsilMedia Sahifasi", url=movie["page_url"])],
    ]
    if extra_results:
        for r in extra_results[1:3]:
            btns.append([InlineKeyboardButton(f"📽 {r['title'][:45]}", url=r["url"])])
    keyboard = InlineKeyboardMarkup(btns)
    caption = (
        f"🎬 *{movie['title']}*\n\n"
        f"📝 {movie['desc']}\n\n"
        f"📺 Sifat: 480p | *720p* | 1080p\n"
        f"🌐 AsilMedia.org"
    )
    if movie.get("img"):
        try:
            await update.message.reply_photo(photo=movie["img"], caption=caption, parse_mode="Markdown", reply_markup=keyboard)
            return
        except Exception:
            pass
    await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=keyboard)

async def search_and_send(update, query):
    msg = await update.message.reply_text(f"🔍 *{query[:40]}* — qidirilmoqda...", parse_mode="Markdown")
    results = search_asilmedia(query)
    if not results:
        await msg.edit_text(f"❌ *{query[:40]}* AsilMedia da topilmadi!\n\n/kino [nom] deb sinab ko'ring", parse_mode="Markdown")
        return
    movie = get_movie_links(results[0]["url"])
    await msg.delete()
    if movie:
        await send_movie(update, movie, results)
    else:
        btns = [[InlineKeyboardButton(f"🎬 {r['title'][:50]}", url=r["url"])] for r in results]
        await update.message.reply_text("🔍 Topildi:", reply_markup=InlineKeyboardMarkup(btns))

# ─────────────────────────────────────────
# HANDLERLAR
# ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Salom! Men kino botman!*\n\n"
        "🎬 *Qanday ishlaydi:*\n\n"
        "📱 TikTok/Instagram/YouTube linkini yuboring\n"
        "→ Bot AI yordamida video kadrini tahlil qiladi\n"
        "→ Kino nomini aniqlab AsilMedia dan topadi\n"
        "→ *720p Ko'rish* va *Yuklab olish* tugmalarini beradi\n\n"
        "✍️ Yoki kino nomini yozing: `/kino Avatar`",
        parse_mode="Markdown"
    )

async def kino_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kino nomini yozing: /kino Avatar")
        return
    await search_and_send(update, " ".join(context.args))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    urls = re.findall(r'https?://[^\s]+', text)

    if urls:
        url = urls[0]
        platform = detect_platform(url)

        if platform:
            msg = await update.message.reply_text(
                f"🎬 {platform.upper()} video tahlil qilinmoqda...\n"
                "🤖 AI kino nomini aniqlamoqda..."
            )
            # Video thumbnail va ma'lumot olish
            frame_path, raw_title, description = get_video_frame(url)

            movie_name = None

            # 1. Google Vision orqali tahlil
            if frame_path:
                vision_data = analyze_image_with_vision(frame_path)
                movie_name = extract_movie_from_vision(vision_data, raw_title)
                try:
                    os.remove(frame_path)
                except:
                    pass

            # 2. Vision ishlamasa sarlavhadan olish
            if not movie_name and raw_title:
                movie_name = clean_title(raw_title)

            # 3. Tavsifdan olish
            if not movie_name and description:
                movie_name = clean_title(description[:100])

            if movie_name and len(movie_name) > 2:
                await msg.edit_text(
                    f"🎯 Kino nomi aniqlandi: *{movie_name}*\n"
                    f"🔍 AsilMedia dan qidirilmoqda...",
                    parse_mode="Markdown"
                )
                results = search_asilmedia(movie_name)
                if results:
                    movie = get_movie_links(results[0]["url"])
                    await msg.delete()
                    if movie:
                        await send_movie(update, movie, results)
                    else:
                        btns = [[InlineKeyboardButton(f"🎬 {r['title'][:50]}", url=r["url"])] for r in results]
                        await update.message.reply_text("🔍 Topildi:", reply_markup=InlineKeyboardMarkup(btns))
                else:
                    await msg.edit_text(
                        f"❌ *{movie_name}* AsilMedia da topilmadi!\n\n"
                        f"Qo'lda qidirish: /kino {movie_name}",
                        parse_mode="Markdown"
                    )
            else:
                await msg.edit_text(
                    "❌ Kino nomini aniqlab bo'lmadi!\n\n"
                    "Kino nomini o'zingiz yozing: /kino [nom]"
                )
        else:
            await update.message.reply_text(
                "❌ Faqat TikTok, YouTube, Instagram linklar!\n\n"
                "🎬 Kino qidirish: /kino [nom]"
            )
    else:
        if len(text) > 2:
            await search_and_send(update, text)
        else:
            await update.message.reply_text("Link yoki kino nomini yuboring!\n/kino Avatar")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("kino", kino_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
