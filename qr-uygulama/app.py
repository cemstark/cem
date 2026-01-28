import io
import os
from pathlib import Path
import secrets
import urllib.parse

try:
    import qrcode
except ModuleNotFoundError:  # pragma: no cover
    qrcode = None  # type: ignore[assignment]
from flask import Flask, Response, redirect, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from config_store import load_config, save_config


RUN_ID = secrets.token_urlsafe(8)
_SAVED_ONCE = False
_LAST_SAVED_PATH: str | None = None
_LAST_SAVE_ERROR: str | None = None

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)


def _with_query(url: str, extra_params: dict) -> str:
    parsed = urllib.parse.urlparse(url)
    qs = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    qs.update({k: str(v) for k, v in extra_params.items() if v is not None})
    new_query = urllib.parse.urlencode(qs, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))


def _public_base_url() -> str:
    # request.url_root includes trailing slash
    return request.url_root.rstrip("/")


def _qr_payload_url(cfg: dict) -> str:
    mode = (cfg.get("qr_mode") or "info_page").strip()

    if mode == "target_url":
        target = (cfg.get("target_url") or "").strip()
        if not target:
            return _with_query(_public_base_url() + url_for("info"), {"rid": RUN_ID})
        if cfg.get("append_run_id_to_target_url"):
            return _with_query(target, {"rid": RUN_ID})
        return target

    # default: open this app's /info page (your "site")
    return _with_query(_public_base_url() + url_for("info"), {"rid": RUN_ID})


def _guess_desktop_dir() -> Path:
    home = Path.home()
    candidates = [
        home / "OneDrive" / "Masaüstü",
        home / "OneDrive" / "Desktop",
        home / "Desktop",
        home / "Masaüstü",
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    # If we can't find a desktop folder, fall back to an app-local output directory.
    return Path.cwd() / "output"


def _qr_payload_for_saved_png(cfg: dict) -> str:
    """
    QR payload for the *saved* PNG (no request context).
    - If public_base_url is set, we use it for info_page mode.
    - Otherwise we default to local http://127.0.0.1:8000.
    """
    mode = (cfg.get("qr_mode") or "info_page").strip()
    if mode == "target_url":
        target = (cfg.get("target_url") or "").strip()
        if not target:
            # fall back to local info page
            base = (cfg.get("public_base_url") or "").strip() or "http://127.0.0.1:8000"
            return _with_query(base.rstrip("/") + "/info", {"rid": RUN_ID})
        if cfg.get("append_run_id_to_target_url"):
            return _with_query(target, {"rid": RUN_ID})
        return target

    base = (cfg.get("public_base_url") or "").strip() or "http://127.0.0.1:8000"
    return _with_query(base.rstrip("/") + "/info", {"rid": RUN_ID})


def save_qr_png_to_desktop(cfg: dict) -> Path:
    if qrcode is None:
        raise RuntimeError(
            "QR üretimi için paket eksik: 'qrcode'. "
            "Kurulum: pip install -r requirements.txt"
        )
    desktop = _guess_desktop_dir()
    filename = (cfg.get("qr_output_filename") or "qr.png").strip() or "qr.png"
    out_path = desktop / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = _qr_payload_for_saved_png(cfg)
    qr = qrcode.QRCode(  # type: ignore[union-attr]
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # type: ignore[union-attr]
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path, format="PNG")
    return out_path


def _maybe_save_once(cfg: dict) -> None:
    global _SAVED_ONCE, _LAST_SAVED_PATH, _LAST_SAVE_ERROR
    if _SAVED_ONCE:
        return
    if not cfg.get("qr_save_to_desktop", True):
        _SAVED_ONCE = True
        _LAST_SAVED_PATH = None
        _LAST_SAVE_ERROR = None
        return
    try:
        out = save_qr_png_to_desktop(cfg)
        _SAVED_ONCE = True
        _LAST_SAVED_PATH = str(out)
        _LAST_SAVE_ERROR = None
    except Exception as e:
        _SAVED_ONCE = True
        _LAST_SAVED_PATH = None
        _LAST_SAVE_ERROR = repr(e)


@app.get("/")
def index():
    cfg = load_config()
    _maybe_save_once(cfg)
    payload = _qr_payload_url(cfg)
    return render_template(
        "index.html",
        cfg=cfg,
        payload=payload,
        run_id=RUN_ID,
        saved_path=_LAST_SAVED_PATH,
        save_error=_LAST_SAVE_ERROR,
    )


@app.get("/info")
def info():
    cfg = load_config()
    return render_template(
        "info.html",
        title=cfg.get("info_title") or "Bilgiler",
        body=cfg.get("info_body") or "",
        target_url=(cfg.get("target_url") or "").strip(),
    )


@app.get("/qr.png")
def qr_png():
    if qrcode is None:
        return (
            "QR üretimi için 'qrcode' paketi kurulu değil.\n"
            "Kurulum:\n"
            "  pip install -r requirements.txt\n",
            500,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
    cfg = load_config()
    payload = _qr_payload_url(cfg)

    qr = qrcode.QRCode(  # type: ignore[union-attr]
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # type: ignore[union-attr]
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/png")


def _require_admin(cfg: dict) -> bool:
    token = (request.args.get("token") or "").strip()
    return bool(token) and token == (cfg.get("admin_token") or "")


@app.get("/admin")
def admin_get():
    cfg = load_config()
    if not _require_admin(cfg):
        return (
            "Yetkisiz. /admin?token=... şeklinde admin_token ile girin. "
            "Token, config.json içinde: admin_token",
            401,
        )

    return render_template("admin.html", cfg=cfg, token=cfg.get("admin_token"))


@app.post("/admin")
def admin_post():
    cfg = load_config()
    if not _require_admin(cfg):
        return ("Yetkisiz.", 401)

    cfg["qr_mode"] = request.form.get("qr_mode", cfg.get("qr_mode", "info_page"))
    cfg["target_url"] = request.form.get("target_url", cfg.get("target_url", "")).strip()
    cfg["append_run_id_to_target_url"] = bool(request.form.get("append_run_id_to_target_url"))
    cfg["info_title"] = request.form.get("info_title", cfg.get("info_title", "Bilgiler"))
    cfg["info_body"] = request.form.get("info_body", cfg.get("info_body", ""))

    save_config(cfg)
    return redirect(url_for("admin_get", token=cfg.get("admin_token")))


if __name__ == "__main__":
    cfg = load_config()
    print("RUN_ID:", RUN_ID)
    _maybe_save_once(cfg)
    if _LAST_SAVED_PATH:
        print("QR PNG kaydedildi:", _LAST_SAVED_PATH)
        print("QR içeriği:", _qr_payload_for_saved_png(cfg))
    elif _LAST_SAVE_ERROR:
        print("QR PNG kaydedilemedi:", _LAST_SAVE_ERROR)
    print("Admin sayfası:")
    print(f"  http://127.0.0.1:8000/admin?token={cfg.get('admin_token')}")
    debug = os.getenv("FLASK_DEBUG", "").strip() == "1"
    app.run(host="127.0.0.1", port=8000, debug=debug)


