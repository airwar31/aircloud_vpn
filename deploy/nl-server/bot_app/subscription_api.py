"""
Subscription API для VPN конфигов
Совместимость с V2rayN, NekoBox, Clash и другими клиентами
"""

import logging
import base64
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from datetime import datetime

from bot_app.database import Database
from bot_app.config import MigrationConfig

logger = logging.getLogger(__name__)

app = FastAPI(title="AirCloud VPN Subscription API")

# Global database instance (will be set by bot on startup)
db: Optional[Database] = None
_read_fallback_warned = False


def _use_legacy_read_path() -> bool:
    """Use local DB reads until RemnaWave read adapter is implemented."""
    global _read_fallback_warned
    if MigrationConfig.use_remnawave_reads() and not _read_fallback_warned:
        logger.warning(
            "READ_MODE=%s requested, but RemnaWave read adapter is not wired yet. "
            "Subscription API falls back to legacy DB reads.",
            MigrationConfig.READ_MODE,
        )
        _read_fallback_warned = True
    return True


def init_subscription_api(database: Database):
    """Initialize subscription API with database instance"""
    global db
    db = database
    logger.info("Subscription API initialized")


def _is_browser(request: Request) -> bool:
    """Определить, идет ли запрос из браузера по User-Agent"""
    ua = request.headers.get("User-Agent", "").lower()
    return "mozilla" in ua or "chrome" in ua or "safari" in ua or "opera" in ua


@app.get("/")
async def root():
    return {"service": "AirCloud VPN Subscription API", "version": "1.0.0"}


@app.get("/sub/{token}")
async def get_subscription(token: str, request: Request):
    """
    Если запрос из браузера — HTML страница с деталями подписки.
    Если из VPN клиента — base64-encoded VLESS конфиги.
    """
    try:
        _use_legacy_read_path()
        if not db:
            raise HTTPException(status_code=500, detail="Database not initialized")

        user = await db.get_user_by_subscription_token(token)
        if not user:
            if _is_browser(request):
                return _render_not_found()
            raise HTTPException(status_code=404, detail="Subscription not found")

        user_id = user["user_id"]
        keys = await db.get_user_keys(user_id)
        now = datetime.now().timestamp()
        active_keys = [k for k in keys if k["expires_at"] > now]

        # Браузер — показать HTML страницу
        if _is_browser(request):
            return HTMLResponse(_render_info_page(token, request, active_keys, now))

        # VPN клиент — вернуть base64
        if not active_keys:
            return PlainTextResponse(base64.b64encode(b"").decode())

        configs = [k["vless_link"] for k in active_keys if k.get("vless_link")]
        encoded = base64.b64encode("\n".join(configs).encode()).decode()
        logger.info(f"Subscription served for user {user_id}: {len(active_keys)} configs")
        return PlainTextResponse(encoded)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving subscription {token}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sub/{token}/raw", response_class=PlainTextResponse)
async def get_subscription_raw(token: str):
    """Plain text VLESS конфиги для отладки"""
    try:
        _use_legacy_read_path()
        if not db:
            raise HTTPException(status_code=500, detail="Database not initialized")

        user = await db.get_user_by_subscription_token(token)
        if not user:
            raise HTTPException(status_code=404, detail="Subscription not found")

        keys = await db.get_user_keys(user["user_id"])
        now = datetime.now().timestamp()
        active_keys = [k for k in keys if k["expires_at"] > now]
        configs = [k["vless_link"] for k in active_keys if k.get("vless_link")]
        return "\n".join(configs) if configs else "# No active subscriptions"

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving raw subscription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _render_not_found() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AirCloud VPN — Подписка не найдена</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #0f0f1a; color: #fff; min-height: 100vh;
               display: flex; align-items: center; justify-content: center; }
        .card { background: #1a1a2e; border-radius: 20px; padding: 40px;
                max-width: 440px; width: 90%; text-align: center;
                border: 1px solid rgba(255,255,255,0.08); }
        .icon { font-size: 56px; margin-bottom: 16px; }
        h1 { font-size: 22px; color: #f44336; margin-bottom: 12px; }
        p { color: #888; font-size: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">❌</div>
        <h1>Подписка не найдена</h1>
        <p>Неверная или устаревшая ссылка на подписку.<br>Получите новую ссылку в боте.</p>
    </div>
</body>
</html>"""
    return HTMLResponse(html, status_code=404)


def _render_info_page(token: str, request: Request, active_keys: list, now: float) -> str:
    sub_url = f"{request.url.scheme}://{request.url.netloc}/sub/{token}"

    # Формируем карточки подписок
    if not active_keys:
        keys_html = """
        <div class="empty">
            <div class="empty-icon">📭</div>
            <p>Нет активных подписок</p>
            <p class="hint">Купите VPN подписку в боте</p>
        </div>"""
    else:
        keys_html = ""
        for key in active_keys:
            tunnel_type = key.get("tunnel_type", "unknown")
            expires_ts = key["expires_at"]
            days_left = int((expires_ts - now) / 86400)
            expires_str = datetime.fromtimestamp(expires_ts).strftime("%d.%m.%Y")

            if tunnel_type == "single":
                icon = "🇳🇱"
                name = "Нидерланды (прямое)"
                desc = "Прямое подключение · VLESS + TLS"
                color = "#4CAF50"
            else:
                icon = "🛡️"
                name = "Обход глушилок"
                desc = "Двойной туннель · VLESS + Reality"
                color = "#2196F3"

            # Цвет дней до истечения
            if days_left <= 7:
                days_color = "#f44336"
            elif days_left <= 30:
                days_color = "#FF9800"
            else:
                days_color = "#4CAF50"

            keys_html += f"""
        <div class="sub-card" style="border-left-color: {color}">
            <div class="sub-header">
                <span class="sub-icon">{icon}</span>
                <div>
                    <div class="sub-name">{name}</div>
                    <div class="sub-desc">{desc}</div>
                </div>
            </div>
            <div class="sub-footer">
                <span class="expires">📅 Истекает {expires_str}</span>
                <span class="days-left" style="color: {days_color}">⏳ {days_left} дн.</span>
            </div>
        </div>"""

    count = len(active_keys)
    status_text = f"{count} активных конфигов" if count else "Нет активных подписок"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AirCloud VPN — Подписка</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f1a;
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        .wrapper {{
            max-width: 480px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 32px 0 24px;
        }}
        .logo {{ font-size: 48px; margin-bottom: 8px; }}
        .title {{ font-size: 24px; font-weight: 700; color: #fff; }}
        .subtitle {{ color: #888; font-size: 14px; margin-top: 4px; }}

        .status-badge {{
            display: inline-block;
            background: rgba(76,175,80,0.15);
            color: #4CAF50;
            border: 1px solid rgba(76,175,80,0.3);
            border-radius: 20px;
            padding: 6px 16px;
            font-size: 13px;
            margin: 12px 0 24px;
        }}

        .section-title {{
            font-size: 13px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 10px;
        }}

        .sub-card {{
            background: #1a1a2e;
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 10px;
            border: 1px solid rgba(255,255,255,0.06);
            border-left: 4px solid #4CAF50;
        }}
        .sub-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .sub-icon {{ font-size: 28px; }}
        .sub-name {{ font-weight: 600; font-size: 15px; }}
        .sub-desc {{ font-size: 12px; color: #888; margin-top: 2px; }}
        .sub-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }}
        .expires {{ font-size: 13px; color: #aaa; }}
        .days-left {{ font-size: 13px; font-weight: 600; }}

        .url-section {{
            margin-top: 24px;
        }}
        .url-box {{
            background: #1a1a2e;
            border-radius: 12px;
            padding: 14px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .url-text {{
            font-family: monospace;
            font-size: 12px;
            color: #64b5f6;
            word-break: break-all;
            line-height: 1.5;
        }}
        .copy-btn {{
            width: 100%;
            margin-top: 10px;
            padding: 10px;
            background: rgba(100,181,246,0.1);
            color: #64b5f6;
            border: 1px solid rgba(100,181,246,0.2);
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .copy-btn:hover {{ background: rgba(100,181,246,0.2); }}
        .copy-btn.copied {{ color: #4CAF50; border-color: rgba(76,175,80,0.3); background: rgba(76,175,80,0.1); }}

        .hint-section {{
            margin-top: 20px;
            background: #1a1a2e;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.06);
        }}
        .hint-title {{ font-size: 13px; color: #aaa; margin-bottom: 10px; }}
        .hint-list {{ list-style: none; }}
        .hint-list li {{
            font-size: 13px;
            color: #888;
            padding: 3px 0;
        }}
        .hint-list li::before {{ content: "→ "; color: #555; }}

        .empty {{
            text-align: center;
            padding: 40px 20px;
            background: #1a1a2e;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.06);
        }}
        .empty-icon {{ font-size: 40px; margin-bottom: 12px; }}
        .empty p {{ color: #888; }}
        .empty .hint {{ color: #555; font-size: 13px; margin-top: 6px; }}

        .footer {{
            text-align: center;
            padding: 24px 0 8px;
            font-size: 12px;
            color: #444;
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <div class="logo">☁️</div>
            <div class="title">AirCloud VPN</div>
            <div class="subtitle">Управление подпиской</div>
            <div class="status-badge">● {status_text}</div>
        </div>

        <div class="section-title">Активные конфиги</div>
        {keys_html}

        <div class="url-section">
            <div class="section-title">Ссылка на подписку</div>
            <div class="url-box">
                <div class="url-text" id="subUrl">{sub_url}</div>
                <button class="copy-btn" onclick="copyUrl()">📋 Скопировать ссылку</button>
            </div>
        </div>

        <div class="hint-section">
            <div class="hint-title">Как использовать в VPN клиенте:</div>
            <ul class="hint-list">
                <li>V2rayN → Подписки → Добавить подписку</li>
                <li>NekoBox → Профили → Новый профиль → URL</li>
                <li>V2rayNG → Подписки → Добавить</li>
                <li>Вставьте ссылку выше и нажмите «Обновить»</li>
            </ul>
        </div>

        <div class="footer">AirCloud VPN © 2025</div>
    </div>

    <script>
        function copyUrl() {{
            const url = document.getElementById('subUrl').textContent;
            navigator.clipboard.writeText(url).then(() => {{
                const btn = document.querySelector('.copy-btn');
                btn.textContent = '✅ Скопировано!';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.textContent = '📋 Скопировать ссылку';
                    btn.classList.remove('copied');
                }}, 2000);
            }});
        }}
    </script>
</body>
</html>"""
