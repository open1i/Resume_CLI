FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY resume_cli/ ./resume_cli/

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["resume-cli"]
CMD ["--help"]
