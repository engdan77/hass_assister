FROM python:3.7-alpine

LABEL maintainer="Daniel Engvall"

ENV ROOT_PASSWORD root
ENV TZ Europe/Stockholm

# Update according to local environment or use --build-arg UID=xxx at build
ARG UID=1004
ARG GID=100

RUN adduser -u ${UID} -D -g '' appuser

RUN apk update	&& apk upgrade && apk add bash && apk add openssh \
		&& sed -i s/#PermitRootLogin.*/PermitRootLogin\ yes/ /etc/ssh/sshd_config \
		&& echo "root:${ROOT_PASSWORD}" | chpasswd \
		&& rm -rf /var/cache/apk/* /tmp/*

RUN apk add libgcc
RUN apk add linux-headers
RUN apk add libc-dev
RUN apk add gcc
RUN apk add make

RUN apk add supervisor

RUN apk add sudo

RUN mkdir /etc/supervisor.d; \
    mkdir /etc/init-scripts; \
    mkdir /etc/settings.d

COPY supervisord.conf /etc/supervisord.conf

COPY entrypoint.sh /

COPY . app/
WORKDIR /app
# COPY requirements.txt /app/
RUN chown -R appuser /app

RUN pip install -r requirements.txt

RUN echo appuser:root | chpasswd

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]