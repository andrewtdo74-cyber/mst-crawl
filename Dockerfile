FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mst_crawler ./mst_crawler
VOLUME /app/data
ENTRYPOINT ["python", "-m", "mst_crawler"]
CMD ["stats"]
