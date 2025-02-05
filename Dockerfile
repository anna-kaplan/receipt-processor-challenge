FROM python:3

WORKDIR /app

RUN pip install Flask
RUN pip install flask_expects_json

COPY src/ /app/src

EXPOSE 5000

CMD ["python3", "src/receipt_api.py"]
