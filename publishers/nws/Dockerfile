FROM python:3.12-slim

WORKDIR /app

# NWS publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + NWS publisher
COPY publishers/ /app/publishers/

# Default: 1h cadence
# Server credentials must be supplied via docker-compose.yml or .env
ENV OSH_ADDRESS=
ENV OSH_PORT=443
ENV OSH_USER=
ENV OSH_PASS=

ENTRYPOINT ["python", "-m", "publishers.nws.nws_publisher"]
CMD ["--interval", "3600"]
