from appstoreserverlibrary.api_client import AsyncAppStoreServerAPIClient, APIException
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier, VerificationException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.LastTransactionsItem import LastTransactionsItem
from appstoreserverlibrary.models.JWSTransactionDecodedPayload import JWSTransactionDecodedPayload
from appstoreserverlibrary.models.JWSRenewalInfoDecodedPayload import JWSRenewalInfoDecodedPayload
from app.core.config import settings
from app.schemas.base import BizException
from app.core.errors import ErrorCode
import os, httpx, asyncio, logging

logger = logging.getLogger(__name__)


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
    key_filename = "SubscriptionKey_CZVQY5KJ7Z.p8"
    path = os.path.join(key_dir, key_filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Private key not found: {path}")
    with open(path, "rb") as f:
        data = f.read()
    return data

root_certificates = load_root_certificates()
enable_online_checks = True
bundle_id = "com.valbara.sporreer"
app_apple_id = 6755963833
private_key = read_private_key()
key_id = "CZVQY5KJ7Z"
issuer_id = settings.APPLE_IAP_ISSUER_ID


prod_client = AsyncAppStoreServerAPIClient(
    private_key,
    key_id,
    issuer_id,
    bundle_id,
    Environment.PRODUCTION
)

sandbox_client = AsyncAppStoreServerAPIClient(
    private_key,
    key_id,
    issuer_id,
    bundle_id,
    Environment.SANDBOX
)

prod_verifier = SignedDataVerifier(
    root_certificates,
    enable_online_checks,
    Environment.PRODUCTION,
    bundle_id,
    app_apple_id
)

sandbox_verifier = SignedDataVerifier(
    root_certificates,
    enable_online_checks,
    Environment.SANDBOX,
    bundle_id,
    app_apple_id
)


async def query_user_subscroption_status(
    transaction_id: str
) -> tuple[LastTransactionsItem | None, JWSTransactionDecodedPayload | None, JWSRenewalInfoDecodedPayload | None]:
    try:
        async def _call_api(api_client: AsyncAppStoreServerAPIClient):
            return await asyncio.wait_for(
                api_client.get_all_subscription_statuses(transaction_id),
                timeout=5.0
            )

        try:
            response = await _call_api(prod_client)
            active_verifier = prod_verifier
        except asyncio.TimeoutError:
            raise BizException(code=ErrorCode.APPLE_SERVICE_ERROR, message="apple.server_timeout")
        except APIException as e:
            status_code = getattr(e, "http_status_code", None)
            logger.error(f"[IAP] Subscription status query failed, http_status_code={status_code}")
            # Python 官方库不会暴露 errorCode，只能用 HTTP 状态码判断环境
            # 404 = 该环境查不到 transaction → 尝试 Sandbox
            # 401 = 正式发布前无法访问生产环境 api 的 fallback → 尝试 Sandbox
            if status_code in (404, 401):
                try:
                    response = await _call_api(sandbox_client)
                    active_verifier = sandbox_verifier
                except asyncio.TimeoutError:
                    raise BizException(code=ErrorCode.APPLE_SERVICE_ERROR, message="apple.server_timeout")
                except Exception:
                    return None, None, None
            else:
                raise BizException(code=ErrorCode.APPLE_SERVICE_ERROR, message="apple.server_error")
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
                    transaction_payload = active_verifier.verify_and_decode_signed_transaction(last_transaction.signedTransactionInfo)
                    renew_payload = active_verifier.verify_and_decode_renewal_info(last_transaction.signedRenewalInfo)
                    signed_date = transaction_payload.signedDate or 0 #renew_payload.signedDate if renew_payload.signedDate else 0
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
        # First try Production
        payload = prod_verifier.verify_and_decode_signed_transaction(jws)
        return payload
    except VerificationException:
        logger.error(f"[IAP] Transaction VerificationException")
        try:
            # Fallback to Sandbox
            payload = sandbox_verifier.verify_and_decode_signed_transaction(jws)
            return payload
        except VerificationException:
            return None


def verify_and_decode_notification_service(signed_payload: str):
    """验证 App Store Server Notifications V2；生产和 Sandbox 均使用同一入口。"""
    try:
        return prod_verifier.verify_and_decode_notification(signed_payload), prod_verifier
    except VerificationException:
        try:
            return sandbox_verifier.verify_and_decode_notification(signed_payload), sandbox_verifier
        except VerificationException:
            return None, None
