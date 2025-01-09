from passlib.context import CryptContext
from fastapi import Request,Depends
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from models import User
import os
import datetime
import smtplib
import json
from email.message import EmailMessage
import logging
from dotenv import load_dotenv
from models import User,ECGData,ECG,UserPatient,Patient,User
from database import get_db
from typing import Optional
from datetime import datetime





# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


## setting up the logger to properly inspect the code
#logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Utility Functions
async def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    email = request.session.get("user")
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()

## create tables.
#Base.metadata.create_all(bind=engine)
#loading the files in the  env fie
load_dotenv()
## Logic to send a message
async def send_email(to_email: str, subject: str, body: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "default-email@example.com")
    smtp_password = os.getenv("SMTP_PASSWORD", "default-password")

    # Email sending logic
    message = EmailMessage()
    message["From"] = smtp_user
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}. Error: {str(e)}")  
        
 
 

 
#getting the doctor fot the specific doctor
def get_user_by_patient_id(db: Session, patient_id: int):
    return db.query(User).select_from(User).join(UserPatient).join(Patient).filter(Patient.id == patient_id).first()

 ## Saving the ecg data      
async def save_ecg_to_db(db: Session, ecg_data: ECGData):
    
    db_ecg = ECG(
        patient_id=ecg_data.patient_id,
        
        ecg=json.dumps(ecg_data.ecg),
        bpm=ecg_data.bpm,
        timestamp=datetime.fromisoformat(ecg_data.timestamp)
    )
    db.add(db_ecg)
    db.commit()
    
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "You have made too many requests. Please try again later.",
            "retry_after": exc.detail
        },
        headers={"Retry-After": str(exc.detail)}
    )    