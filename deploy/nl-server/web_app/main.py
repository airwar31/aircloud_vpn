"""
AirCloud VPN Web App
Отдельный веб-сервис: Subscription API + Telegram Mini App (React SPA)
"""

import logging
import base64
import os
import uuid
import json
import hmac
import time
import hashlib
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qsl

import aiohttp
import aiosqlite
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

DB_PATH           = os.getenv("DB_PATH", "/app/db/users.db")
YOOKASSA_SHOP_ID  = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
BOT_TOKEN         = os.getenv("BOT_TOKEN", "")
MINI_APP_AUTH_REQUIRED = os.getenv("MINI_APP_AUTH_REQUIRED", "true").lower() == "true"
TELEGRAM_INITDATA_MAX_AGE = int(os.getenv("TELEGRAM_INITDATA_MAX_AGE", "86400"))
SUBSCRIPTION_BASE_URL = os.getenv("SUBSCRIPTION_BASE_URL", "").rstrip("/")
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]
if not CORS_ALLOW_ORIGINS:
    CORS_ALLOW_ORIGINS = ["*"]

PRICES = {
    "single": {"1_month": 150, "3_months": 400, "12_months": 1200},
    "double": {"1_month": 250, "3_months": 650, "12_months": 2200},
}
STARS_RATE = 0.8  # rubles -> Stars

# ── Paths ────────────────────────────────────────────────────────────────────
_HERE     = os.path.dirname(__file__)
_DIST     = os.path.join(_HERE, "static", "dist")
_INDEX    = os.path.join(_DIST, "index.html")
_ASSETS   = os.path.join(_DIST, "assets")

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="AirCloud VPN Web", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Serve Vite-built assets (/assets/*)
if os.path.isdir(_ASSETS):
    app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")


# ─── DB helpers ──────────────────────────────────────────────────────────────

async def _get_user_by_token(token: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT user_id, username FROM users WHERE subscription_token = ?", (token,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def _get_active_keys(user_id: int) -> list:
    now = datetime.now().timestamp()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT email, tunnel_type, vless_link, expires_at
               FROM vpn_subscriptions
               WHERE user_id = ?
               ORDER BY tunnel_type, expires_at DESC""",
            (user_id,),
        )
        rows = await cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            expires_ts = _parse_expires_at(d.get("expires_at"))
            if expires_ts > now:
                d["expires_at"] = expires_ts
                result.append(d)
        result.sort(key=lambda item: item.get("expires_at", 0), reverse=True)
        return result


def _parse_expires_at(val) -> float:
    """Convert expires_at from DB to Unix timestamp (seconds)."""
    if val is None:
        return 0.0

    if isinstance(val, datetime):
        return float(val.timestamp())

    try:
        ts = float(val)
        if ts > 1e12:
            ts = ts / 1000.0
        return ts
    except (ValueError, TypeError):
        pass

    try:
        text = str(val).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return float(datetime.fromisoformat(text).timestamp())
    except (ValueError, TypeError):
        pass

    try:
        return float(datetime.strptime(str(val).strip(), "%Y-%m-%d %H:%M:%S").timestamp())
    except (ValueError, TypeError):
        return 0.0

def _is_browser(request: Request) -> bool:
    ua = request.headers.get("User-Agent", "").lower()
    return any(x in ua for x in ("mozilla", "chrome", "safari", "opera"))


def _rubles_to_stars(rubles: float) -> int:
    return max(int(rubles * STARS_RATE), 1)


def _verify_telegram_init_data(init_data: str) -> dict:
    """
    Verify Telegram WebApp initData and return parsed payload.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="BOT_TOKEN is not configured")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing Telegram hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    auth_date_raw = pairs.get("auth_date")
    if auth_date_raw:
        try:
            auth_date = int(auth_date_raw)
            if TELEGRAM_INITDATA_MAX_AGE > 0 and (time.time() - auth_date) > TELEGRAM_INITDATA_MAX_AGE:
                raise HTTPException(status_code=401, detail="Telegram auth data is expired")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid auth_date")

    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="Missing Telegram user data")

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Invalid Telegram user payload")

    if not isinstance(user, dict) or "id" not in user:
        raise HTTPException(status_code=401, detail="Invalid Telegram user payload")

    pairs["user"] = user
    return pairs


def _authorize_telegram_user(request: Request, expected_user_id: Optional[int] = None) -> int:
    """Authorize Mini App request and return Telegram user ID."""
    if not MINI_APP_AUTH_REQUIRED:
        if expected_user_id is None:
            raise HTTPException(status_code=400, detail="user_id is required")
        return int(expected_user_id)

    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data header")

    payload = _verify_telegram_init_data(init_data)
    auth_user_id = int(payload["user"]["id"])

    if expected_user_id is not None and auth_user_id != int(expected_user_id):
        raise HTTPException(status_code=403, detail="Forbidden: user_id mismatch")

    return auth_user_id


async def _store_pending_order(
    user_id: int,
    amount: float,
    plan_type: str,
    tunnel_type: str,
    payment_method: str,
    payment_id: str,
):
    """Persist pending order for Mini App payments."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO orders
                (user_id, amount, currency, plan_type, tunnel_type, status, payment_method, payment_id)
                VALUES (?, ?, 'RUB', ?, ?, 'pending', ?, ?)
                """,
                (user_id, amount, plan_type, tunnel_type, payment_method, payment_id),
            )
            await db.commit()
    except Exception as e:
        # Do not fail checkout if DB write fails; activation still can work via metadata.
        logger.error(f"Failed to store pending Mini App order: {e}")


# ─── API routes ──────────────────────────────────────────────────────────────

@app.get("/api/user/{user_id}/subscription")
async def api_user_subscription(user_id: int, request: Request):
    """Subscription data for Telegram Mini App."""
    user_id = _authorize_telegram_user(request, expected_user_id=user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT subscription_token FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
        if not row:
            return {"keys": [], "subscription_url": None}
        token = row["subscription_token"]

    keys = await _get_active_keys(user_id)
    base_url = SUBSCRIPTION_BASE_URL or f"{request.url.scheme}://{request.url.netloc}"
    sub_url = f"{base_url}/sub/{token}" if token else None

    return {
        "keys": [
            {
                "tunnel_type": k["tunnel_type"],
                "expires_at": _parse_expires_at(k["expires_at"]),
                "email": k["email"],
                "vless_link": k.get("vless_link") or "",
            }
            for k in keys
        ],
        "subscription_url": sub_url,
    }


@app.post("/api/create-payment")
async def api_create_payment(request: Request):
    """Create payment from Telegram Mini App."""
    body = await request.json()
    requested_user_id = body.get("user_id")
    user_id = _authorize_telegram_user(request, expected_user_id=requested_user_id)
    tunnel_type = body.get("tunnel_type")
    duration = body.get("duration")
    method = body.get("method")

    if tunnel_type not in PRICES or duration not in PRICES.get(tunnel_type, {}):
        raise HTTPException(status_code=400, detail="Invalid plan")

    price = PRICES[tunnel_type][duration]

    if method == "stars":
        stars = _rubles_to_stars(price)
        link = await _create_stars_invoice(tunnel_type, duration, stars)
        if not link:
            raise HTTPException(status_code=500, detail="Failed to create Stars invoice")
        return {"type": "invoice", "invoice_link": link}

    if method == "yookassa":
        if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
            raise HTTPException(status_code=503, detail="YooKassa not configured")

        pid, url = await _create_yookassa_payment(user_id, price, tunnel_type, duration)
        if not pid:
            raise HTTPException(status_code=500, detail="Failed to create payment")

        await _store_pending_order(
            user_id=user_id,
            amount=price,
            plan_type=duration,
            tunnel_type=tunnel_type,
            payment_method="yookassa",
            payment_id=pid,
        )

        return {"type": "url", "url": url, "payment_id": pid}

    raise HTTPException(status_code=400, detail="Unknown payment method")


@app.get("/sub/{token}")
async def subscription(token: str, request: Request):
    """Браузер → HTML, VPN клиент → base64 VLESS"""
    user = await _get_user_by_token(token)
    if not user:
        if _is_browser(request):
            return HTMLResponse(_page_not_found(), status_code=404)
        raise HTTPException(status_code=404, detail="Subscription not found")

    keys = await _get_active_keys(user["user_id"])

    if _is_browser(request):
        return HTMLResponse(_page_subscription(token, request, keys))

    configs = [k["vless_link"] for k in keys if k.get("vless_link")]
    encoded = base64.b64encode("\n".join(configs).encode()).decode()
    return PlainTextResponse(encoded)


@app.get("/sub/{token}/raw", response_class=PlainTextResponse)
async def subscription_raw(token: str):
    user = await _get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")
    keys = await _get_active_keys(user["user_id"])
    configs = [k["vless_link"] for k in keys if k.get("vless_link")]
    return "\n".join(configs) if configs else "# No active subscriptions"


# ─── SPA fallback ─────────────────────────────────────────────────────────────

@app.get("/")
@app.get("/app")
async def spa_root():
    """React Mini App"""
    if os.path.isfile(_INDEX):
        return FileResponse(_INDEX, media_type="text/html")
    return HTMLResponse("<p>Frontend not built. Run: cd frontend && npm run build</p>", status_code=503)


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """SPA catch-all: return index.html for unknown frontend routes"""
    # Don't intercept API or subscription routes (already defined above)
    if full_path.startswith(("api/", "sub/", "assets/")):
        raise HTTPException(status_code=404)
    if os.path.isfile(_INDEX):
        return FileResponse(_INDEX, media_type="text/html")
    raise HTTPException(status_code=404)


# ─── Payment helpers ─────────────────────────────────────────────────────────

async def _create_stars_invoice(tunnel_type: str, duration: str, stars: int) -> Optional[str]:
    if not BOT_TOKEN:
        return None
    labels = {"single": "Нидерланды (прямое)", "double": "Обход глушилок (двойной)"}
    dur_labels = {"1_month": "1 месяц", "3_months": "3 месяца", "12_months": "12 месяцев"}
    payload = {
        "title": f"AirCloud VPN — {labels.get(tunnel_type, tunnel_type)}",
        "description": f"Подписка на {dur_labels.get(duration, duration)}",
        "payload": f"{tunnel_type}_{duration}",
        "currency": "XTR",
        "prices": [{"label": "VPN подписка", "amount": stars}],
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink",
                json=payload,
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"]
                logger.error(f"Telegram API error: {data}")
    except Exception as e:
        logger.error(f"Stars invoice error: {e}")
    return None


async def _create_yookassa_payment(
    user_id: int, amount: float, tunnel_type: str, duration: str
) -> tuple:
    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/"},
        "capture": True,
        "description": f"AirCloud VPN — {tunnel_type} {duration}",
        "metadata": {
            "user_id": str(user_id),
            "tunnel_type": tunnel_type,
            "duration": duration,
            "email": f"vpn_{user_id}@aircloud.local",
            "source": "mini_app",
        },
    }
    credentials = base64.b64encode(f"{YOOKASSA_SHOP_ID}:{YOOKASSA_SECRET_KEY}".encode()).decode()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.yookassa.ru/v3/payments",
                json=payload,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Idempotence-Key": str(uuid.uuid4()),
                    "Content-Type": "application/json",
                },
            ) as resp:
                data = await resp.json()
                if "id" not in data:
                    logger.error(f"YooKassa HTTP {resp.status}: {data}")
                    return None, None
                return data["id"], data["confirmation"]["confirmation_url"]
    except Exception as e:
        logger.error(f"YooKassa payment error: {e}")
        return None, None


# ─── Browser subscription page (static HTML, no React) ───────────────────────

def _page_not_found() -> str:
    return """<!DOCTYPE html>
<html lang="ru"><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>AirCloud VPN</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             background:#0f0f1a;color:#fff;min-height:100vh;
             display:flex;align-items:center;justify-content:center}
        .card{background:#1a1a2e;border-radius:20px;padding:40px;max-width:440px;
              width:90%;text-align:center;border:1px solid rgba(255,255,255,.08)}
        .icon{font-size:56px;margin-bottom:16px}
        h1{font-size:22px;color:#f44336;margin-bottom:12px}
        p{color:#888;font-size:15px;line-height:1.6}
    </style>
</head><body>
    <div class="card">
        <div class="icon">❌</div>
        <h1>Подписка не найдена</h1>
        <p>Неверная или устаревшая ссылка.<br>Получите новую в боте.</p>
    </div>
</body></html>"""


def _page_subscription(token: str, request: Request, keys: list) -> str:
    now = datetime.now().timestamp()
    sub_url = f"{request.url.scheme}://{request.url.netloc}/sub/{token}"

    if not keys:
        cards_html = """
        <div class="empty">
            <div style="font-size:40px;margin-bottom:12px">📭</div>
            <p>Нет активных подписок</p>
            <p class="hint">Купите VPN подписку в боте</p>
        </div>"""
    else:
        cards_html = ""
        for key in keys:
            t = key.get("tunnel_type", "single")
            expires_ts = _parse_expires_at(key["expires_at"])
            days_left = int((expires_ts - now) / 86400)
            expires_str = datetime.fromtimestamp(expires_ts).strftime("%d.%m.%Y")
            if t == "single":
                icon, name, desc, color = "🇳🇱", "Нидерланды", "Прямое · VLESS + TLS", "#4CAF50"
            else:
                icon, name, desc, color = "🛡️", "Обход глушилок", "Двойной · VLESS + Reality", "#2196F3"
            days_color = "#f44336" if days_left <= 7 else ("#FF9800" if days_left <= 30 else "#4CAF50")
            cards_html += f"""
        <div class="card" style="border-left-color:{color}">
            <div class="ch"><span class="ci">{icon}</span>
            <div><div class="cn">{name}</div><div class="cd">{desc}</div></div></div>
            <div class="cf">
                <span class="ce">📅 {expires_str}</span>
                <span style="color:{days_color};font-weight:600">⏳ {days_left} дн.</span>
            </div>
        </div>"""

    count = len(keys)
    badge = f"{count} конфигов" if count else "Нет подписок"

    return f"""<!DOCTYPE html>
<html lang="ru"><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>AirCloud VPN — Подписка</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             background:#0f0f1a;color:#fff;min-height:100vh;padding:20px}}
        .wrap{{max-width:480px;margin:0 auto}}
        .header{{text-align:center;padding:32px 0 24px}}
        .logo{{font-size:48px;margin-bottom:8px}}
        .title{{font-size:24px;font-weight:700}}
        .sub{{color:#888;font-size:14px;margin-top:4px}}
        .badge{{display:inline-block;background:rgba(76,175,80,.15);color:#4CAF50;
                border:1px solid rgba(76,175,80,.3);border-radius:20px;
                padding:6px 16px;font-size:13px;margin:12px 0 24px}}
        .label{{font-size:12px;color:#555;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px}}
        .card{{background:#1a1a2e;border-radius:14px;padding:16px;margin-bottom:10px;
               border:1px solid rgba(255,255,255,.06);border-left:4px solid #4CAF50}}
        .ch{{display:flex;align-items:center;gap:12px;margin-bottom:12px}}
        .ci{{font-size:28px}}
        .cn{{font-weight:600;font-size:15px}}
        .cd{{font-size:12px;color:#888;margin-top:2px}}
        .cf{{display:flex;justify-content:space-between;align-items:center;
             padding-top:10px;border-top:1px solid rgba(255,255,255,.06)}}
        .ce{{font-size:13px;color:#aaa}}
        .url-box{{background:#1a1a2e;border-radius:12px;padding:14px;
                  border:1px solid rgba(255,255,255,.08);margin-top:4px}}
        .url-text{{font-family:monospace;font-size:12px;color:#64b5f6;
                   word-break:break-all;line-height:1.5}}
        .copy-btn{{width:100%;margin-top:10px;padding:10px;background:rgba(100,181,246,.1);
                   color:#64b5f6;border:1px solid rgba(100,181,246,.2);border-radius:8px;
                   font-size:13px;cursor:pointer;transition:background .2s;font-family:inherit}}
        .copy-btn:hover{{background:rgba(100,181,246,.2)}}
        .copy-btn.ok{{color:#4CAF50;border-color:rgba(76,175,80,.3);background:rgba(76,175,80,.1)}}
        .hint-box{{background:#1a1a2e;border-radius:12px;padding:16px;
                   border:1px solid rgba(255,255,255,.06);margin-top:4px}}
        .hint-box p{{font-size:13px;color:#888;padding:3px 0}}
        .hint-box p::before{{content:"> ";color:#555}}
        .empty{{text-align:center;padding:40px 20px;background:#1a1a2e;
                border-radius:14px;border:1px solid rgba(255,255,255,.06)}}
        .empty p{{color:#888}}.hint{{color:#555;font-size:13px;margin-top:6px}}
        .section{{margin-top:20px}}
        .footer{{text-align:center;padding:24px 0 8px;font-size:12px;color:#333}}
    </style>
</head><body>
<div class="wrap">
    <div class="header">
        <div class="logo">&#9729;</div>
        <div class="title">AirCloud VPN</div>
        <div class="sub">Управление подпиской</div>
        <div class="badge">● {badge}</div>
    </div>
    <div class="label">Активные конфиги</div>
    {cards_html}
    <div class="section">
        <div class="label">Ссылка на подписку</div>
        <div class="url-box">
            <div class="url-text" id="url">{sub_url}</div>
            <button class="copy-btn" onclick="cp()">📋 Скопировать ссылку</button>
        </div>
    </div>
    <div class="section">
        <div class="label">Как добавить в клиент</div>
        <div class="hint-box">
            <p>V2rayN → Подписки → Добавить</p>
            <p>NekoBox → Профили → Новый → URL</p>
            <p>V2rayNG → Подписки → Добавить</p>
            <p>Вставьте ссылку и нажмите «Обновить»</p>
        </div>
    </div>
    <div class="footer">AirCloud VPN © 2025</div>
</div>
<script>
function cp(){{
    navigator.clipboard.writeText(document.getElementById('url').textContent).then(()=>{{
        const b=document.querySelector('.copy-btn');
        b.textContent='✅ Скопировано!';b.classList.add('ok');
        setTimeout(()=>{{b.textContent='📋 Скопировать ссылку';b.classList.remove('ok')}},2000);
    }});
}}
</script>
</body></html>"""

