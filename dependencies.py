# dependencies.py
import secrets
import os
import logging
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from models import async_session_maker

security = HTTPBasic()

def check_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Перевіряє облікові дані адміністратора зі змінних оточення."""
    
    env_user = os.environ.get("ADMIN_USER", "admin")
    env_pass = os.environ.get("ADMIN_PASS") 
    
    if not env_pass:
        logging.error("КРИТИЧНА ПОМИЛКА: ADMIN_PASS не встановлено у змінних оточення!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Система не налаштована (відсутній пароль адміністратора)",
        )

    is_user_ok = secrets.compare_digest(credentials.username, env_user)
    is_pass_ok = secrets.compare_digest(credentials.password, env_pass)
    
    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний логін або пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

async def get_db_session() -> Generator[AsyncSession, None, None]:
    """Створює та надає сесію бази даних для ендпоінта."""
    async with async_session_maker() as session:
        yield session