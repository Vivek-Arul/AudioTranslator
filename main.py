from flask import Flask, request, jsonify, send_file, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings
from io import BytesIO
import zipfile
import os

app = Flask(__name__)

AZURE_STORAGE_CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

UPLOAD_CONTAINER_NAME = "uploads"
TRANSLATED_CONTAINER_NAME = "translated"

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
upload_container = blob_service_client.get_container_client(UPLOAD_CONTAINER_NAME)
translated_container = blob_service_client.get_container_client(TRANSLATED_CONTAINER_NAME)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files or "config" not in request.files:
        return jsonify({"error": "Missing file or config.json"}), 400

    file = request.files["file"]
    config_file = request.files["config"]

    if not file.filename.endswith(".zip"):
        return jsonify({"error": "Only .zip files supported"}), 400

    # Clear previous blobs
    for container in [upload_container, translated_container]:
        for blob in container.list_blobs():
            container.delete_blob(blob.name)

    # Upload the ZIP file to 'uploads' container
    blob_client = upload_container.get_blob_client(file.filename)
    blob_client.upload_blob(
        file,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/zip")
    )

    # Upload config.json to 'translated' container
    config_blob_client = translated_container.get_blob_client("config.json")
    config_blob_client.upload_blob(
        config_file,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json")
    )

    return jsonify({"message": "Upload successful", "filename": file.filename})

@app.route("/download", methods=["GET"])
def download_translated_zip():
    blobs = [blob.name for blob in translated_container.list_blobs() if blob.name.endswith(".wav")]
    if not blobs:
        return jsonify({"error": "No translated audio found"}), 404

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for name in blobs:
            data = translated_container.get_blob_client(name).download_blob().readall()
            zipf.writestr(name, data)

    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name="translated_audio.zip", mimetype="application/zip")

if __name__ == "__main__":
    app.run(debug=True)
