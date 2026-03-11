FROM python:3.12-slim

WORKDIR /app

# NDBC publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + NDBC publisher
COPY publishers/ /app/publishers/

# Default: 1h cadence (NDBC realtime2 updates hourly)
ENV OSH_ADDRESS=os4csapi-osh.duckdns.org
ENV OSH_PORT=443
ENV OSH_USER=os4csapi
ENV OSH_PASS=ogc134mm

ENTRYPOINT ["python", "-m", "publishers.ndbc.ndbc_publisher"]
CMD ["--interval", "3600"]
