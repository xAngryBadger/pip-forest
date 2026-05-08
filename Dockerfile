FROM python:3.10-slim

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY src/ src/
COPY data/ data/

ENV SRF_WEB_MODE=1
ENV SRF_PASSWORD=gazella2024
ENV SRF_DATA_DIR=data
ENV SRF_STEP_TIMEOUT=3600

EXPOSE 8000

CMD ["uvicorn", "src.web.api:app", "--host", "0.0.0.0", "--port", "8000"]
