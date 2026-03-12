FROM python:3.12-slim

WORKDIR /app

# NDBC publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + NDBC publisher
COPY publishers/ /app/publishers/

# Default: 1h cadence (NDBC realtime2 updates hourly)
# Server credentials must be supplied via docker-compose.yml or .env
ENV OSH_ADDRESS=
ENV OSH_PORT=443
ENV OSH_USER=
ENV OSH_PASS=

ENTRYPOINT ["python", "-m", "publishers.ndbc.ndbc_publisher"]
CMD ["--interval", "3600"]
