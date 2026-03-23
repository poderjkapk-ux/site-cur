# auth_utils.py

import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from models import Employee
from dependencies import get_db_session

# --- КОНФИГУРАЦИЯ ---
# В продакшене обязательно замените этот ключ на случайную длинную строку
# Можно сгенерировать через `openssl rand -hex 32`
SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey_change_this_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # Токен живет 12 часов (длина смены)

# Настройка контекста для хеширования паролей (используем bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Схема авторизации (формально нужна для Swagger UI, но мы используем куки)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="staff/login")

# --- ФУНКЦИИ ХЕШИРОВАНИЯ ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, совпадает ли введенный пароль с хешем."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Генерирует хеш из пароля."""
    return pwd_context.hash(password)

# --- ФУНКЦИИ JWT (ТОКЕНЫ) ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создает JWT токен с данными пользователя и сроком действия."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- ЗАВИСИМОСТИ (DEPENDENCIES) ---

async def get_current_staff(
    request: Request, 
    session: AsyncSession = Depends(get_db_session)
) -> Employee:
    """
    Получает текущего авторизованного сотрудника из куки 'staff_access_token'.
    Используется как Depends(get_current_staff) в защищенных роутах.
    """
    token = request.cookies.get("staff_access_token")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Необхідна авторизація",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        # Декодируем токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception

    # Ищем сотрудника в базе данных
    employee = await session.get(Employee, int(user_id))
    
    if not employee:
        raise credentials_exception
    
    return employee