FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir sgp4 \
    && pip install --no-cache-dir git+https://github.com/OS4CSAPI/OSHConnect-Python.git

# Copy publisher framework + ISS publisher
COPY publishers/ /app/publishers/

# Default: 30s cadence
ENV OSH_ADDRESS=os4csapi-osh.duckdns.org
ENV OSH_PORT=443
ENV OSH_USER=os4csapi
ENV OSH_PASS=ogc134mm

ENTRYPOINT ["python", "-m", "publishers.iss.iss_publisher"]
CMD ["--interval", "30"]
