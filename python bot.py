import sqlite3
import telebot

TOKEN = "9056544226:AAGkVzzRWFjEhh8j_v3mEmW-dNvD0b0VSsk"
ADMIN_ID = (
    9056544226  # O'z Telegram ID raqamingizni yozing (faqat siz kino qo'shasiz)
)

bot = telebot.TeleBot(TOKEN)


# Ma'lumotlar bazasini yaratish (agar yo'q bo'lsa)
def init_db():
  conn = sqlite3.connect("movies.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT,
            caption TEXT
        )
    """
  )
  conn.commit()
  conn.close()


init_db()

# Admin kino qo'shayotganda vaqtincha kodni saqlab turish uchun lug'at
user_state = {}


# /start buyrug'i
@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.send_message(
      message.chat.id,
      "Salom! Kino kodini yuboring (masalan: 2), men sizga o'sha kinoni"
      " tashlab beraman.",
  )


# /addkino buyrug'i (Faqat adminga kino qo'shishni boshlab beradi)
@bot.message_handler(commands=["addkino"])
def add_kino_start(message):
  if message.from_user.id != ADMIN_ID:
    bot.send_message(message.chat.id, "Bu buyruq faqat admin uchun!")
    return

  bot.send_message(
      message.chat.id, "Iltimos, kino uchun **kod** yuboring (masalan: 2):"
  )
  user_state[message.from_user.id] = {"step": "waiting_for_code"}


# Admin yuborgan xabarlarni va oddiy foydalanuvchi so'rovlarini ushlash
@bot.message_handler(
    content_types=["text", "video", "document"], func=lambda message: True
)
def handle_all(message):
  user_id = message.from_user.id
  text = message.text

  # 1. Agar admin kino qo'shayotgan bo'lsa
  if user_id == ADMIN_ID and user_id in user_state:
    state = user_state[user_id]["step"]

    if state == "waiting_for_code":
      # Admin kodni yubordi
      user_state[user_id]["code"] = text
      user_state[user_id]["step"] = "waiting_for_file"
      bot.send_message(
          message.chat.id,
          f"Endi **{text}** kod uchun **video yoki faylni** yuboring:",
      )
      return

    elif state == "waiting_for_file":
      # Admin videoni yoki faylni yubordi
      code = user_state[user_id]["code"]

      # Videoning yoki faylning unique ID raqamini olamiz
      if message.video:
        file_id = message.video.file_id
      elif message.document:
        file_id = message.document.file_id
      else:
        bot.send_message(
            message.chat.id, "Iltimos, video yoki fayl yuboring!"
        )
        return

      caption = message.caption if message.caption else f"Kino kodi: {code}"

      # Bazaga saqlaymiz
      conn = sqlite3.connect("movies.db")
      cursor = conn.cursor()
      cursor.execute(
          "REPLACE INTO movies (code, file_id, caption) VALUES (?, ?, ?)",
          (code, file_id, caption),
      )
      conn.commit()
      conn.close()

      bot.send_message(
          message.chat.id,
          f"Muvaffaqiyatli saqlandi! Kod: <b>{code}</b>",
          parse_mode="HTML",
      )
      del user_state[user_id]  # Holatni tozalaymiz
      return

  # 2. Oddiy foydalanuvchi kino kodini yuborsa
  if text:
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT file_id, caption FROM movies WHERE code = ?", (text,)
    )
    movie = cursor.fetchone()
    conn.close()

    if movie:
      file_id, caption = movie
      # Bazadan topilgan videoni foydalanuvchiga yuboramiz
      bot.send_video(message.chat.id, file_id, caption=caption)
    else:
      bot.send_message(
          message.chat.id,
          f"Siz yuborgan kod: {text}\nTez orada bu kod bo'yicha kino chiqadigan"
          " qilinadi!",
      )


bot.infinity_polling()
