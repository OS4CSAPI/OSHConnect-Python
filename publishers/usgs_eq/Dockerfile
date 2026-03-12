FROM python:3.12-slim

LABEL maintainer="OS4CSAPI" \
      description="USGS Earthquake Feed publisher — polls all_day GeoJSON every 60s"

WORKDIR /app
COPY bootstrap_helpers.py publishers/bootstrap_helpers.py
COPY publishers/__init__.py publishers/__init__.py
COPY publishers/usgs_eq/ publishers/usgs_eq/

# No pip install needed — stdlib only

# Server credentials must be supplied via docker-compose.yml or .env
ENV OSH_ADDRESS= \
    OSH_PORT=443 \
    OSH_USER= \
    OSH_PASS=

CMD ["python", "-u", "-m", "publishers.usgs_eq.usgs_eq_publisher", "--interval", "60"]
