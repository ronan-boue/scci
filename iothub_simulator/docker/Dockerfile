FROM artifactory.hydro.qc.ca/dockerhub-docker-remote/python:3.12.1-slim-bullseye

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY cacert-hq-combined.pem /usr/local/share/ca-certificates/proxy.crt
RUN update-ca-certificates

COPY simulator.py /app/simulator.py
COPY requirements.txt /app/requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


EXPOSE 5671 8883 443

CMD ["python3", "simulator.py"]
