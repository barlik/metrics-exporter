FROM quay.io/rhscl/python-36-rhel7:latest

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

USER root
RUN mkdir /app
WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./
USER 1001

ENTRYPOINT ["python", "/app/app.py"]
