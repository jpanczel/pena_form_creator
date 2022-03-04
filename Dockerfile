# syntax = docker/dockerfile:1.3

FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

ENV GOOGLE_APPLICATION_CREDENTIALS="app/tmp/pena_form_service_account.json"

COPY . .

ENTRYPOINT [ "python" ]

CMD [ "app/app.py" ]

#RUN --mount=type=secret,id=client_secret,dst=/tmp/client_secret_form_creator.json python3 app.py

