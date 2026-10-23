# Image durcie : base slim (moins de paquets = moins de CVE), utilisateur non-root.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Correctifs de sécurité Debian disponibles au moment du build
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY requirements.txt .
# pip/setuptools/wheel ne servent qu'à l'installation : on les retire de l'image finale
# (pip embarque ses propres copies d'urllib3 et msgpack, signalées par Trivy)
RUN pip install -r requirements.txt \
    && pip uninstall -y pip setuptools wheel

COPY --chown=root:root app.py .

USER app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--preload", "--worker-tmp-dir", "/tmp", "app:app"]
