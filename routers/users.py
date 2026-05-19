from fastapi import APIRouter, HTTPException
from models import UserDetails, TokenResponse
from utils.connect_db import get_connection
from utils.jwt_handler import create_token, verify_token

router = APIRouter(prefix="/api/v1/user", tags=["user"])

@router.post('/login', response_model=TokenResponse)
async def login(user:UserDetails):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * from users WHERE email = ?',(user.email))
    dbuser = cursor.fetchone()

    conn.close()

    if not dbuser:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    # Example password check
    if dbuser["password"] != user.password:
        raise HTTPException(
            status_code=401,
            detail="Wrong password"
        )

    token = create_token(dbuser["id"])

    return {
        "access_token": token,
    }

@router.post("/signup")
async def signup(user: UserDetails):

    conn = get_connection()
    cursor = conn.cursor()

    # Check existing user
    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (user.email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()

        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    
    

    # Insert user
    cursor.execute("""
        INSERT INTO users (
            email,
            password
        )
        VALUES (?, ?)
    """, (
        user.email,
        user.password
    ))

    conn.commit()

    user_id = cursor.lastrowid

    conn.close()

    return {
        "message": "User created successfully",
        "user_id": user_id,
        "email": user.email
    }