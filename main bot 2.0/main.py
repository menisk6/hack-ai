import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from BotHelper import HelpGPT, llm
from VecSearch import model
from database import db_users

bot_token = '7111549955:AAH8Crf_diPBkMz01lzORgaBGzotLNTM9wc'

oper_agent = None

async def main():
    await db_users.connect()
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    bot = Bot(bot_token, parse_mode=None)
    # logging.basicConfig(level=logging.INFO)
    
    @dp.message(Command(commands=["start"]))
    async def repl(message):
        global oper_agent
        oper_agent = HelpGPT.from_llm(llm, verbose=False)
        oper_agent.seed_agent()
        # ai_message = oper_agent.ai_step()
        # await message.answer(ai_message)
        await message.answer("Здравствуйте, я бот помощник, какой у вас вопрос?")
    
    @dp.message(F.text)
    async def repl(message):
        if oper_agent is None:
            await message.answer('Используйте команду /start')
        else:
            human_message = message.text
            if human_message:
                oper_agent.human_step(human_message)
                faq_embeddings = model.encode(human_message)
                vector_str = f"[{', '.join(map(str, faq_embeddings))}]"
                query = f"""
                    SELECT "Вопрос", "Ответ", "Вектор" <-> $1 AS distance
                    FROM knowledge
                    ORDER BY "Вектор" <-> $1
                    LIMIT $2;
                    """
                topics = await db_users.fetch(query, vector_str, 2)
                # oper_agent.analyse_stage()
            ai_message = oper_agent.ai_step(topics, API = True)
            await message.answer(ai_message)
            k = oper_agent.analyse_stage()

    @dp.message(~F.text)
    async def empty(message):
        await message.answer('Бот принимает только текст')

    await dp.start_polling(bot)
    await db_users.disconnect()

if __name__ == "__main__":
    asyncio.run(main())