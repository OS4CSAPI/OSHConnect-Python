FROM python:3.12-slim

WORKDIR /app

# OpenSky publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + OpenSky publisher
COPY publishers/ /app/publishers/

# Default: 5min cadence (OpenSky anonymous: 400 credits/day)
ENV OSH_ADDRESS=os4csapi-osh.duckdns.org
ENV OSH_PORT=443
ENV OSH_USER=os4csapi
ENV OSH_PASS=ogc134mm

ENTRYPOINT ["python", "-m", "publishers.opensky.opensky_publisher"]
CMD ["--interval", "300"]
