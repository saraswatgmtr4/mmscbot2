import asyncio
import os
import pyrogram
import yt_dlp
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pyrogram.errors import UserAlreadyParticipant, FloodWait
import config

# --- MONKEY PATCH START (Fixes GroupcallForbidden Error for 2025) ---
import pyrogram.errors
if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    pyrogram.errors.GroupcallForbidden = type("GroupcallForbidden", (Exception,), {})
# --- MONKEY PATCH END ---

# Initialize Clients
bot = Client("Bot", config.API_ID, config.API_HASH, bot_token=config.BOT_TOKEN)
assistant = Client("Assistant", config.API_ID, config.API_HASH, session_string=config.SESSION_NAME)
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
    
    # --- FORCE RESOLVE START ---
    try:
        # We use 'await client.get_chat' to make sure the BOT knows the group
        await client.get_chat(chat_id)
        # We use 'await assistant.get_chat' to make sure the ASSISTANT knows the group
        await assistant.get_chat(chat_id)
    except Exception:
        # If it fails, the Assistant probably isn't in the group yet. 
        # The auto-invite logic below will handle it.
        pass
    # --- FORCE RESOLVE END ---
    
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("❌ **Usage:** `/play [song name]`")

    m = await message.reply("🔄 **Checking Assistant status...**")

    # 1. AUTO-INVITE LOGIC
    try:
        await client.get_chat_member(chat_id, config.ASSISTANT_ID)
    except Exception:
        await m.edit("🎟️ **Assistant not found. Generating invite...**")
        try:
            invitelink = await client.export_chat_invite_link(chat_id)
            await assistant.join_chat(invitelink)
            await m.edit("✅ **Assistant joined successfully!**")
            await asyncio.sleep(2) # Wait for Telegram to register join
        except Exception as e:
            return await m.edit(f"❌ **Failed to invite assistant.**\nMake sure I am Admin!\n`Error: {e}`")

    # 2. SEARCH LOGIC
    await m.edit("🔎 **Searching for song...**")
    try:
        ydl_opts = {"format": "bestaudio", "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            url = info['url']
            title = info['title']
            duration = info['duration']
    except Exception as e:
        return await m.edit(f"❌ **Search Error:** {e}")

    # 3. PEER RESOLUTION
    try:
        await assistant.get_chat(chat_id)
    except:
        pass

    # 4. START STREAMING
    try:
        await call_py.play(chat_id, url)
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏸ Pause", callback_data="pause"),
                InlineKeyboardButton("▶️ Resume", callback_data="resume")
            ],
            [InlineKeyboardButton("⏹ Stop", callback_data="stop")]
        ])

        await m.edit(
            f"🎶 **Now Playing**\n\n📌 **Title:** {title}\n🕒 **Duration:** {duration}s\n👤 **Requested by:** {message.from_user.mention}",
            reply_markup=buttons
        )
    except Exception as e:
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
async def start_all():
    try:
        print("1. Starting Bot...")
        await bot.start()
        print("Bot started successfully!")
    except Exception as e:
        print(f"CRITICAL ERROR starting Bot: {e}")
        return

    try:
        print("2. Starting Assistant...")
        await assistant.start()
        print("Assistant started successfully!")
    except Exception as e:
        print(f"CRITICAL ERROR starting Assistant: {e}")
        return

    try:
        print("3. Starting PyTgCalls...")
        await call_py.start()
        print("PyTgCalls started successfully!")
    except Exception as e:
        print(f"CRITICAL ERROR starting PyTgCalls: {e}")
        return

    print("✅ ALL SYSTEMS GO! Bot is now responding to messages.")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_all())


