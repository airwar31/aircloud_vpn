from fastapi import FastAPI, Request, HTTPException
from session_manager import SessionManager
import json
import logging

app = FastAPI()
session_manager = SessionManager()
logger = logging.getLogger(__name__)

@app.post("/xray/auth")
async def xray_auth_webhook(request: Request):
    """Webhook для авторизации подключений Xray"""
    try:
        data = await request.json()
        
        # Извлекаем данные из запроса Xray
        xray_uuid = data.get("uuid")
        client_ip = data.get("source_ip", request.client.host)
        user_agent = request.headers.get("user-agent", "")
        
        if not xray_uuid:
            return {"allow": False, "reason": "missing_uuid"}
        
        # Проверяем лимит сессий (1 устройство)
        session_check = await session_manager.check_session_limit(
            xray_uuid=xray_uuid,
            client_ip=client_ip,
            user_agent=user_agent,
            max_sessions=1
        )
        
        if session_check["allowed"]:
            logger.info(f"Разрешено подключение для UUID {xray_uuid[:8]}... с IP {client_ip}")
            return {"allow": True}
        else:
            logger.warning(f"Отклонено подключение для UUID {xray_uuid[:8]}... с IP {client_ip}: {session_check['reason']}")
            return {
                "allow": False, 
                "reason": session_check["reason"],
                "message": "Превышен лимит устройств. Отключите VPN на другом устройстве."
            }
            
    except Exception as e:
        logger.error(f"Ошибка в webhook авторизации: {e}")
        return {"allow": True}  # Разрешаем в случае ошибки

@app.post("/xray/disconnect")
async def xray_disconnect_webhook(request: Request):
    """Webhook для отключения пользователей"""
    try:
        data = await request.json()
        xray_uuid = data.get("uuid")
        
        if xray_uuid:
            await session_manager.terminate_session(xray_uuid)
            logger.info(f"Сессия завершена для UUID {xray_uuid[:8]}...")
            
            # Проверяем, можно ли разблокировать пользователя
            unblocked = await session_manager.check_and_unblock_user(xray_uuid)
            if unblocked:
                logger.info(f"Пользователь с UUID {xray_uuid[:8]}... разблокирован")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Ошибка в webhook отключения: {e}")
        return {"status": "error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)