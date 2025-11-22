import os
from google.cloud import storage

BUCKET_NAME = "stock-datasets-andres"

USE_GCP = os.getenv("USE_GCP", "false").lower() == "true"

if USE_GCP:
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
else:
    client = None
    bucket = None


def download_file(blob_name, local_path):
    if not USE_GCP:
        print("[INFO] GCP desactivado en entorno local")
        return
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)


def upload_file(local_path, blob_name):
    if not USE_GCP:
        print("[INFO] GCP desactivado en entorno local")
        return
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)