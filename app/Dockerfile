FROM python:3.11-slim

# Bonnes pratiques Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY app.py .

# Port exposé par l'application Flask
EXPOSE 5000

# Commande de lancement
CMD ["python", "app.py"]
