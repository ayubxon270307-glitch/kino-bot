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

# ─────────────────────────────────────────
# 1. LINKDAN VIDEO NOMINI OLISH
# ─────────────────────────────────────────
def get_video_title(url):
    """TikTok/Instagram/YouTube linkidan video nomini oladi"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,  # Yuklamasdan faqat nom oladi
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '')
            description = info.get('description', '')
            return title, description
    except Exception as e:
        logger.error(f"Title error: {e}")
        return None, None

# ─────────────────────────────────────────
# 2. ASILMEDIA DAN QIDIRISH (Google orqali)
# ─────────────────────────────────────────
def search_asilmedia(query):
    """Google orqali AsilMedia dan kino qidiradi"""
    try:
        # Nomni tozalash — faqat asosiy so'zlar
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

# ─────────────────────────────────────────
# 3. KINO SAHIFASIDAN 720p LINKLAR OLISH
# ─────────────────────────────────────────
def get_movie_links(url):
    """Kino sahifasidan 720p ko'rish va yuklab olish linkini oladi"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Kino nomi
        title_el = soup.select_one("h1")
        raw_title = title_el.get_text(strip=True) if title_el else "Kino"
        # Uzun sarlavhadan faqat asosiy nomni olish
        clean_title = re.sub(
            r'\s*(Uzbek tilida|O\'zbekcha tarjima|tarjima|Full HD|tas-ix|skachat|HD|kino|Barcha qismlar).*',
            '', raw_title, flags=re.IGNORECASE
        ).strip()

        # Tavsif
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

        # Rasm
        img_el = soup.select_one("img[src*='/uploads/']")
        img_url = ""
        if img_el:
            img_url = img_el.get("src", "")
            if not img_url.startswith("http"):
                img_url = "https://asilmedia.org" + img_url

        # 720p linklar
        watch_720 = url
        download_720 = url

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True).lower()
            if not href.startswith("http"):
                href = "https://asilmedia.org" + href
            if "720" in text:
                if any(w in text for w in ["ko'rish", "смотреть", "watch", "onlayn", "online"]):
                    watch_720 = href
                if any(w in text for w in ["skachat", "yuklab", "download", "юкла"]):
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

# ─────────────────────────────────────────
# 4. PLATFORMANI ANIQLASH
# ─────────────────────────────────────────
def detect_platform(url):
    if "tiktok.com" in url:
        return "tiktok"
    elif "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    return None

# ─────────────────────────────────────────
# 5. KINO NATIJASINI YUBORISH
# ─────────────────────────────────────────
async def send_movie_result(update, movie, note=""):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ 720p Onlayn Ko'rish", url=movie["watch_url"])],
        [InlineKeyboardButton("⬇️ 720p Yuklab Olish", url=movie["download_url"])],
        [InlineKeyboardButton("🌐 AsilMedia Sahifasi", url=movie["page_url"])],
    ])

    caption = (
        f"🎬 *{movie['title']}*\n\n"
        f"📝 {movie['desc']}\n\n"
        f"📺 Sifat: 480p | *720p* | 1080p\n"
        f"🌐 Manba: AsilMedia.org"
    )
    if note:
        caption += f"\n\n{note}"

    if movie.get("img"):
        try:
            await update.message.reply_photo(
                photo=movie["img"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return
        except Exception:
            pass

    await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=keyboard)

# ─────────────────────────────────────────
# 6. TELEGRAM HANDLERLAR
# ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Salom! Men kino botman!*\n\n"
        "📌 *Qanday ishlaydi:*\n\n"
        "🎵 TikTok/Instagram/YouTube linkini yuboring\n"
        "→ Bot video nomini aniqlab AsilMedia dan topadi\n"
        "→ *720p Ko'rish* va *Yuklab olish* linkini beradi\n\n"
        "🎬 Yoki to'g'ridan kino nomini yozing\n"
        "→ `/kino Avatar` — AsilMedia dan qidiradi\n\n"
        "🎵 Faqat muzika: `/audio [link]`",
        parse_mode="Markdown"
    )

async def kino_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kino nomini yozing: /kino Avatar")
        return
    query = " ".join(context.args)
    await search_and_send(update, query)

async def audio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Link yuboring: /audio [link]")
        return
    url = context.args[0]
    msg = await update.message.reply_text("🎵 Muzika yuklanmoqda...")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '/tmp/%(title)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            title = info.get('title', 'Audio')
        if os.path.exists(filepath):
            await msg.edit_text("📤 Yuborilmoqda...")
            with open(filepath, 'rb') as f:
                await update.message.reply_audio(audio=f, title=title, caption=f"🎵 {title}")
            os.remove(filepath)
            await msg.delete()
        else:
            await msg.edit_text("❌ Yuklab bo'lmadi!")
    except Exception as e:
        await msg.edit_text("❌ Xatolik yuz berdi!")
        logger.error(e)

async def search_and_send(update, query):
    msg = await update.message.reply_text(f"🔍 *{query[:40]}* — AsilMedia dan qidirilmoqda...", parse_mode="Markdown")
    results = search_asilmedia(query)

    if not results:
        await msg.edit_text(
            f"❌ *{query[:40]}* AsilMedia da topilmadi!\n\n"
            "Kino hali qo'shilmagan bo'lishi mumkin.",
            parse_mode="Markdown"
        )
        return

    movie = get_movie_links(results[0]["url"])
    await msg.delete()

    if movie:
        # Boshqa natijalar tugmasi
        extra_btns = []
        if len(results) > 1:
            for r in results[1:4]:
                extra_btns.append([InlineKeyboardButton(f"📽 {r['title'][:45]}", url=r["url"])])

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ 720p Onlayn Ko'rish", url=movie["watch_url"])],
            [InlineKeyboardButton("⬇️ 720p Yuklab Olish", url=movie["download_url"])],
            [InlineKeyboardButton("🌐 AsilMedia Sahifasi", url=movie["page_url"])],
        ] + extra_btns)

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
    else:
        # Faqat linklar ro'yxati
        btns = [[InlineKeyboardButton(f"🎬 {r['title'][:50]}", url=r["url"])] for r in results]
        await update.message.reply_text(
            f"🔍 *{query[:40]}* — Natijalar:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # URL bormi?
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)

    if urls:
        url = urls[0]
        platform = detect_platform(url)

        if platform:
            # TikTok / Instagram / YouTube linki
            msg = await update.message.reply_text(
                f"🔍 {platform.upper()} linkidan kino nomi aniqlanmoqda..."
            )
            title, description = get_video_title(url)

            if title:
                # Nomdan keraksiz qismlarni tozalash
                clean = re.sub(r'[#@|\[\](){}]', ' ', title)
                clean = re.sub(r'\s+', ' ', clean).strip()[:60]

                await msg.edit_text(f"🎬 *{clean}* — AsilMedia dan qidirilmoqda...", parse_mode="Markdown")
                results = search_asilmedia(clean)

                if not results and description:
                    # Nom topilmasa tavsif bilan sinab ko'rish
                    desc_query = description[:50]
                    results = search_asilmedia(desc_query)

                if results:
                    movie = get_movie_links(results[0]["url"])
                    await msg.delete()
                    if movie:
                        extra_btns = []
                        if len(results) > 1:
                            for r in results[1:3]:
                                extra_btns.append([InlineKeyboardButton(f"📽 {r['title'][:45]}", url=r["url"])])

                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("▶️ 720p Onlayn Ko'rish", url=movie["watch_url"])],
                            [InlineKeyboardButton("⬇️ 720p Yuklab Olish", url=movie["download_url"])],
                            [InlineKeyboardButton("🌐 AsilMedia Sahifasi", url=movie["page_url"])],
                        ] + extra_btns)

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
                await msg.edit_text("❌ Link dan nom olib bo'lmadi. Kino nomini yozing: /kino [nom]")
        else:
            await update.message.reply_text(
                "❌ Faqat TikTok, YouTube, Instagram linklar qabul qilinadi!\n\n"
                "🎬 Kino qidirish: /kino [nom]"
            )
    else:
        # URL yo'q — kino nomi deb qabul qilish
        if len(text) > 2:
            await search_and_send(update, text)
        else:
            await update.message.reply_text("Link yoki kino nomini yuboring!\n/kino Avatar")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("kino", kino_cmd))
    app.add_handler(CommandHandler("audio", audio_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
