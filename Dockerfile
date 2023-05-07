FROM python:alpine
RUN pip install emoji requests flask waitress
COPY app /app
WORKDIR /app
ENTRYPOINT python -u main.py