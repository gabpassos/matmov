import sqlite3
import pandas as pd

datasetFilePath = 'data/database.db'

data = sqlite3.connect(datasetFilePath)

data = pd.read_sql_query('SELECT * FROM formulario_inscricao', data)

print(data)
