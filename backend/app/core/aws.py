from datetime import datetime

import boto3
from botocore.config import Config

from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


def generate_presigned_upload_url(s3_key: str, mime_type: str, expires: int = 900) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": s3_key,
            "ContentType": mime_type,
        },
        ExpiresIn=expires,
        HttpMethod="PUT",
    )


def generate_cloudfront_signed_url(s3_key: str, expires_at: datetime) -> str:
    from botocore.signers import CloudFrontSigner
    import rsa

    def rsa_signer(message: bytes) -> bytes:
        private_key = rsa.PrivateKey.load_pkcs1(
            settings.cloudfront_private_key_pem.encode()
        )
        return rsa.sign(message, private_key, "SHA-1")

    cf_url = f"https://{settings.CLOUDFRONT_DOMAIN}/{s3_key}"
    signer = CloudFrontSigner(settings.CLOUDFRONT_KEY_PAIR_ID, rsa_signer)
    return signer.generate_presigned_url(cf_url, date_less_than=expires_at)


def delete_s3_object(s3_key: str) -> None:
    client = get_s3_client()
    client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
