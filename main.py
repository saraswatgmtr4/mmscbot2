import asyncio
import os
import pyrogram
import yt_dlp
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserAlreadyParticipant, FloodWait
import config
from pyrogram import utils
import logging 
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality # Import both from types
# --- ID RANGE FIX START ---
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# Move your patch here (ensure it's BEFORE the clients start)
from pyrogram import utils
def get_peer_type_new(peer_id: int) -> str:
    pid = str(peer_id)
    if not pid.startswith("-"): return "user"
    return "channel" if pid.startswith("-100") else "chat"
utils.get_peer_type = get_peer_type_new
# --- MONKEY PATCH START (Fixes GroupcallForbidden Error for 2025) ---
import pyrogram.errors
if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    pyrogram.errors.GroupcallForbidden = type("GroupcallForbidden", (Exception,), {})
# --- MONKEY PATCH END ---

# Initialize Clients
# Use distinct names so they create separate 'bot.session' and 'assistant.session' files
bot = Client("bot_session", config.API_ID, config.API_HASH, bot_token=config.BOT_TOKEN)
assistant = Client("assistant_session", config.API_ID, config.API_HASH, session_string=config.SESSION_NAME)
call_py = PyTgCalls(assistant)

# --- HELPER FUNCTIONS ---
def get_btns(extra=None):
    btns = [[InlineKeyboardButton("📢 Channel", url=config.CHANNEL_LINK)]]
    if extra: 
        btns.insert(0, extra)
    return InlineKeyboardMarkup(btns)

async def check_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ("administrator", "creator") or user_id == config.OWNER_ID

# --- MUSIC LOGIC ---




@bot.on_message(filters.command(["play"]) & filters.group)
async def play_cmd(client, message: Message):
    chat_id = message.chat.id
    
    # 1. PEER RESOLUTION (Ensures Assistant/Bot recognize the group)
    try:
        await client.get_chat(chat_id)
        await assistant.get_chat(chat_id)
    except:
        pass
    
    # 2. INPUT VALIDATION
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("❌ **Usage:** `/play [song name or link]`")

    m = await message.reply("🔄 **Processing...**")

    # 3. AUTO-INVITE ASSISTANT
    try:
        await assistant.get_chat_member(chat_id, "me")
    except Exception:
        try:
            invite_link = await client.export_chat_invite_link(chat_id)
            await assistant.join_chat(invite_link)
        except Exception as e:
            return await m.edit(f"❌ **Assistant join failed:** {e}\n\n*Make sure I am Admin with Invite Users permission.*")

    # 4. SEARCH & EXTRACT (YouTube)
    await m.edit("🔎 **Searching for your song...**")
    try:
        ydl_opts = {"format": "bestaudio", "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            url = info['url']
            title = info['title']
            duration = info.get('duration', 0)
    except Exception as e:
        return await m.edit(f"❌ **Search Error:** {e}")

    # 5. START STREAMING
    await m.edit("🎼 **Starting Voice Chat...**")
    try:
        # Optimized for PyTgCalls v2.2.8 (Audio Only)
        await call_py.play(
            chat_id,
            MediaStream(
                url,
                audio_parameters=AudioQuality.STUDIO
            )
        )
        
        # 6. UI INTERFACE
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏸ Pause", callback_data="pause"),
                InlineKeyboardButton("▶️ Resume", callback_data="resume")
            ],
            [
                InlineKeyboardButton("⏹ Stop", callback_data="stop")
            ]
        ])

        await m.edit(
            f"🎶 **Now Playing**\n\n"
            f"📌 **Title:** {title[:40]}...\n"
            f"🕒 **Duration:** {duration}s\n"
            f"👤 **Requested by:** {message.from_user.mention}",
            reply_markup=buttons
        )
    except Exception as e:
        if "ffprobe" in str(e).lower():
            await m.edit("❌ **Streaming Error:** FFmpeg/ffprobe not found on server.\n\n*Tip: Add ffmpeg to your Railway variables.*")
        else:
            await m.edit(f"❌ **Streaming Error:** {e}")
@bot.on_message(filters.command(["pause", "resume", "end", "skip"]) & filters.group)
async def music_controls(_, message: Message):
    if not await check_admin(message.chat.id, message.from_user.id): 
        return
    cmd = message.command[0]
    try:
        if cmd == "pause":
            await call_py.pause_stream(message.chat.id)
        elif cmd == "resume":
            await call_py.resume_stream(message.chat.id)
        elif cmd in ["end", "skip"]:
            await call_py.leave_call(message.chat.id)
        
        await message.reply(f"✅ {cmd.capitalize()}ed successfully!", reply_markup=get_btns())
    except:
        await message.reply("❌ Error controlling playback. Is there a call active?")

# --- ADMIN & TOOLS ---

@bot.on_message(filters.command("start"))
async def start_msg(_, message: Message):
    btns = [
        [InlineKeyboardButton("📢 Channel", url=config.CHANNEL_LINK),
         InlineKeyboardButton("💬 Support", url=config.SUPPORT_GROUP)],
        [InlineKeyboardButton("👤 Owner", url=f"https://t.me/{config.OWNER_USERNAME}")]
    ]
    await message.reply(f"Welcome {message.from_user.mention}! I'm a VC Music Bot.",
                        reply_markup=InlineKeyboardMarkup(btns))

@bot.on_message(filters.command("song"))
async def download_song(_, message: Message):
    query = " ".join(message.command[1:])
    if not query: return await message.reply("Give song name!")
    
    m = await message.reply("📥 Downloading MP3...")
    opts = {
        'format': 'bestaudio', 
        'outtmpl': '%(title)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ytdl:
            info = ytdl.extract_info(f"ytsearch:{query}", download=True)['entries'][0]
            fname = f"{info['title']}.mp3"
            await bot.send_audio(message.chat.id, fname, caption=f"🎵 {info['title']}", reply_markup=get_btns())
            if os.path.exists(fname):
                os.remove(fname)
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    await m.delete()

# --- BOOT ---
# --- BOOT SECTION ---
async def start_all():
    # 1. Start everything
    print("1️⃣ Starting Bot...")
    await bot.start()
    
    print("2️⃣ Starting Assistant...")
    await assistant.start()
    
    print("3️⃣ Starting PyTgCalls...")
    await call_py.start()

    # 4. Sync ONLY the Assistant (Bots can't do this)
    print("4️⃣ Syncing Assistant Database...")
    try:
        # We only do this for the assistant to avoid the 400 BOT_METHOD_INVALID error
        async for _ in assistant.get_dialogs(limit=20):
            pass
        print("✅ Assistant Synced!")
    except Exception as e:
        print(f"⚠️ Assistant Sync warning: {e}")

    print("🚀 BOT IS ONLINE AND LISTENING!")
    # This keeps the bot running
    await idle()

if __name__ == "__main__":
    # Standard way to run in 2025
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_all())
    except KeyboardInterrupt:
        print("Stopping...")













