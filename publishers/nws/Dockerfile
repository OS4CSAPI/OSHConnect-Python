FROM python:3.12-slim

WORKDIR /app

# NWS publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + NWS publisher
COPY publishers/ /app/publishers/

# Default: 1h cadence
ENV OSH_ADDRESS=os4csapi-osh.duckdns.org
ENV OSH_PORT=443
ENV OSH_USER=os4csapi
ENV OSH_PASS=ogc134mm

ENTRYPOINT ["python", "-m", "publishers.nws.nws_publisher"]
CMD ["--interval", "3600"]
