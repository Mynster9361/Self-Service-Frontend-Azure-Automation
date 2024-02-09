FROM python:slim

RUN apt-get update && \
    apt-get install -y python3 python3-pip

COPY ./src /app/src
COPY ./requirements.txt /app

WORKDIR /app

RUN pip3 install -r requirements.txt

EXPOSE 8000

# configure the container to run in an executed manner
ENTRYPOINT [ "python" ]

CMD ["src/app.py" ]