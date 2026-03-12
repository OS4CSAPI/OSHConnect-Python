FROM python:3.12-slim

WORKDIR /app

# OpenSky publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + OpenSky publisher
COPY publishers/ /app/publishers/

# Default: 5min cadence (OpenSky anonymous: 400 credits/day)
# Server credentials must be supplied via docker-compose.yml or .env
ENV OSH_ADDRESS=
ENV OSH_PORT=443
ENV OSH_USER=
ENV OSH_PASS=

ENTRYPOINT ["python", "-m", "publishers.opensky.opensky_publisher"]
CMD ["--interval", "300"]
