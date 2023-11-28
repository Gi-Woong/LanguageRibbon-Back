FROM python:3.9-slim
LABEL authors="chaegiung"
ENV PYTHONBUFFERED 1
WORKDIR /app
ADD . .
RUN apt-get update -y
RUN apt-get install pkg-config -y
RUN apt-get install -y default-libmysqlclient-dev
RUN apt install -y libmariadb-dev-compat libmariadb-dev
RUN apt install build-essential -y
RUN pip install -r requirements.txt
EXPOSE 8000
EXPOSE 3306
# CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]