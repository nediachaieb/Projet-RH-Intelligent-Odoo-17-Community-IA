# image officielle Odoo 17
FROM odoo:17
USER root

# Installation des dépendances système + Python
RUN set -eux; \
    # Force la mise à jour et tolère les incohérences temporaires
    apt-get update --allow-releaseinfo-change || true; \
    # Réessaie plusieurs fois pour pallier les miroirs en cours de sync
    apt-get install -y --no-install-recommends     \
        libglib2.0-0     \
        libgl1-mesa-glx  \
        python3-dev      \
        gcc              \
    || { apt-get clean; rm -rf /var/lib/apt/lists/*; \
         apt-get update; apt-get install -y --no-install-recommends \
            libglib2.0-0 libgl1-mesa-glx python3-dev gcc; }; \
    # Installation des paquets Python nécessaires
    pip install --no-cache-dir --timeout=10000     \
        PyMuPDF beautifulsoup4; \
    # Nettoyage
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

USER odoo