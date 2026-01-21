import os
import json
import socket
from flask import Flask, request, render_template_string, redirect, url_for
import redis
from google.cloud import storage
import datetime

app = Flask(__name__)

# --- Configuration ---
# Récupération des variables d'environnement (Best Practice K8s/12-factor)
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
BUCKET_NAME = os.environ.get("BUCKET_NAME")
PROJECT_ID = os.environ.get("PROJECT_ID")  # Optionnel si détecté auto par la lib GCP

# Connexion Redis
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    r.ping()  # Test connection
except Exception as e:
    print(f"Erreur connexion Redis: {e}")
    r = None

# --- HTML Template (Simple) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CloudMemo - StudentCorp</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background-color: #f4f4f4; padding: 20px; border-radius: 5px; }
        .message { background: white; padding: 10px; margin-bottom: 5px; border-left: 4px solid #3498db; }
        .status { color: green; font-weight: bold; }
        .error { color: red; font-weight: bold; }
        .info { font-size: 0.8em; color: #666; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>☁️ CloudMemo</h1>

    <div class="container">
        <h3>Ajouter un mémo</h3>
        <form action="/add" method="post">
            <input type="text" name="memo" placeholder="Penser à éteindre les VMs..." required style="width: 70%;">
            <button type="submit">Ajouter</button>
        </form>
    </div>

    <br>

    <div class="container">
        <h3>Actions Cloud</h3>
        <form action="/archive" method="post">
            <button type="submit" style="background-color: #e67e22; color: white; border: none; padding: 10px;">📦 Archiver vers GCS</button>
        </form>
        {% if status %}
            <p class="status">{{ status }}</p>
        {% endif %}
        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}
    </div>

    <h3>Liste des mémos (Redis)</h3>
    {% for memo in memos %}
        <div class="message">{{ memo }}</div>
    {% else %}
        <p>Aucun mémo pour le moment.</p>
    {% endfor %}

    <div class="info">
        Server Hostname: {{ hostname }} <br>
        Redis Host: {{ redis_host }} <br>
        Target Bucket: {{ bucket_name }}
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    status = request.args.get("status")
    error = request.args.get("error")

    memos = []
    if r:
        try:
            memos = r.lrange("memos", 0, -1)
        except redis.ConnectionError:
            error = "Redis non disponible"

    return render_template_string(
        HTML_TEMPLATE,
        memos=memos,
        hostname=socket.gethostname(),
        redis_host=REDIS_HOST,
        bucket_name=BUCKET_NAME,
        status=status,
        error=error,
    )


@app.route("/add", methods=["POST"])
def add_memo():
    memo = request.form.get("memo")
    if memo and r:
        r.lpush("memos", memo)
    return redirect(url_for("index"))


@app.route("/archive", methods=["POST"])
def archive_to_gcs():
    if not BUCKET_NAME:
        return redirect(
            url_for("index", error="Configuration manquante: BUCKET_NAME non défini.")
        )

    if not r:
        return redirect(
            url_for("index", error="Redis non disponible, impossible d'archiver.")
        )

    try:
        # 1. Récupération des données
        memos = r.lrange("memos", 0, -1)
        data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "hostname": socket.gethostname(),
            "memos": memos,
        }
        json_data = json.dumps(data, indent=4)

        # 2. Upload vers GCS
        # L'authentification se fait automatiquement via GOOGLE_APPLICATION_CREDENTIALS
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)

        filename = f"backup-memos-{int(datetime.datetime.now().timestamp())}.json"
        blob = bucket.blob(filename)
        blob.upload_from_string(json_data, content_type="application/json")

        return redirect(
            url_for(
                "index",
                status=f"Succès! Fichier {filename} uploadé dans {BUCKET_NAME}.",
            )
        )

    except Exception as e:
        return redirect(url_for("index", error=f"Erreur GCS: {str(e)}"))


if __name__ == "__main__":
    # Ecoute sur 0.0.0.0 pour Docker
    app.run(host="0.0.0.0", port=5000)
