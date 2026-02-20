FROM python:3.12-slim

WORKDIR /app
COPY frontend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY frontend /app/frontend
EXPOSE 8501

CMD ["streamlit", "run", "/app/frontend/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
