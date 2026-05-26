FROM python:3.12-slim

WORKDIR /app

COPY publishers /app/publishers

ENV PYTHONUNBUFFERED=1
ENV MET_OFFICE_GLOBAL_SPOT_API_KEY=
ENV MET_OFFICE_GLOBAL_SPOT_API_KEY_FILE=
ENV MET_OFFICE_GLOBAL_SPOT_BASE_URL=https://data.hub.api.metoffice.gov.uk/sitespecific/v0
ENV MET_OFFICE_GLOBAL_SPOT_HOURLY_PATH=/point/hourly
ENV MET_OFFICE_DATAHUB_API_KEY_HEADER=apikey

ENTRYPOINT ["python", "-m", "publishers.met_office_global_spot.met_office_global_spot_publisher"]
CMD ["--interval", "3600"]
