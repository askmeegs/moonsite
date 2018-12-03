FROM gcr.io/mooninfo-2018/moonsite-base:latest
COPY . /app
WORKDIR /app
ENTRYPOINT ["python","app.py"]