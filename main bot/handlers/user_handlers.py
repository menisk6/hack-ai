import asyncio
import re

from aiogram.utils.keyboard import InlineKeyboardBuilder

from BotHelper import HelpGPT, llm
from VecSearch import model
from database import db_users
from aiogram import F, Router, exceptions, types, filters, Dispatcher
from aiogram.enums import ContentType, ChatType, ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.types import (CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton, Chat, InlineKeyboardMarkup,
                           InlineKeyboardButton)
import pandas as pd
import datetime
from aiogram import Bot

router = Router()

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', None)

# oper_agent = HelpGPT.from_llm(llm, verbose=False)
# oper_agent.seed_agent()

class FSMFillForm(StatesGroup):
    '''Машина состояний'''
    get_auth = State()        # Состояние авторизации
    ai_talk = State()         # Состояние общения с ai
    tp_talk = State()         # Состояние общения с техподом


#Роутер срабатывает при отправки пользователем команды /start. Переводит в сотояние общения с ИИ
@router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext):
    global oper_agent
    oper_agent = HelpGPT.from_llm(llm, verbose=False)
    oper_agent.seed_agent()
    # ai_message = oper_agent.ai_step()
    await message.reply(f'Здравствуйте, я бот техподдержки. Какой у Вас вопрос?')
    # await message.reply(ai_message)
    await state.set_state(FSMFillForm.ai_talk)


#Роутер срабатывает при отправки пользователем команды /cancel. Переводит в сотояние по умолчанию
@router.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Действия отменены. Для повторного обращения отправьте /start',
    reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


#Роутер срабатывает при отправки пользователем команды /help. Переводит в сотояние по умолчанию
@router.message(Command(commands='help'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Это бот технической поддержки. Для начала отправь команду /start',
    reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


#Роутер срабатывает при нажатии пользователем кнопки Закончить диалог. Переводит в сотояние ai_talk
@router.message(F.text == "Закончить диалог")
async def func_email(message: Message, state: FSMContext):
    await message.answer("Спасибо за обращение. Всего доброго.")
    await state.set_state(FSMFillForm.ai_talk)



#Роутер срабатывает при нажатии пользователем кнопки Задать вопрос в группе при общении с ИИ. В зависимости от наличия регистрации
#переводит либо в сосотяние tp_talk, либо get_auth
@router.message(F.text == "Задать вопрос в группе", StateFilter(FSMFillForm.ai_talk))
async def func_email(message: Message, state: FSMContext,  bot: Bot):
    check_db = await db_users.fetch(f'SELECT tg_id FROM public.users')
    df = pd.DataFrame(check_db)
    if not df.empty and df[0].str.contains(str(message.from_user.id)).any():
        user = message.from_user.id
        group = -1002394147014
        sql = await db_users.fetch(f"SELECT * FROM public.questions WHERE tg_id = $1 AND datetime::date = $2 ORDER BY datetime DESC LIMIT 5", str(user), datetime.date.today())
        df = pd.DataFrame(sql)
        df_str = df.to_string()
        await bot.send_message(chat_id=group, text=f"{df[1][0]}\n<pre>{df_str}</pre>", parse_mode='html', )
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(
            InlineKeyboardButton(
                text='Посмотреть историю сообщений',
                callback_data='Посмотреть историю сообщений'
            )
        )
        await bot.send_message(chat_id=group, text=f"{df[0][0]}\n{df[1][0]}", parse_mode='html', reply_markup=kb_builder.as_markup())
        await message.answer("Ваш вопрос отправлен в службу поддержки. Ожидайте ответа.")
        await state.set_state(FSMFillForm.tp_talk)
    else:
        keyboard = [
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
        ]
        await message.answer(
            text='Для обшения с оператором техподдержки Вам необходимо авторизоваться. Пожалуйста, пришлите свой номер телефона в формате +79XXXXXXXXX,'
                 ' либо email, указанные при регистрации', reply_markup=ReplyKeyboardMarkup(keyboard=keyboard,
                                                                                            resize_keyboard=True,
                                                                                            input_field_placeholder='Введите данные, либо нажмите на кнопку, чтобы поделиться контактом',
                                                                                            one_time_keyboard=True))
        await state.set_state(FSMFillForm.get_auth)


#Роутер для отлавливания любого текста, отправленного пользователем при общении с ИИ
@router.message(F.text, StateFilter(FSMFillForm.ai_talk))
async def func_email(message: Message, state: FSMContext):
    human_message = message.text
    if human_message:
        oper_agent.human_step(human_message)
        faq_embeddings = model.encode(human_message)
        vector_str = f"[{', '.join(map(str, faq_embeddings))}]"
        query = f"""
            SELECT "Вопрос", "Ответ", "Вектор" <=> $1 AS distance
            FROM knowledge
            ORDER BY "Вектор" <=> $1
            LIMIT $2;
            """
        topics = await db_users.fetch(query, vector_str, 2)
        ai_message = oper_agent.ai_step(topics)
    # oper_agent.analyse_stage()
    # ai_message = f'ОТВЕТ ИИ - {message.text}'
    await db_users.execute(
        'INSERT INTO public.questions (tg_id, quest, mess_id, datetime, answer, adress) VALUES ($1, $2, $3, $4, $5, $6)',
        str(message.from_user.id), message.text, str(message.message_id), datetime.datetime.now().strftime('%d/%m/%Y, %H:%M:%S'), ai_message, 'AI')
    keyboard1 = [[KeyboardButton(text="Задать вопрос в группе")], [KeyboardButton(text="Закончить диалог")]]
    await message.reply(text = f'{ai_message}', reply_markup=ReplyKeyboardMarkup(keyboard=keyboard1,
    resize_keyboard=True,
    input_field_placeholder='Либо скорректируйте свой запрос',
    one_time_keyboard=True))


# Роутер если пользователь при регистрации нажал на кнопку Поделиться контактом
@router.message(F.content_type == ContentType.CONTACT, StateFilter(FSMFillForm.get_auth))
async def func_contact(message: Message, state: FSMContext,  bot: Bot):
    user = message.from_user.id
    group = -1002394147014
    await db_users.execute('INSERT INTO public.users (tg_id, name, phone, email, tg_name, lastname) VALUES ($1, $2, $3,$4,$5,$6)',
                           str(message.from_user.id), message.contact.first_name, message.contact.phone_number, None, message.from_user.username, message.contact.last_name)
    await message.reply(f'Регистрация пройдена. Ожидайте ответа')
    sql = await db_users.fetch(
        f"SELECT * FROM public.questions WHERE tg_id = $1 AND datetime::date = $2 ORDER BY datetime DESC LIMIT 5",
        str(user), datetime.date.today())
    df = pd.DataFrame(sql)
    df_str = df.to_string()
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(
            text='Посмотреть историю сообщений',
            callback_data='Посмотреть историю сообщений'
        )
    )
    await bot.send_message(chat_id=group, text=f"{df[0][0]}\n{df[1][0]}", parse_mode='html',
                           reply_markup=kb_builder.as_markup())
    await state.set_state(FSMFillForm.tp_talk)


#Роутер если пользователь при регистрации отправил любой текст. Осуществляется проверка введенных значений
@router.message(F.text, StateFilter(FSMFillForm.get_auth))
async def func_email(message: Message, state: FSMContext,  bot: Bot):
    user = message.from_user.id
    group = -1002394147014
    if re.match(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+[.][a-zA-Z0-9-.]+$)', message.text) is not None:
        await db_users.execute(
            'INSERT INTO public.users (tg_id, email, tg_name) VALUES ($1, $2, $3)',
            str(message.from_user.id),   message.text, message.from_user.username)
        await message.reply(f'Регистрация пройдена. Ожидайте ответа')
        sql = await db_users.fetch(
            f"SELECT * FROM public.questions WHERE tg_id = $1 AND datetime::date = $2 ORDER BY datetime DESC LIMIT 5",
            str(user), datetime.date.today())
        df = pd.DataFrame(sql)
        df_str = df.to_string()
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(
            InlineKeyboardButton(
                text='Посмотреть историю сообщений',
                callback_data='Посмотреть историю сообщений'
            )
        )
        await bot.send_message(chat_id=group, text=f"{df[0][0]}\n{df[1][0]}", parse_mode='html',
                               reply_markup=kb_builder.as_markup())
        await state.set_state(FSMFillForm.tp_talk)
    elif re.match(r'([+]79\d{9})', message.text) is not None:
        await db_users.execute(
            'INSERT INTO public.users (tg_id, phone, tg_name) VALUES ($1, $2, $3)',
            str(message.from_user.id), message.text, message.from_user.username)
        await message.reply(f'Регистрация пройдена. Ожидайте ответа')
        sql = await db_users.fetch(
            f"SELECT * FROM public.questions WHERE tg_id = $1 AND datetime::date = $2 ORDER BY datetime DESC LIMIT 5",
            str(user), datetime.date.today())
        df = pd.DataFrame(sql)
        df_str = df.to_string()
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(
            InlineKeyboardButton(
                text='Посмотреть историю сообщений',
                callback_data='Посмотреть историю сообщений'
            )
        )
        await bot.send_message(chat_id=group, text=f"{df[0][0]}\n{df[1][0]}", parse_mode='html',
                               reply_markup=kb_builder.as_markup())
        await state.set_state(FSMFillForm.tp_talk)
    else:
        await message.reply(f'Это не похоже на почту или телефон. Введите корректные данные')


#Роутер отправки сообщения пользователя в группу техподов
@router.message(F.text, StateFilter(FSMFillForm.tp_talk))
async def func_email(message: Message, state: FSMContext,  bot: Bot):
    user = message.from_user.id
    group = -1002394147014
    await db_users.execute(
        'INSERT INTO public.questions (tg_id, quest, mess_id, datetime, adress) VALUES ($1, $2, $3, $4, $5)',
        str(message.from_user.id), message.text, str(message.message_id), datetime.datetime.now().strftime('%d/%m/%Y, %H:%M:%S'), 'TP')
    sql = await db_users.fetch(
        f"SELECT * FROM public.questions WHERE tg_id = $1 AND datetime::date = $2 ORDER BY datetime DESC LIMIT 5",
        str(user), datetime.date.today())
    df = pd.DataFrame(sql)
    df_str = df.to_string()
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(
            text='Посмотреть историю сообщений',
            callback_data='Посмотреть историю сообщений'
        )
    )
    await bot.send_message(chat_id=group, text=f"{df[0][0]}\n{df[1][0]}", parse_mode='html',
                           reply_markup=kb_builder.as_markup())


@router.callback_query(F.data == 'Посмотреть историю сообщений')
async def user_info(callback_query: CallbackQuery):
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Назад', callback_data='back_mes')],
                                                            [InlineKeyboardButton(text='Вперед', callback_data='next_mes')]])
    user_id = callback_query.message.text.split('\n')[0]
    sql = await db_users.fetch(f"SELECT * FROM public.questions WHERE tg_id = $1 ORDER BY datetime DESC",str(user_id))
    df = pd.DataFrame(sql, columns=['tg_id','Вопрос','mes_id','Дата','Ответ ИИ','Ответ ТП', 'адрес'])
    df_str = df['Вопрос'].iloc[0][:3000]
    print(len(df_str))
    await callback_query.message.answer(text=f"{user_id}\n0\n<pre>{df_str}</pre>", parse_mode='html', reply_markup=inline_keyboard)


@router.callback_query(F.data == 'next_mes')
async def user_info(callback_query: CallbackQuery):
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Назад', callback_data='back_mes')],
                                                            [InlineKeyboardButton(text='Вперед', callback_data='next_mes')]])
    text = callback_query.message.text.split('\n')
    user_id = text[0]
    call_number = int(text[1])
    sql = await db_users.fetch(f"SELECT * FROM public.questions WHERE tg_id = $1 ORDER BY datetime DESC",str(user_id))
    df = pd.DataFrame(sql, columns=['tg_id','Вопрос','mes_id','Дата','Ответ ИИ','Ответ ТП', 'адрес'])
    df_str = df['Вопрос'].iloc[call_number+1][:3000]
    await callback_query.message.edit_text(text=f"{user_id}\n{call_number+1}\n<pre>{df_str}</pre>", parse_mode='html', reply_markup=inline_keyboard)


@router.callback_query(F.data == 'back_mes')
async def user_info(callback_query: CallbackQuery):
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Назад', callback_data='back_mes')],
                                                            [InlineKeyboardButton(text='Вперед', callback_data='next_mes')]])
    text = callback_query.message.text.split('\n')
    user_id = text[0]
    call_number = int(text[1])
    sql = await db_users.fetch(f"SELECT * FROM public.questions WHERE tg_id = $1 ORDER BY datetime DESC",str(user_id))
    df = pd.DataFrame(sql, columns=['tg_id','Вопрос','mes_id','Дата','Ответ ИИ','Ответ ТП', 'адрес'])
    df_str = df['Вопрос'].iloc[call_number-1][:3000]
    await callback_query.message.edit_text(text=f"{user_id}\n{call_number-1}\n<pre>{df_str}</pre>", parse_mode='html', reply_markup=inline_keyboard)


#Роутер наличия реплаев в группе техподов
@router.message(lambda a: a.chat.id == -1002394147014)
async def handle_group_message(message: types.Message):
    if message.chat.type in ["group", "supergroup"]:
        user_id = re.search(r'\d{9}',message.reply_to_message.text).group()
        keyboard2 = [[KeyboardButton(text="Закончить диалог")]]
        print(message.text)
        print(message.reply_to_message.text)
        await db_users.execute('UPDATE public.questions SET answer_tp = $1, adress = $2 WHERE tg_id = $3 AND quest = $4',
                               message.text, 'TP', user_id, message.reply_to_message.text.split('\n')[1])
        await message.bot.send_message(user_id, f"Ответ от службы поддержки:\n\n{message.text}", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard2,
    resize_keyboard=True,
    one_time_keyboard=True))


#Роутер срабатывает при отправки пользователем любого текста кроме команд в состоянии по умолчанию
@router.message(F.text, StateFilter(default_state))
async def none_default_state(message: Message, state: FSMContext):
    await message.answer(
        text='Моя твоя не понимать. Для начала отправь команду /start',
    reply_markup=types.ReplyKeyboardRemove())
    await state.clear()