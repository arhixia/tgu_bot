import os

from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ.get('TOKEN')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('DB_NAME')
DB_PASS = os.environ.get('DB_PASS')
DB_USER = os.environ.get('DB_USER')
YANDEX_CLOUD_FOLDER = os.environ.get('YANDEX_CLOUD_FOLDER')
YANDEX_CLOUD_API_KEY = os.environ.get('YANDEX_CLOUD_API_KEY')
ACCESS_KEY_S3 = os.environ.get('ACCESS_KEY_S3')
SECRET_KEY_S3 = os.environ.get('SECRET_KEY_S3')
ENDPOINT_URL_S3 = os.environ.get('ENDPOINT_URL_S3')
BUCKET_NAME_S3 = os.environ.get('BUCKET_NAME_S3')