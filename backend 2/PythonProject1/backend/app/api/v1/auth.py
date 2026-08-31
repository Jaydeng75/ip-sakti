from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from app.core.security import create_access_token, verify_password, get_password_hash

router = APIRouter()

MOCK_USERS_DB = {
    "lawyer@example.com": {
        "id": 1,
        "email": "lawyer@example.com",
        "hashed_password": get_password_hash("password123"),
        "role": "user",
    },
    "admin@example.com": {
        "id": 2,
        "email": "admin@example.com",
        "hashed_password": get_password_hash("admin123"),
        "role": "admin",
    },
}

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = MOCK_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        data={"sub": str(user["id"]), "role": user["role"]}
    )

    return {"access_token": access_token, "token_type": "bearer"}