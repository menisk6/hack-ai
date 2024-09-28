from datetime import datetime

import pandas as pd
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db_users


admins = [488249546, 682369960]

def create_inline_kb(width: int,
                     *args: str,
                     **kwargs: str) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    # Заполняем список кнопками из аргументов args и kwargs


    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=width)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()

class AdminPanel(StatesGroup):
    main_menu = State()
    manage_requests = State()
    manage_users = State()
    user_info = State()
    settings = State()


admin_router = Router()


@admin_router.message((F.text.endswith('Админ')) & (F.from_user.id.in_(admins)))
async def admin_panel(message: Message, state: FSMContext):
    await state.set_state(AdminPanel.main_menu)
    keyboard = [
        [KeyboardButton(text="Статистика обращений")],[KeyboardButton(text="Информация о пользователях")]]
    await message.reply(
        text='Выберите действие', reply_markup=ReplyKeyboardMarkup(keyboard=keyboard,
                                                                   resize_keyboard=True,
                                                                   one_time_keyboard=False))


@admin_router.message(StateFilter(AdminPanel.main_menu))
async def main_menu(message: Message, state: FSMContext):
    if message.text == 'Информация о пользователях':
        await state.set_state(AdminPanel.manage_users)
        check_db = await db_users.fetch(f'SELECT * FROM public.users')
        df = pd.DataFrame(check_db)
        kb_builder = InlineKeyboardBuilder()
        for user in df.itertuples():
            kb_builder.row(
                InlineKeyboardButton(
                    text=user[1],
                    callback_data=user[1]
                )
            )
        await message.reply('Информация о пользователях', reply_markup=kb_builder.as_markup())
    elif message.text == "Статистика обращений":
        check_users = await db_users.fetch(f'SELECT * FROM public.users')
        check_quest = await db_users.fetch(f'SELECT * FROM public.questions')
        df_users = pd.DataFrame(check_users)
        df_quest = pd.DataFrame(check_quest)
        text = (f'''Зарегистрированных пользователей в базе - {len(df_users)}
        Всего зарегистрировано обращений - {len(df_quest)}
        Сообщений обработано ИИ - {len(df_quest.loc[df_quest[6] == 'AI'])}
        Сообщений обработано оператором - {len(df_quest.loc[df_quest[6] == 'TP'])}
        Необработанные техподдержкой заявки - {len(df_quest.loc[(df_quest[6] == 'TP')&(df_quest[5] is None)])}
''')
        keyboard = [
            [KeyboardButton(text="Статистика обращений")], [KeyboardButton(text="Информация о пользователях")]]
        await message.reply(
            text=text, reply_markup=ReplyKeyboardMarkup(keyboard=keyboard,
                                                                       resize_keyboard=True,
                                                                       one_time_keyboard=False))


@admin_router.callback_query(StateFilter(AdminPanel.manage_users))
async def user_info(callback_query: CallbackQuery, state: FSMContext):
    sql = await db_users.fetch(
        f"SELECT * FROM public.users WHERE tg_id = $1",
        callback_query.data)
    df = pd.DataFrame(sql)
    await state.set_state(AdminPanel.user_info)
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Назад', callback_data='back')]])
    await callback_query.message.edit_text(f"Пользователь: {callback_query.data}.\n <pre>{df.to_string()}</pre>",
                                           parse_mode='html', reply_markup=inline_keyboard)



@admin_router.callback_query(StateFilter(AdminPanel.user_info))
async def back(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == 'back':
        await state.set_state(AdminPanel.manage_users)
        check_db = await db_users.fetch(f'SELECT * FROM public.users')
        df = pd.DataFrame(check_db)
        kb_builder = InlineKeyboardBuilder()
        for user in df.itertuples():
            kb_builder.row(
                InlineKeyboardButton(
                    text=user[1],
                    callback_data=user[1]
                )
            )
        # await message.reply('Информация о пользователях', reply_markup=kb_builder.as_markup())
        await callback_query.message.edit_text('Информация о пользователях', reply_markup=kb_builder.as_markup())

