import os
import asyncio
import aiohttp
import random
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import BotCommand
from groq import AsyncGroq

# --- 1. ЗАГРУЗКА НАСТРОЕК ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

groq_client = AsyncGroq(api_key=GROQ_KEY)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилища
user_settings = {}
user_modes = {}

# Локальные шутки
RU_JOKES = {
    "🐱 Коты": ["Кот — это жидкость.", "Мой кот разрешает мне спать на краю моей кровати."],
    "🐍 IT": ["Программист в лифте: — На какой вам этаж? — 404.", "Это аппаратная проблема."],
    "💀 Чёрный юмор": ["Шутка про безработных не работает.", "Мишень для бабушки."]
}

# --- 2. ФУНКЦИИ API ---
async def get_russian_api_joke():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://rzhunemogu.ru/RandJSON.aspx?CType=1", timeout=5) as resp:
                text = await resp.text()
                return text.replace('{"content":"', '').replace('"}', '').strip()
    except:
        all_jokes = [j for sublist in RU_JOKES.values() for j in sublist]
        return random.choice(all_jokes)


async def get_meme_url():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme", timeout=5) as resp:
                data = await resp.json()
                return data.get("url")
    except:
        return None


async def get_english_api_joke():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://official-joke-api.appspot.com/random_joke", timeout=5) as resp:
                data = await resp.json()
                return f"🇺🇸 {data['setup']}\n\n— {data['punchline']}"
    except:
        return "Sorry, can't find a joke right now."


async def ask_ai(prompt, system_role="You are a funny assistant."):
    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ],
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"🤖 Ошибка ИИ: {e}"


# --- 3. КЛАВИАТУРЫ ---
def get_lang_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🇷🇺 Русский")
    builder.button(text="🇺🇸 English")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_ru_kb():
    builder = ReplyKeyboardBuilder()
    for topic in RU_JOKES.keys():
        builder.button(text=topic)
    builder.button(text="🤖 ИИ-шутник")
    builder.button(text="💬 Смешной диалог")
    builder.button(text="🖼 Пришли мем")
    builder.button(text="🎲 Случайная шутка")
    builder.button(text="📖 Помощь")
    builder.button(text="⚙️ Сменить язык")
    builder.adjust(3, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_en_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎯 Get a joke")
    builder.button(text="🖼 Send a meme")
    builder.button(text="💬 AI Chat")
    builder.button(text="📖 Help")
    builder.button(text="⚙️ Change Language")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


# --- 4. ПОМОЩЬ ---
async def send_help(message: types.Message):
    lang = user_settings.get(message.from_user.id, "RU")

    if lang == "RU":
        text = (
            "<b>📖 Полная справка Giggly_Bot</b>\n\n"
            "🔹 /start — Перезапустить бота и выбрать язык\n"
            "🔹 /help — Показать эту справку\n"
            "🔹 /joke — Быстрая случайная шутка\n\n"
            "<b>Доступные кнопки в русском меню:</b>\n"
            "• 🐱 Коты, 🐍 IT, 💀 Чёрный юмор — локальные шутки\n"
            "• 🤖 ИИ-шутник — ИИ придумает шутку на твою тему\n"
            "• 💬 Смешной диалог — свободное общение с весёлым ИИ\n"
            "• 🖼 Пришли мем — случайный мем с Reddit\n"
            "• 🎲 Случайная шутка — шутка из интернета\n"
            "• 📖 Помощь — показать эту справку\n"
            "• ⚙️ Сменить язык — вернуться к выбору языка\n\n"
            "<i>После одной шутки от ИИ бот автоматически возвращается в обычный режим.</i>"
        )
    else:
        text = (
            "<b>📖 Giggly_Bot Help</b>\n\n"
            "🔹 /start — Restart and choose language\n"
            "🔹 /help — Show this help\n"
            "🔹 /joke — Quick joke\n\n"
            "<b>Available buttons:</b>\n"
            "• 🎯 Get a joke — Random English joke\n"
            "• 🖼 Send a meme — Random meme from Reddit\n"
            "• 💬 AI Chat — Free chat with funny AI\n"
            "• 📖 Help — show this message\n"
            "• ⚙️ Change Language\n\n"
            "<i>Bot returns to normal mode after using AI joke mode.</i>"
        )

    await message.answer(text, parse_mode="HTML")


# --- 5. ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    start_text = (
        "Привет! Я Giggly_Bot — твой генератор настроения. 🎭\n\n"
        "Я умею всё: мемы, шутки и умный чат.\n"
        "Если запутаешься — жми /help\n\n"
        "Выбери язык / Choose language:"
    )
    await message.answer(start_text, reply_markup=get_lang_kb())


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await send_help(message)


@dp.message(F.text.in_(["📖 Помощь", "📖 Help"]))
async def button_help(message: types.Message):
    await send_help(message)


@dp.message(Command("joke"))
async def cmd_joke_fast(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    joke = await get_russian_api_joke()
    await message.answer(f"🚀 Вот тебе шутка:\n\n{joke}")


@dp.message(F.text == "🇷🇺 Русский")
async def set_ru(message: types.Message):
    user_settings[message.from_user.id] = "RU"
    await message.answer("🇷🇺 Русский язык активирован!\nИспользуй кнопки ниже.", reply_markup=get_ru_kb())


@dp.message(F.text == "🇺🇸 English")
async def set_en(message: types.Message):
    user_settings[message.from_user.id] = "EN"
    await message.answer("🇺🇸 English mode activated!", reply_markup=get_en_kb())


@dp.message(F.text.in_(["🖼 Пришли мем", "🖼 Send a meme"]))
async def send_meme(message: types.Message):
    await bot.send_chat_action(message.chat.id, "upload_photo")
    meme_url = await get_meme_url()
    if meme_url:
        await message.answer_photo(meme_url)
    else:
        await message.answer("😔 Мемы временно недоступны.")


@dp.message(F.text == "🎯 Get a joke")
async def en_joke(message: types.Message):
    joke = await get_english_api_joke()
    await message.answer(joke)


@dp.message(F.text == "🤖 ИИ-шутник")
async def mode_joke(message: types.Message):
    user_modes[message.from_user.id] = "ai_joke"
    await message.answer("Напиши тему для шутки (например: про котов, школу, программистов):")


@dp.message(F.text.in_(["💬 Смешной диалог", "💬 AI Chat"]))
async def mode_chat(message: types.Message):
    user_modes[message.from_user.id] = "chat"
    await message.answer("🔥 Я в режиме свободного общения! Пиши что угодно.")


@dp.message(F.text.in_(RU_JOKES.keys()))
async def local_joke(message: types.Message):
    await message.answer(random.choice(RU_JOKES[message.text]))


@dp.message(F.text.in_(["⚙️ Сменить язык", "⚙️ Change Language"]))
async def change_lang(message: types.Message):
    await message.answer("Выбери язык:", reply_markup=get_lang_kb())


@dp.message(F.text == "🎲 Случайная шутка")
async def random_joke_ru(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    joke = await get_russian_api_joke()
    await message.answer(f"🎲 Случайная шутка:\n\n{joke}")


@dp.message(F.text)
async def handle_text(message: types.Message):
    uid = message.from_user.id
    mode = user_modes.get(uid)

    if mode in ["ai_joke", "chat"]:
        await bot.send_chat_action(message.chat.id, "typing")

        if mode == "ai_joke":
            system_role = "Ты стендап-комик. Придумай одну смешную шутку на тему пользователя. Отвечай только на русском."
        else:
            system_role = "Ты весёлый и остроумный друг. Отвечай только на русском." if user_settings.get(uid, "RU") == "RU" else "You are a funny and witty friend."

        response = await ask_ai(message.text, system_role)
        await message.answer(response)

        if mode == "ai_joke":
            user_modes[uid] = None
    else:
        await message.answer("Пожалуйста, используй кнопки меню или напиши /help")


# --- 6. ЗАПУСК ---
async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Показать помощь"),
        BotCommand(command="joke", description="Случайная шутка")
    ])

    print(">>> Giggly_Bot успешно запущен и готов!")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())