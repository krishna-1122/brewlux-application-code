FROM mysql:8.4

ENV MYSQL_DATABASE=brewlux

COPY schema.sql /docker-entrypoint-initdb.d/01-schema.sql

EXPOSE 3306
