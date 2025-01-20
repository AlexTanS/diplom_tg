import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Message
import aiohttp
from typing import Union

API_TOKEN = 'Введите свой токен'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# @AlexTUrban_bot
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

api_address = {
    "list_of_services": "http://127.0.0.1:8000/api/list_of_services/",
    "service": "http://127.0.0.1:8000/api/service/",
}


# получение списка услуг по API к сервису
async def fetch_json(session: aiohttp.ClientSession, url: str) -> dict:
    async with session.get(url) as response:
        return await response.json()


# отправка данных по API и получение ответа
async def post_to_api(session: aiohttp.ClientSession, url: str, payload: dict) -> Union[dict, None]:
    async with session.post(url, json=payload) as response:
        if response.status == 200:
            return await response.json()
        else:
            logging.error(f"Request failed with status code: {response.status}")
            return None


class ServiceState(StatesGroup):
    id_ticket = State()
    password = State()
    service = State()


# клавиатура
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("Приобрести услугу"), KeyboardButton("Информация")],
    ],
    resize_keyboard=True
)


@dp.message_handler(commands=['start'])
async def start(message: Message):
    await message.answer("Привет, я бот, помогающий приобрести допуслуги", reply_markup=kb)


@dp.message_handler(text="Приобрести услугу", state='*')
async def start_buy(message: types.Message, state: FSMContext):
    await ServiceState.id_ticket.set()
    await message.reply("Пожалуйста, введите номер билета:")


@dp.message_handler(state=ServiceState.id_ticket)
async def set_id_ticket(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['id_ticket'] = message.text
    await ServiceState.next()
    await message.reply("Теперь введите пароль учетной записи:")


@dp.message_handler(state=ServiceState.password)
async def set_password(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password'] = message.text
    await ServiceState.next()

    list_services = []
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, api_address["list_of_services"])
        for d in data:
            list_services.append(d["name"])
    # чекбоксы
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row(*list_services)
    await message.reply("Пожалуйста, выберите один из вариантов:", reply_markup=markup)


# запрос к API с данными
@dp.message_handler(state=ServiceState.service)
async def end_services(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['service'] = message.text

    # сериализация
    payload = dict()
    data = await state.get_data()
    payload["id_ticket"] = str(data["id_ticket"])
    payload["password"] = str(data["password"])
    payload["service"] = str(data["service"])

    # отправка post запроса
    async with aiohttp.ClientSession() as session:
        d = await post_to_api(session, api_address["service"], payload)

    if d is not None:  # получаю словарь с ответом {'test': 'test', 'test2': 'test2'}
        await message.reply(d["response"], reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Произошла ошибка при отправке запроса.")
    await state.finish()


# Обработчик кнопки Информация
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


# неинформативные сообщения
@dp.message_handler()
async def start(message: Message):
    await message.answer("Введите команду /start чтобы начать общение")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
