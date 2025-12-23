#iski ma kaaaaaaa
import pyrogram
import asyncio 
print(f"DEBUG: Currently using Pyrogram version: {pyrogram.__version__}")
import pyrogram
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# --- MONKEY PATCH START (Fixes GroupcallForbidden Error) ---
import pyrogram.errors
if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    pyrogram.errors.GroupcallForbidden = type("GroupcallForbidden", (Exception,), {})
# --- MONKEY PATCH END ---

from pytgcalls import PyTgCalls
import config

# Verification Line
print(f"DEBUG: Using Pyrogram {pyrogram.__version__}")

# Initialize Clients
bot = Client("Bot", config.API_ID, config.API_HASH, bot_token=config.BOT_TOKEN)
assistant = Client("Assistant", config.API_ID, config.API_HASH, session_string=config.SESSION_NAME)

call_py = PyTgCalls(assistant)
def get_btns(extra=None):
    btns = [[InlineKeyboardButton("📢 Channel", url=config.CHANNEL_LINK)]]
    if extra: btns.insert(0, extra)
    return InlineKeyboardMarkup(btns)


async def check_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ("administrator", "creator") or user_id == config.OWNER_ID


# --- MUSIC LOGIC ---
@bot.on_message(filters.command(["play", "playforce"]) & filters.group)
async def play_cmd(_, message: Message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("Give me a song name!")

    m = await message.reply("🔎 Searching...")
    
    try:
        # 1. Search for the song
        with yt_dlp.YoutubeDL({"format": "bestaudio", "quiet": True}) as ytdl:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            url, title, duration = info['url'], info['title'], info['duration']

        # 2. Handle 'playforce' logic
        if message.command[0] == "playforce":
            config.queue[message.chat.id] = []  # Clear queue

        # 3. Start Playing (2025 v2.x direct-play syntax)
        # Note: All lines below this are indented 4 spaces from the 'try'
        await call_py.play(message.chat.id, url)
        
        # 4. Update tracking state
        config.playing[message.chat.id] = {"url": url, "title": title}

        # 5. Build Buttons
        controls = [
            [InlineKeyboardButton("⏸ Pause", callback_data="pause"),
             InlineKeyboardButton("▶️ Resume", callback_data="resume")],
            [InlineKeyboardButton("⏭ Skip", callback_data="skip"), 
             InlineKeyboardButton("⏹ End", callback_data="stop")]
        ]
        
        await m.edit(
            f"🎶 **Playing:** {title}\n🕒 **Duration:** {duration}s",
            reply_markup=get_btns(controls[0] + controls[1])
        )

    except Exception as e:
        await m.edit(f"❌ **Error:** {e}")

@bot.on_message(filters.command(["pause", "resume", "end", "skip"]) & filters.group)
async def music_controls(_, message: Message):
    if not await check_admin(message.chat.id, message.from_user.id): return
    cmd = message.command[0]
    try:
        if cmd == "pause":
            await call_py.pause_stream(message.chat.id)
        elif cmd == "resume":
            await call_py.resume_stream(message.chat.id)
        elif cmd == "end":
            await call_py.leave_call(message.chat.id)
        await message.reply(f"✅ {cmd.capitalize()}ed successfully!", reply_markup=get_btns())
    except:
        await message.reply("❌ Error controlling playback.")


# --- ADMIN & TOOLS ---
@bot.on_message(filters.command("ban") & filters.group)
async def ban_user(_, message: Message):
    if not await check_admin(message.chat.id, message.from_user.id): return
    user = message.reply_to_message.from_user if message.reply_to_message else None
    if user:
        await bot.ban_chat_member(message.chat.id, user.id)
        await message.reply(f"🚫 {user.mention} banned.", reply_markup=get_btns())


@bot.on_message(filters.command("info"))
async def user_info(_, message: Message):
    user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    text = f"👤 **Name:** {user.first_name}\n🆔 **ID:** `{user.id}`\n🔗 **User:** @{user.username}"
    await message.reply(text, reply_markup=get_btns())


@bot.on_message(filters.command("song"))
async def download_song(_, message: Message):
    query = " ".join(message.command[1:])
    m = await message.reply("📥 Downloading MP3...")
    opts = {'format': 'bestaudio', 'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]}
    with yt_dlp.YoutubeDL(opts) as ytdl:
        info = ytdl.extract_info(f"ytsearch:{query}", download=True)['entries'][0]
        fname = f"{info['title']}.mp3"
        await bot.send_audio(message.chat.id, fname, caption=f"🎵 {info['title']}", reply_markup=get_btns())
        os.remove(fname)
    await m.delete()


@bot.on_message(filters.command("start"))
async def start_msg(_, message: Message):
    btns = [
        [InlineKeyboardButton("📢 Channel", url=config.CHANNEL_LINK),
         InlineKeyboardButton("💬 Support", url=config.SUPPORT_GROUP)],
        [InlineKeyboardButton("👤 Owner", url=f"https://t.me/{config.OWNER_USERNAME}")]
    ]
    await message.reply(f"Welcome {message.from_user.mention}! I'm a VC Music Bot.",
                        reply_markup=InlineKeyboardMarkup(btns))


# --- BOOT ---
async def start_all():
    await bot.start();
    await assistant.start();
    await call_py.start()
    print("Bot is fully functional!");
    await idle()


if __name__ == "__main__":

    asyncio.get_event_loop().run_until_complete(start_all())












