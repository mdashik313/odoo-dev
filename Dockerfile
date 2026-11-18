# Odoo 18.0 — application image

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# System libraries needed to build/run packages from requirements.txt
# (psycopg2, lxml, Pillow, python-ldap, cryptography, reportlab, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libffi-dev \
        libjpeg62-turbo-dev \
        libldap2-dev \
        libopenjp2-7-dev \
        libpq-dev \
        libsasl2-dev \
        libssl-dev \
        libtiff-dev \
        libwebp-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        fonts-dejavu-core \
        fonts-liberation \
        shared-mime-info \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Patched-Qt wkhtmltopdf (required by Odoo for PDF headers/footers).
# Version recommended for Odoo 16+: 0.12.6.1-3
RUN apt-get update && apt-get install -y --no-install-recommends \
        fontconfig \
        libxrender1 \
        xfonts-75dpi \
        xfonts-base \
    && curl -o /tmp/wkhtmltox.deb -sSL \
        https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && echo "98ba0d157b50d36f23bd0dedf4c0aa28c7b0c50fcdcdc54aa5b6bbba81a3941d  /tmp/wkhtmltox.deb" | sha256sum -c - \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/wkhtmltox.deb \
    && wkhtmltopdf --version \
    && wkhtmltoimage --version

# Non-root user for running Odoo; filestore lives in /var/lib/odoo
RUN useradd --system --create-home --home-dir /var/lib/odoo --shell /bin/bash odoo \
    && mkdir -p /var/lib/odoo \
    && chown -R odoo:odoo /var/lib/odoo

WORKDIR /opt/odoo

# Install Python dependencies first so dependency layers cache well
COPY requirements.txt /opt/odoo/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the Odoo 18.0 source tree into the image (ownership set to odoo during copy)
COPY --chown=odoo:odoo . /opt/odoo

USER odoo
