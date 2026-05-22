import os
import re
import logging
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8842926054:AAGPZJzcMB9AU8DNKHQMW1z_mxZGUpA7E6E"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

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
        clean_title = re.sub(
            r'\s*(Uzbek tilida|O\'zbekcha tarjima|tarjima|Full HD|tas-ix|skachat|HD|kino|Barcha qismlar).*',
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
            "title": clean_title or raw_title[:60],
            "desc": desc,
            "img": img_url,
            "watch_url": watch_720,
            "download_url": download_720,
            "page_url": url
        }
    except Exception as e:
        logger.error(f"Links error: {e}")
        return None

def get_video_title_sync(url):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', ''), info.get('description', '')
    except Exception as e:
        logger.error(f"Title error: {e}")
        return None, None

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
        await msg.edit_text(f"❌ *{query[:40]}* AsilMedia da topilmadi!", parse_mode="Markdown")
        return
    movie = get_movie_links(results[0]["url"])
    await msg.delete()
    if movie:
        await send_movie(update, movie, results)
    else:
        btns = [[InlineKeyboardButton(f"🎬 {r['title'][:50]}", url=r["url"])] for r in results]
        await update.message.reply_text("🔍 Topildi:", reply_markup=InlineKeyboardMarkup(btns))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Salom! Men kino botman!*\n\n"
        "📌 *Qanday ishlaydi:*\n\n"
        "🎵 TikTok/Instagram/YouTube linkini yuboring\n"
        "→ Bot kino nomini aniqlab AsilMedia dan topadi\n"
        "→ *720p Ko'rish* va *Yuklab olish* tugmalarini beradi\n\n"
        "🎬 Yoki kino nomini yozing\n"
        "→ `/kino Avatar`",
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
            msg = await update.message.reply_text(f"🔍 {platform.upper()} dan kino nomi aniqlanmoqda...")
            title, description = get_video_title_sync(url)
            if title:
                clean = re.sub(r'[#@|\[\](){}]', ' ', title)
                clean = re.sub(r'\s+', ' ', clean).strip()[:60]
                await msg.edit_text(f"🎬 *{clean}* — AsilMedia dan qidirilmoqda...", parse_mode="Markdown")
                results = search_asilmedia(clean)
                if not results and description:
                    results = search_asilmedia(description[:50])
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
                        f"❌ *{clean}* AsilMedia da topilmadi!\n\n"
                        f"Qo'lda qidirish: /kino {clean}",
                        parse_mode="Markdown"
                    )
            else:
                await msg.edit_text("❌ Nomini aniqlab bo'lmadi. /kino [nom] deb yozing.")
        else:
            await update.message.reply_text("❌ Faqat TikTok, YouTube, Instagram linklar!\n\n🎬 Kino qidirish: /kino [nom]")
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
