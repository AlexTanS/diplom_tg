import logging
import asyncio
from typing import Union
from aiogram import Dispatcher, Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp

# @AlexTUrban_bot
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

api_address = {
    "list_of_services": "http://127.0.0.1:8000/api/list_of_services/",
    "service": "http://127.0.0.1:8000/api/service/",
}

bot = Bot(token="8188076440:AAE1v-T8PAUJZVfCTa9nQR-0bvHnZiYHXzA")
dp = Dispatcher(bot, storage=MemoryStorage())

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("Приобрести услугу"), KeyboardButton("Информация")],
    ],
    resize_keyboard=True
)


# kb_inline = InlineKeyboardMarkup(
#     inline_keyboard=[
#         [InlineKeyboardButton(text="Обед", callback_data="obed"),
#          InlineKeyboardButton(text="Интернет", callback_data="wifi"),
#          InlineKeyboardButton(text="Кино", callback_data="kino"), ],
#     ]
# )


async def fetch_json(session: aiohttp.ClientSession, url: str) -> dict:
    async with session.get(url) as response:
        return await response.json()


async def post_to_api(session: aiohttp.ClientSession, url: str, payload: dict) -> Union[dict, None]:
    async with session.post(url, json=payload) as response:
        if response.status == 200:
            return await response.json()
        else:
            logging.error(f"Request failed with status code: {response.status}")
            return None


async def get_list_services():
    """Создание списка дополнительных услуг"""
    list_services = []
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, api_address["list_of_services"])
        for d in data:
            list_services.append(d["name"].title())
    return list_services


services = get_list_services()  # доступные сервисы


class UserState(StatesGroup):
    choosing = State()  # варианты выбора заказов
    id_ticket = State()  # номер билета
    password = State()  # пароль учетной записи


def create_checkbox_keyboard():
    """Инлайн-клавиатура с чекбоксами"""
    inline_kb = InlineKeyboardMarkup(row_width=1)
    for s in services:
        checked = "🔲" if s not in get_selected_services() else "✅"
        callback_data = f"Услуга: {s}"
        inline_kb.insert(InlineKeyboardButton(text=f"{checked} {s}", callback_data=callback_data))
    inline_kb.row(InlineKeyboardButton(text="Далее", callback_data="next"))
    return inline_kb


def get_selected_services():
    """Список выбранных опций"""
    return dp.current_state().get_data().get("selected_options", [])


async def update_selected_options(option):
    """Обновление списка выбранных опций"""
    selected_services = get_selected_services()
    if option in selected_services:
        selected_services.remove(option)
    else:
        selected_services.append(option)
    await dp.current_state().update_data(selected_options=selected_services)


@dp.message_handler(commands=["start"])
async def start(message: Message):
    await message.answer("Привет, я бот, помогающий приобрести допуслуги", reply_markup=kb)


@dp.message_handler(text="Приобрести услугу")
async def set_id_ticket(message: Message):
    await message.answer("Введите номер своего билета:")
    await UserState.id_ticket.set()


@dp.message_handler(state=UserState.id_ticket)
async def set_password(message: Message, state):
    await state.update_data(id_ticket=message.text)
    await message.answer("Введите пароль от учетной записи:")
    await UserState.password.set()


@dp.message_handler(state=UserState.password)
async def end_services(message: Message, state):
    await state.update_data(password=message.text)

    payload = dict()
    data = await state.get_data()
    payload["id_ticket"] = str(data["id_ticket"])
    payload["password"] = str(data["password"])

    # отправка post запроса
    async with aiohttp.ClientSession() as session:
        data = await post_to_api(session, api_address["service"], payload)

    if data is not None:  # получаю словарь с ответом {'test': 'test', 'test2': 'test2'}
        # await message.answer(str(data))
        pass
    else:
        await message.answer("Произошла ошибка при отправке запроса.")

    await message.answer("Результат запроса СДЕЛАТЬ", reply_markup=kb_inline)

    await state.finish()


@dp.message_handler(text="Информация")
async def info(message: Message, state: FSMContext):
    list_services = []
    await message.answer(
        "Для приобретения услуги вам понадобится пароль от учетной записи и номер билета."
        "Услуги включают в себя следующее:")

    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, api_address["list_of_services"])
        for d in data:
            list_services.append([d["name"], d["price"]])

    for s in list_services:
        await message.answer(f"- {s[0]}, стоимость: {s[1]}")


@dp.message_handler()
async def start(message: Message):
    await message.answer("Введите команду /start чтобы начать общение")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
