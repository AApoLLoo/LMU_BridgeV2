import os
import sys
from typing import Callable, Optional


def _existing_file(path: str) -> bool:
    return bool(path) and os.path.isfile(path)


def resolve_ca_bundle() -> Optional[str]:
    """Return a valid CA bundle path if one is available on this machine."""
    env_keys = ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE")
    for key in env_keys:
        value = os.environ.get(key, "")
        if _existing_file(value):
            return value

    candidates = []

    try:
        import certifi

        certifi_path = certifi.where()
        if certifi_path:
            candidates.append(certifi_path)
    except Exception:
        pass

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        exe_dir = os.path.dirname(sys.executable)
        candidates.extend(
            [
                os.path.join(meipass, "certifi", "cacert.pem"),
                os.path.join(meipass, "cacert.pem"),
                os.path.join(exe_dir, "_internal", "certifi", "cacert.pem"),
                os.path.join(exe_dir, "certifi", "cacert.pem"),
                os.path.join(exe_dir, "cacert.pem"),
            ]
        )

    for path in candidates:
        if _existing_file(path):
            return path

    return None


def bootstrap_tls_env(log: Optional[Callable[[str], None]] = None) -> Optional[str]:
    """Normalize CA env vars so requests/socket clients use a valid certificate bundle."""
    ca_path = resolve_ca_bundle()

    if ca_path:
        os.environ["REQUESTS_CA_BUNDLE"] = ca_path
        os.environ["SSL_CERT_FILE"] = ca_path
        os.environ["CURL_CA_BUNDLE"] = ca_path
        if log:
            log(f"[TLS] Bundle CA utilise: {ca_path}")
    else:
        if log:
            log("[TLS] Aucun bundle CA explicite trouve, fallback TLS systeme.")

    return ca_path

