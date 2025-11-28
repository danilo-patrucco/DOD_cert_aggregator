FROM alpine:3.20

WORKDIR /certs
COPY certificates/ ./certificates/

CMD ["sh"]