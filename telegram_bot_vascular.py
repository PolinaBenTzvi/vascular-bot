import logging
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

API_TOKEN = '8065041435:AAEuXdc6r1A2ji2h6kgI1_WZGCtp_ayISPI'

menu_df = pd.read_excel("menu_structure_mine.xlsx")
cards_df = pd.read_excel("cards_content.xlsx")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Очистка: удаляем пробелы, невидимые символы, приводим к нижнему регистру
def normalize(text):
    return ''.join(e for e in str(text).replace('\u200f', '').replace('\u200e', '').strip().lower() if e.isalnum())

menu_tree = {}
cards_dict = {}
operation_cards = {}

# Карточки
for _, row in cards_df.iterrows():
    card_id = row['card_id']
    prefix = card_id.split('_')[0].lower()
    cards_dict[card_id] = {
        "title": row['title'],
        "text": row['text']
    }
    operation_cards.setdefault(prefix, []).append(card_id)

# Меню
for _, row in menu_df.iterrows():
    button = str(row['button']).strip()
    parent = str(row['parent']).strip() if pd.notna(row['parent']) else None
    key = normalize(parent) if parent is not None else None
    menu_tree.setdefault(key, []).append((button, row['action']))

# Построение клавиатуры
def build_menu(parent_raw):
    key = normalize(parent_raw) if parent_raw is not None else None
    keyboard = []
    for button, action in menu_tree.get(key, []):
        callback = f"menu:{button}"
        keyboard.append([InlineKeyboardButton(button, callback_data=callback)])
    if parent_raw is not None:
        back_button = InlineKeyboardButton("⬅️ Back", callback_data=f"back:{parent_raw}")
        start_button = InlineKeyboardButton("🏁 Start", callback_data="startover")
        keyboard.append([back_button, start_button])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("ברוך הבא! נא לבחור מהתפריט:", reply_markup=build_menu(None))

@dp.callback_query_handler(lambda c: c.data.startswith("menu:"))
async def handle_menu(callback_query: types.CallbackQuery):
    data_raw = callback_query.data.split("menu:")[1]
    norm_data = normalize(data_raw)

    matched_prefix = None
    for prefix in operation_cards:
        if norm_data.startswith(normalize(prefix)):
            matched_prefix = prefix
            break

    if matched_prefix:
        order = ["desc", "setup", "equip"]
        card_ids = operation_cards[matched_prefix]
        def sort_key(cid):
            for i, key in enumerate(order):
                if cid.lower().endswith(key):
                    return i
            return 999
        card_ids_sorted = sorted(card_ids, key=sort_key)

        for card_id in card_ids_sorted:
            card = cards_dict[card_id]
            await bot.send_message(
                callback_query.from_user.id,
                f"{card['title']}\n\n{card['text']}"
            )
        back_button = InlineKeyboardButton("⬅️ Back", callback_data=f"back:{data_raw}")
        start_button = InlineKeyboardButton("🏁 Start", callback_data="startover")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button, start_button]])
        await bot.send_message(callback_query.from_user.id, "בחר פעולה נוספת:", reply_markup=keyboard)
    else:
        await bot.send_message(callback_query.from_user.id, "📂 בחר תת-תפריט:", reply_markup=build_menu(data_raw))

@dp.callback_query_handler(lambda c: c.data == "startover")
async def handle_start_over(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "ברוך הבא! נא לבחור מהתפריט:", reply_markup=build_menu(None))

@dp.callback_query_handler(lambda c: c.data.startswith("back:"))
async def handle_back(callback_query: types.CallbackQuery):
    current_raw = callback_query.data.split("back:")[1]
    norm_current = normalize(current_raw)

    parent = None
    for _, row in menu_df.iterrows():
        if normalize(row['button']) == norm_current:
            parent = row['parent']
            break
    await bot.send_message(callback_query.from_user.id, "⬅️ חזרה לתפריט קודם:", reply_markup=build_menu(parent))

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
