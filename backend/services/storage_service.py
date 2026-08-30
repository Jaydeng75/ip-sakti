import os
import uuid


UPLOAD_DIR = "uploads"


def save_file(file):
    

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    extension = ""

    if file.filename and "." in file.filename:
        extension = "." + file.filename.split(".")[-1]

    stored_name = str(uuid.uuid4()) + extension

    path = os.path.join(
        UPLOAD_DIR,
        stored_name
    )

    with open(path, "wb") as buffer:
        buffer.write(file.file.read())

    return {
        "path": path,
        "provider": "local"
    }