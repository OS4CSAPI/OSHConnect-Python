FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir git+https://github.com/OS4CSAPI/OSHConnect-Python.git

COPY publishers/ /app/publishers/

ENV OSH_ADDRESS=
ENV OSH_PORT=443
ENV OSH_USER=
ENV OSH_PASS=
ENV OSH_ROOT=sensorhub
ENV MET_OFFICE_LAND_OBSERVATIONS_API_KEY=
ENV MET_OFFICE_LAND_OBSERVATIONS_API_KEY_FILE=
ENV MET_OFFICE_LAND_OBSERVATIONS_BASE_URL=https://data.hub.api.metoffice.gov.uk/observation-land/1
ENV MET_OFFICE_DATAHUB_API_KEY_HEADER=apikey

ENTRYPOINT ["python", "-m", "publishers.met_office_datahub.met_office_datahub_publisher"]
CMD ["--interval", "3600"]