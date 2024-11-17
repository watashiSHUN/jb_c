FROM python:3.10-slim-bullseye

RUN apt-get update \
    && apt-get install -y --no-install-recommends --no-install-suggests\
    build-essential \
    && pip install --no-cache-dir  --upgrade pip

# /app is the current working directory
WORKDIR /app 

# install python dependencies
COPY ./requirements.txt /app

RUN pip install --no-cache-dir --requirement /app/requirements.txt

# copy the source code to the container
COPY . /app

EXPOSE 8080

CMD ["python3", "src/main.py"]