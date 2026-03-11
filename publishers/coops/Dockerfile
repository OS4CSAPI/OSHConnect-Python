FROM python:3.12-slim

WORKDIR /app

# CO-OPS publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + CO-OPS publisher
COPY publishers/ /app/publishers/

# Default: 6min cadence (CO-OPS updates every 6 minutes)
ENV OSH_ADDRESS=os4csapi-osh.duckdns.org
ENV OSH_PORT=443
ENV OSH_USER=os4csapi
ENV OSH_PASS=ogc134mm

ENTRYPOINT ["python", "-m", "publishers.coops.coops_publisher"]
CMD ["--interval", "360"]
