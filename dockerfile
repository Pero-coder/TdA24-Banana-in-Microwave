FROM python:3.10-buster
WORKDIR /
ARG MONGO_PWD
ARG MONGO_USERNAME
ENV MONGO_PWD=$MONGO_PWD
ENV MONGO_USERNAME=$MONGO_USERNAME
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT python3 -m flask --app app.py run --host=0.0.0.0 --port=80
EXPOSE 80
