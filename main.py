import os
import asyncio
import yt_dlp
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from googleapiclient.discovery import build
from config import BOT_TOKEN, YOUTUBE_API_KEY

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
bot = Bot(token=BOT_TOKEN)
router = Router()

async def health(request):
    return web.Response(text="Bot is running")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Welcome!\nВведите название трека для поиска.")

@router.message()
async def search(message: types.Message):
    q = message.text.strip()
    if len(q) < 2:
        await message.answer("Одной буквы маловато.")
        return
    try:
        req = youtube.search().list(q=q, part="snippet", type="video", maxResults=5, videoCategoryId="10")
        res = req.execute()
        items = res.get("items", [])
        if not items:
            await message.answer("Ничего не нашлось.")
            return
        btns = [[InlineKeyboardButton(text=f"{i['snippet']['title'][:50]} — {i['snippet']['channelTitle']}", callback_data=f"dl_{i['id']['videoId']}")] for i in items]
        await message.answer("Вот что нашёл:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    except Exception:
        await message.answer("Я споткнулся. Дай мне минутку.")

@router.callback_query(F.data.startswith("dl_"))
async def download(callback: types.CallbackQuery):
    vid = callback.data.replace("dl_", "")
    await callback.answer()
    try:
        os.makedirs("downloads", exist_ok=True)
        opts = {"format": "bestaudio/best", "outtmpl": f"downloads/{vid}.%(ext)s", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}], "quiet": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={vid}"])
        path = f"downloads/{vid}.mp3"
        if os.path.exists(path) and os.path.getsize(path) < 50000000:
            await callback.message.answer_audio(FSInputFile(path))
        else:
            await callback.message.answer("Трек слишком тяжёлый.")
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        await callback.message.answer("Я споткнулся. Дай мне минутку.")

async def main():
    await start_web_server()
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
