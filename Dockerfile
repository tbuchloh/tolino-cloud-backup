FROM python:3-alpine

ADD requirements.txt \
    *.py \
    /app/

RUN pip install -r /app/requirements.txt

WORKDIR /app

ENTRYPOINT [ "python", "/app/tolino-cloud-backup.py" ]
