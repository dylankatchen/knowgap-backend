FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt debugpy==1.8.22

COPY . .

EXPOSE 5001
EXPOSE 5678

CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "/usr/local/bin/hypercorn", "app:app", "--bind", "0.0.0.0:5001"]