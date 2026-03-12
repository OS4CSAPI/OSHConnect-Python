FROM python:3.12-slim

WORKDIR /app

# AviationWeather publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + AWX publisher
COPY publishers/ /app/publishers/

# Default: 5min cadence (METARs update every ~5 min)
# Server credentials must be supplied via docker-compose.yml or .env
ENV OSH_ADDRESS=
ENV OSH_PORT=443
ENV OSH_USER=
ENV OSH_PASS=

ENTRYPOINT ["python", "-m", "publishers.aviation_wx.aviation_wx_publisher"]
CMD ["--interval", "300"]
