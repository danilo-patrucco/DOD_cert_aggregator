FROM registry1.dso.mil/ironbank/redhat/ubi/ubi9-minimal:9.4

COPY certificates/* /etc/ssl/certs
