# FILEPATH: /c:/Users/linmi/Documents/key-distributor/src/Dockerfile

FROM python:3.12-alpine

ENV KD_PORT=4434

WORKDIR /app

COPY requirements.txt .
COPY src/app.py .

RUN apk add build-base libffi-dev
RUN pip install -r requirements.txt

CMD ["python", "app.py"]
