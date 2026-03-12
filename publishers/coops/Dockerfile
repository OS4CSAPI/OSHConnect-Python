FROM python:3.12-slim

WORKDIR /app

# CO-OPS publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + CO-OPS publisher
COPY publishers/ /app/publishers/

# Default: 6min cadence (CO-OPS updates every 6 minutes)
# Server credentials must be supplied via docker-compose.yml or .env
ENV OSH_ADDRESS=
ENV OSH_PORT=443
ENV OSH_USER=
ENV OSH_PASS=

ENTRYPOINT ["python", "-m", "publishers.coops.coops_publisher"]
CMD ["--interval", "360"]
