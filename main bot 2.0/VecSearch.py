
from database import db_users
from sentence_transformers import SentenceTransformer
import numpy as np

path = r'C:\Users\Максим\Desktop\work\main bot 2.0\locmodels'
model = SentenceTransformer(path)

# def fetch_nearest_vectors(question, k):
#     """
#     Функция для получения K ближайших строк из таблицы на основе векторов.
#     """
#     # Преобразование вектора в строку формата PostgreSQL

#     faq_embeddings = model.encode(question)
#     vector_str = f"[{', '.join(map(str, faq_embeddings))}]"

#     # try:
#     #     # SQL запрос для получения K ближайших векторов
#     query = f"""
#     SELECT "Вопрос", "Ответ", "Вектор" <-> $1 AS distance
#     FROM knowledge
#     ORDER BY "Вектор" <-> $1
#     LIMIT $2;
#     """
    
#     # Выполнение запроса
#     results = db_users.fetch(query, vector_str, k)
#     return results



