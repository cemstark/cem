import json
import os
import secrets
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "qr_mode": "info_page",  # "info_page" | "target_url"
    "target_url": "https://example.com",
    "append_run_id_to_target_url": False,
    "public_base_url": "",  # e.g. "https://your-app.onrender.com" (used for saving qr.png without request context)
    "qr_save_to_desktop": True,
    "qr_output_filename": "qr.png",
    "info_title": "Bilgiler",
    "info_body": "Buraya bilgilerinizi yazın.",
    "admin_token": "",
}


def _config_path() -> str:
    env_path = (os.getenv("QR_CONFIG_PATH") or "").strip()
    if env_path:
        return env_path
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "config.json")


def load_config() -> Dict[str, Any]:
    path = _config_path()
    env_admin_token = (os.getenv("ADMIN_TOKEN") or "").strip()
    if not os.path.exists(path):
        cfg = dict(DEFAULT_CONFIG)
        cfg["admin_token"] = env_admin_token or secrets.token_urlsafe(18)
        # If ADMIN_TOKEN is provided, we still write the config file so other fields persist.
        save_config(cfg)
        return cfg

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg if isinstance(cfg, dict) else {})

    # Allow overriding admin token via environment (recommended for cloud deploys).
    if env_admin_token:
        merged["admin_token"] = env_admin_token
    elif not merged.get("admin_token"):
        merged["admin_token"] = secrets.token_urlsafe(18)
        save_config(merged)

    return merged


def save_config(cfg: Dict[str, Any]) -> None:
    path = _config_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


