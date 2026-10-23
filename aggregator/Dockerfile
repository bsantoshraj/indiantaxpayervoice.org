# Build from the repository root: docker build -f aggregator/Dockerfile .
FROM python:3.12-slim
RUN useradd --uid 10001 --no-create-home aggregator
WORKDIR /app
COPY aggregator/itv_aggregator ./itv_aggregator
COPY survey ./survey
RUN mkdir -p /srv/stats && chown aggregator /srv/stats
USER aggregator
ENV ITV_SCHEMA=/app/survey/questionnaire-v1.json ITV_OUT_DIR=/srv/stats
ENTRYPOINT ["python", "-m", "itv_aggregator"]
