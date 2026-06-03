FROM python:3.12-slim

WORKDIR /app

COPY publishers/ /app/publishers/

ENV OSH_ADDRESS=
ENV OSH_PORT=443
ENV OSH_USER=
ENV OSH_PASS=

ENTRYPOINT ["python", "-m", "publishers.storebaelt_webcams.storebaelt_webcams_publisher"]
CMD ["--interval", "300"]
