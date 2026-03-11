FROM python:3.12-slim

WORKDIR /app

# Install dependencies (no additional pip packages needed beyond stdlib)
RUN pip install --no-cache-dir git+https://github.com/OS4CSAPI/OSHConnect-Python.git

# Copy publisher framework + USGS Water publisher
COPY publishers/ /app/publishers/

# Default: 15min cadence (matches USGS reporting frequency)
ENV OSH_ADDRESS=os4csapi-osh.duckdns.org
ENV OSH_PORT=443
ENV OSH_USER=os4csapi
ENV OSH_PASS=ogc134mm
# Optional: USGS API key for higher rate limits
# ENV USGS_API_KEY=

ENTRYPOINT ["python", "-m", "publishers.usgs_water.usgs_water_publisher"]
CMD ["--interval", "900"]
