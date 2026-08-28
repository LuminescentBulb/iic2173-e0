FROM python:3.14
WORKDIR /master-app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY . .
CMD ["fastapi", "run", "main.py", "--port", "8080"]