from appstoreserverlibrary.api_client import AsyncAppStoreServerAPIClient
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier, VerificationException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.LastTransactionsItem import LastTransactionsItem
from appstoreserverlibrary.models.JWSTransactionDecodedPayload import JWSTransactionDecodedPayload
from appstoreserverlibrary.models.JWSRenewalInfoDecodedPayload import JWSRenewalInfoDecodedPayload
from app.core.config import settings
from app.schemas.base import BizException
from app.core.errors import ErrorCode
import os, httpx, asyncio


def load_root_certificates() -> list[bytes]:
    cert_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "certs")
    # 列出你放在 certs/ 目录下的所有 .cer 文件
    cert_filenames = [
        "AppleIncRootCertificate.cer",
        "AppleRootCA-G2.cer",
        "AppleRootCA-G3.cer",
    ]
    certs = []
    for fn in cert_filenames:
        path = os.path.join(cert_dir, fn)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Root certificate not found: {path}")
        with open(path, "rb") as f:
            data = f.read()
        certs.append(data)
    return certs

def read_private_key() -> bytes:
    key_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "certs")
    key_filename = "SubscriptionKey_5RY6JV82K7.p8"
    path = os.path.join(key_dir, key_filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Private key not found: {path}")
    with open(path, "rb") as f:
        data = f.read()
    return data

root_certificates = load_root_certificates()
enable_online_checks = True
bundle_id = "com.valbara.sporreer"
environment = Environment.SANDBOX
app_apple_id = 6755963833 # appAppleId must be provided for the Production environment
private_key = read_private_key()
key_id = "5RY6JV82K7"
issuer_id = settings.APPLE_IAP_ISSUER_ID

client = AsyncAppStoreServerAPIClient(
    private_key,
    key_id,
    issuer_id,
    bundle_id,
    environment
)

signed_data_verifier = SignedDataVerifier(
    root_certificates, 
    enable_online_checks,
    environment,
    bundle_id,
    app_apple_id
)


async def query_user_subscroption_status(
    transaction_id: str
) -> tuple[LastTransactionsItem | None, JWSTransactionDecodedPayload | None, JWSRenewalInfoDecodedPayload | None]:
    try:
        try:
            response = await asyncio.wait_for(client.get_all_subscription_statuses(transaction_id), timeout=5.0)
        except asyncio.TimeoutError:
            raise BizException(code=ErrorCode.APPLE_SERVICE_ERROR, message="apple.server_timeout")
        except httpx.HTTPError:
            raise BizException(code=ErrorCode.APPLE_SERVICE_ERROR, message="apple.server_error")

        if not response.data:
            return None, None, None
        for item in response.data:
            # 订阅组
            if item.subscriptionGroupIdentifier == "21846901":
                latest_tx = None
                latest_renew_payload = None
                latest_transaction_payload = None
                latest_signed_date = -1
                for last_transaction in item.lastTransactions:
                    transaction_payload = signed_data_verifier.verify_and_decode_signed_transaction(last_transaction.signedTransactionInfo)
                    renew_payload = signed_data_verifier.verify_and_decode_renewal_info(last_transaction.signedRenewalInfo)
                    signed_date = renew_payload.signedDate if renew_payload.signedDate else 0
                    if signed_date > latest_signed_date:
                        latest_signed_date = signed_date
                        latest_renew_payload = renew_payload
                        latest_transaction_payload = transaction_payload
                        latest_tx = last_transaction
                return latest_tx, latest_transaction_payload, latest_renew_payload
    
    except VerificationException as e:
        #print(e)
        return None, None, None


async def verify_and_decode_transaction_service(
    jws: str
) -> JWSTransactionDecodedPayload | None:
    try:
        payload = signed_data_verifier.verify_and_decode_signed_transaction(jws)
        #print(payload)
    except VerificationException as e:
        #print(e)
        return None
    return payload
