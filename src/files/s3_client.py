from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4
from aiobotocore.session import get_session
from src.db.config import ACCESS_KEY_S3, SECRET_KEY_S3, ENDPOINT_URL_S3, BUCKET_NAME_S3


class S3Client:
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        bucket_name: str,
        region_name: str = "ru-1",
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self):
        async with self.session.create_client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
        ) as client:
            yield client 

    
    async def upload_file(self, data: bytes, key: str, content_type: str = "image/png") -> str:
        """загружает файл в S3, возвращает ключ"""
        async with self.get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
                ContentDisposition="inline",
            )
        return key
    

    async def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        """возвращает presigned URL для приватного файла"""
        async with self.get_client() as client:
            url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires,
            )
            import asyncio
            if asyncio.iscoroutine(url):
                url = await url
        return url

    async def delete_file(self, key: str) -> None:
        async with self.get_client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=key)


    def key_for_task(self, filename: str = "task.png") -> str:
        """tasks/YYYY/MM/DD/uuid.png"""
        now = datetime.now(timezone.utc)
        ext = Path(filename).suffix or ".png"
        return f"tasks/{now.year:04d}/{now.month:02d}/{now.day:02d}/{uuid4().hex}{ext}"

    def key_for_answer(self, student_id: int, task_id: int) -> str:
        """answers/student_id/task_id/uuid.jpg"""
        return f"answers/{student_id}/{task_id}/{uuid4().hex}.jpg"
    


_s3: Optional[S3Client] = None

def get_s3() -> S3Client: #клиент
    global _s3
    if _s3 is None:
        _s3 = S3Client(
            access_key=ACCESS_KEY_S3,
            secret_key=SECRET_KEY_S3,
            endpoint_url=ENDPOINT_URL_S3,
            bucket_name=BUCKET_NAME_S3,
        )
    return _s3
    
