import firebase_admin
from firebase_admin import credentials, storage
import os
import dotenv

dotenv.load_dotenv()

# Path to your downloaded service account key
cred = credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

# Initialize the app with your bucket name
firebase_admin.initialize_app(cred, {
    "storageBucket": 'raylac-72351.appspot.com',
})

# Get a bucket reference
bucket = storage.bucket()

if __name__ == "__main__":
    bucket.blob("eval-runs-dev/test.txt").upload_from_string("Hello, world!")