FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/
COPY start.sh .
RUN chmod +x /app/start.sh

RUN mkdir -p /app/output

EXPOSE 7860

CMD ["/app/start.sh"]
