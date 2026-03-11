FROM python:3.12-slim

WORKDIR /app

# AviationWeather publisher uses only stdlib — no pip dependencies needed

# Copy publisher framework + AWX publisher
COPY publishers/ /app/publishers/

# Default: 5min cadence (METARs update every ~5 min)
ENV OSH_ADDRESS=os4csapi-osh.duckdns.org
ENV OSH_PORT=443
ENV OSH_USER=os4csapi
ENV OSH_PASS=ogc134mm

ENTRYPOINT ["python", "-m", "publishers.aviation_wx.aviation_wx_publisher"]
CMD ["--interval", "300"]
