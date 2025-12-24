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
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton # Ensure these are imported

@bot.on_message(filters.command(["play", "playforce"]) & filters.group)
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserAlreadyParticipant, FloodWait
import asyncio
import config

@bot.on_message(filters.command(["play"]) & filters.group)
async def play_cmd(client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # 1. Check if a song name was provided
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("❌ **Usage:** `/play [song name]`")

    m = await message.reply("🔄 **Checking Assistant status...**")

    # 2. AUTO-INVITE LOGIC: Check if Assistant is in the group
    try:
        await client.get_chat_member(chat_id, config.ASSISTANT_ID) # Define ASSISTANT_ID in config
    except Exception:
        # Assistant not found, let's invite it
        await m.edit("🎟️ **Assistant not found. Generating invite...**")
        try:
            invitelink = await client.export_chat_invite_link(chat_id)
            # Assistant account joins via the link
            await assistant.join_chat(invitelink)
            await m.edit("✅ **Assistant joined successfully!**")
        except Exception as e:
            return await m.edit(f"❌ **Failed to invite assistant.**\nMake sure I am Admin!\n`Error: {e}`")

    # 3. SEARCH LOGIC
    await m.edit("🔎 **Searching for song...**")
    try:
        with yt_dlp.YoutubeDL({"format": "bestaudio", "quiet": True}) as ytdl:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            url = info['url']
            title = info['title']
            duration = info['duration']
            thumbnail = info.get('thumbnail')
    except Exception as e:
        return await m.edit(f"❌ **Search Error:** {e}")

    # 4. PEER RESOLUTION (Final fix for 'ID not found')
    try:
        await assistant.get_chat(chat_id)
    except Exception:
        pass

    # 5. START STREAMING
    try:
        await call_py.play(chat_id, url)
        
        # Buttons for controls
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
            f"🎶 **Now Playing**\n\n📌 **Title:** {title}\n🕒 **Duration:** {duration}s\n👤 **Requested by:** {message.from_user.mention}",
            reply_markup=buttons
        )
    except Exception as e:
        await m.edit(f"❌ **Streaming Error:** {e}")

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
    # 1. Start the Bot
    print("Starting Bot...")
    await bot.start()
    
    # 2. Start the Assistant
    print("Starting Assistant...")
    await assistant.start()
    
    # 3. Start PyTgCalls
    print("Starting PyTgCalls...")
    await call_py.start()
    
    print("✅ BOT IS ONLINE!")
    
    # 4. Keep the bot running
    await idle()
    
    # 5. Graceful shutdown
    await bot.stop()
    await assistant.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_all())







