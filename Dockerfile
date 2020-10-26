FROM mongo:latest

WORKDIR /maffin

COPY requirements.txt ./
RUN apt-get update && apt-get install -y build-essential python3
RUN apt-get install -y screen
RUN apt-get install -y python3-setuptools
RUN apt-get install -y python3-pip
RUN pip3 install --no-cache-dir -r requirements.txt


COPY . .


CMD ["sh","docker_start.sh"]