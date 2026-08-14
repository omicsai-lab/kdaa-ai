FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE requirements.txt requirements-app.txt ./
COPY src ./src
COPY app ./app
COPY configs ./configs
COPY data/demo ./data/demo

RUN python -m pip install --upgrade pip && \
    python -m pip install ".[app]"

RUN useradd --create-home --uid 10001 kdaa && chown -R kdaa:kdaa /app
USER kdaa

EXPOSE 8501 8000


CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
