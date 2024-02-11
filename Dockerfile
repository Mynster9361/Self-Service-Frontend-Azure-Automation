FROM python:alpine3.19

RUN apk update
RUN apk add python3
RUN apk add py3-pip

COPY ./src /app/src
COPY ./requirements.txt /app

WORKDIR /app

RUN pip3 install -r requirements.txt

EXPOSE 8000

# configure the container to run in an executed manner
ENTRYPOINT [ "python" ]

CMD ["src/app.py" ]