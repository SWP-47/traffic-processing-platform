FROM python:3.11-slim

RUN apt-get update && apt-get install -y libpcap-dev

WORKDIR /cn

COPY . .

RUN pip install -r requirements.txt

# RUN if [ ! -f .env ]; then cp .env.example .env; fi

CMD ["python3", "cn_demo_1.py"]