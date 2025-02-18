import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from flask import Flask
from threading import Thread
from keep_alive import keep_alive  # Подключаем keep_alive.py

# 🔹 Логирование (чтобы видеть ошибки)
logging.basicConfig(level=logging.INFO)

# 🔹 Получаем токен из переменных окружения (Replit Secrets)
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Ошибка! BOT_TOKEN не найден. Добавьте его в 'Secrets' Replit.")

print(f"🔑 BOT_TOKEN: {TOKEN[:10]}...")  # Выведет часть токена для проверки

# 🔹 Создаем бота и диспетчер с MemoryStorage
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# 🔹 Flask-сервер (для 24/7 работы)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Бот работает 24/7!"

# 🔹 Словари для хранения ID отправителей и получателей
user_data = {}  # Кто отправил анонимное сообщение
recipient_data = {}  # Кому было отправлено сообщение

# 🔹 Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Отправь **ID получателя**, **перешли его сообщение** или **напиши @username**, и я передам анонимное сообщение."
    )

# 🔹 Функция для получения ID по username
async def get_user_id_by_username(username: str):
    try:
        user = await bot.get_chat(username)
        return user.id
    except Exception:
        return None

# 🔹 Обработчик получения ID получателя и отправки сообщений
@dp.message()
async def handle_anonymous_message(message: types.Message):
    user_id = message.from_user.id

    # Проверяем, переслал ли пользователь сообщение
    if message.forward_from:
        recipient_id = message.forward_from.id
        user_data[user_id] = recipient_id
        await message.answer(f"✅ ID получателя найден: `{recipient_id}`\n\nТеперь отправь текст или медиа.")
        return

    # Если пользователь отправил ID вручную
    if message.text and message.text.isdigit():
        recipient_id = int(message.text)
        user_data[user_id] = recipient_id
        await message.answer(f"✅ ID получателя установлен: `{recipient_id}`\n\nТеперь отправь текст или медиа.")
        return

    # Если пользователь отправил username
    if message.text and message.text.startswith("@"):
        username = message.text.strip("@")
        recipient_id = await get_user_id_by_username(username)
        if recipient_id:
            user_data[user_id] = recipient_id
            await message.answer(f"✅ ID для @{username} найден: `{recipient_id}`\n\nТеперь отправь текст или медиа.")
        else:
            await message.answer("❌ Ошибка! Пользователь не найден или у него закрыты сообщения.")
        return

    # Проверяем, сохранен ли ID
    recipient_id = user_data.get(user_id)
    if not recipient_id:
        await message.answer("⚠️ Сначала отправь ID, @username или пересланное сообщение.")
        return

    # Создаем кнопку "Ответить анонимно"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💬 Ответить анонимно", callback_data=f"reply_{user_id}")]]
    )

    # Отправляем анонимное сообщение
    try:
        if message.text:
            await bot.send_message(recipient_id, f"📩 Анонимное сообщение:\n\n{message.text}", reply_markup=keyboard)

        elif message.photo:
            await bot.send_photo(recipient_id, message.photo[-1].file_id, caption="📷 Анонимное фото", reply_markup=keyboard)

        elif message.video:
            await bot.send_video(recipient_id, message.video.file_id, caption="🎥 Анонимное видео", reply_markup=keyboard)

        elif message.document:
            await bot.send_document(recipient_id, message.document.file_id, caption="📄 Анонимный документ", reply_markup=keyboard)

        elif message.voice:
            await bot.send_voice(recipient_id, message.voice.file_id, caption="🎙️ Анонимное голосовое", reply_markup=keyboard)

        elif message.audio:
            await bot.send_audio(recipient_id, message.audio.file_id, caption="🎵 Анонимное аудио", reply_markup=keyboard)

        else:
            await message.answer("❌ Этот формат не поддерживается.")
            return

        await message.answer("✅ Сообщение отправлено анонимно!")
        recipient_data[recipient_id] = user_id  # Сохраняем связь между отправителем и получателем

    except Exception as e:
        await message.answer(f"⚠️ Ошибка при отправке: {e}\nВозможно, у получателя закрыты личные сообщения.")

# 🔹 Обработчик кнопки "Ответить анонимно"
@dp.callback_query()
async def reply_anonymously(callback: CallbackQuery):
    recipient_id = callback.from_user.id
    sender_id = recipient_data.get(recipient_id)

    if not sender_id:
        await callback.answer("⚠️ Ошибка! Невозможно определить отправителя.")
        return

    await callback.message.answer("✍️ Напиши анонимный ответ, и я передам его.")

    # Сохраняем получателя как "ответчика"
    user_data[recipient_id] = sender_id

# 🔹 Функция запуска бота
async def main():
    """Запускает бота"""
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

# 🔹 Поддержание работы Flask-сервера
def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    Thread(target=run_flask).start()  # Запускаем Flask
    keep_alive()  # Поддержка работы 24/7
    asyncio.run(main())  # Запуск бота

