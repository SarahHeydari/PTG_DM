FROM python:3.12-slim

RUN apt-get update && apt-get -y upgrade && apt-get install -y \
    binutils \
    proj-bin libproj-dev \
    gdal-bin libgdal-dev \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["sh", "entrypoint.sh"]
