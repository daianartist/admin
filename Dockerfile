# Используем официальный Python-образ (например, для Python 3.11)
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей (если есть)
COPY requirements.txt /app/

# Устанавливаем зависимости из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в контейнер
COPY . /app/

# Указываем порт, который будет использоваться приложением
EXPOSE 8989

# Указываем Flask, что основное приложение — это main.py
ENV FLASK_APP=main.py

# Команда для запуска Flask-приложения
CMD ["flask", "run", "--host=0.0.0.0", "--port=8989"]
