
from database import db_users
from sentence_transformers import SentenceTransformer
import numpy as np
import os

path = os.path.dirname(os.path.abspath(__file__)) + r'\locmodels'
# path = r'C:\Users\Максим\Desktop\work\main bot 2.0\locmodels'
# print(path)
model = SentenceTransformer(path)



