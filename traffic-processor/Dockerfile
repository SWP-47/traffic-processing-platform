FROM python:3.11-slim

RUN apt-get update && apt-get install -y libpcap-dev

WORKDIR /tp

COPY ./software-part .

RUN pip install -r ./software-part/requirements.txt

RUN if [ ! -f ./software-part/.env ]; then cp ./software-part/.env.example .env; fi

CMD ["python3", "./software-part/tp_packet_counter.py"]