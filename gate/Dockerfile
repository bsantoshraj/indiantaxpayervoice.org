FROM python:3.15-slim
RUN useradd --uid 10002 --no-create-home gate
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY itv_gate ./itv_gate
COPY static ./static
USER gate
EXPOSE 8000
CMD ["python", "-m", "itv_gate"]
