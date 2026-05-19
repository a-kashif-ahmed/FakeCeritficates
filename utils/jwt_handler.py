from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta

SECRET_KEY = "&$AJMK)*#@"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

def create_token(user_id:str):
    expi = datetime.now + timedelta(days=1)
    payload = {
        "uid" : str(user_id),
        "exp" : expi
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm= ALGORITHM)
    return token

def verify_token(token : str = Depends(oauth2_scheme) ):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id = payload.get("uid")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return str(user_id)

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail= "Invalid Token"
        )
