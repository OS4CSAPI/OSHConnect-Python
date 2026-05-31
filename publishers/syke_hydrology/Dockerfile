FROM python:3.12-slim

WORKDIR /app

COPY publishers/ /app/publishers/

ENV OSH_ADDRESS=
ENV OSH_PORT=443
ENV OSH_USER=
ENV OSH_PASS=

ENTRYPOINT ["python", "-m", "publishers.syke_hydrology.syke_hydrology_publisher"]
CMD ["--interval", "900"]
