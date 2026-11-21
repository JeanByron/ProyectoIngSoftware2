FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc pkg-config default-libmysqlclient-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8003
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8003 --noreload"]
