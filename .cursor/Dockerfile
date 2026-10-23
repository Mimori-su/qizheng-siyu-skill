FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends git sudo python3 openjdk-21-jre-headless ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN id ubuntu >/dev/null 2>&1 || useradd -m -s /bin/bash ubuntu
USER ubuntu
WORKDIR /home/ubuntu
