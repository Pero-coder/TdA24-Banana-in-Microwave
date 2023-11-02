FROM python:3.10-buster
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT python3 -m flask --app app/app.py run --host=0.0.0.0 --port=80
EXPOSE 80
