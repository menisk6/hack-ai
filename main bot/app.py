import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from VecSearch import model
from database import db_users
from BotHelper import HelpGPT, llm
from contextlib import asynccontextmanager

class Request(BaseModel):
    question: str


class Response(BaseModel):
    answer: str
    class_1: str
    class_2: str

# app = FastAPI()


# @app.get("/")
# def index():
#     return {"text": "Интеллектуальный помощник оператора службы поддержки."}

    
# @app.post("/predict")
async def predict_sentiment(request: Request):
    oper_agent = HelpGPT.from_llm(llm, verbose=False)
    oper_agent.seed_agent()
    question_embedding = model.encode(request.question)
    vector_str = f"[{', '.join(map(str, question_embedding))}]"
    query = f"""
            SELECT "Вопрос", "Ответ", "Вектор" <-> $1 AS distance
            FROM knowledge
            ORDER BY "Вектор" <=> $1
            LIMIT $2;
            """
    topics = await db_users.fetch(query, vector_str, 2)
    ai_message = oper_agent.ai_step(topics)
    response = Response(
        answer=ai_message,
        class_1='МОНЕТИЗАЦИЯ', # Классификатор оценивается опционально; при отсутствии можно задать константное значение.
        class_2='Отключение/подключение монетизации', # Классификатор оценивается опционально; при отсутствии можно задать константное значение.
    )
    return response

# if __name__ == "__main__":
#     host = "localhost" # Сконфигурируйте host согласно настройкам вашего сервера.
#     config = uvicorn.Config(app, host=host, port=8000)
#     server = uvicorn.Server(config)
#     loop = asyncio.get_running_loop()
#     t = [loop.create_task(server.serve())]
#     loop.run_until_complete(asyncio.wait(t))

# Создание экземпляра FastAPI


from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import asyncio

# Импорт вашей функции
# from your_module import predict_sentiment

app = FastAPI()

# Пример модели запроса с использованием Pydantic
class SentimentRequest(BaseModel):
    question: str

# Пример модели ответа с использованием Pydantic
class SentimentResponse(BaseModel):
    answer: str
    class_1: str
    class_2: str

# Инициализация FastAPI-приложения и его маршрутов

@app.post("/predict_sentiment", response_model=SentimentResponse)
async def predict_sentiment_api(request: SentimentRequest):
    """
    Принимает вопрос и возвращает оценку чувствительности.
    """
    try:
        # Вызов вашей функции predict_sentiment и передача аргументов
        response = await predict_sentiment(request)
        return SentimentResponse(
            answer=response.answer,
            class_1=response.class_1,
            class_2=response.class_2
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Запуск с помощью Uvicorn:
# uvicorn app:app --reload
