FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
EXPOSE 8501

CMD ["sh", "-c", "streamlit run /app/streamlit_app.py --server.address 0.0.0.0 --server.port ${PORT:-8501}"]
