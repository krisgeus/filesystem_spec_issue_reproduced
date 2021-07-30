FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY head-and-get-script.py ./head-and-get-script.py

CMD [ "python", "./head-and-get-script.py" ]