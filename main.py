from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import engine, Base
from utils import custom_rate_limit_handler
from routes import router
import os
import logging

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "a-strong-default-key"))
# creating all tables
Base.metadata.create_all(bind=engine)
## limiting th requests to avoid attacks
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

logging.basicConfig(level=logging.INFO)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

























# from fastapi import FastAPI, Request, Form, Depends, WebSocket, HTTPException
# from fastapi.responses import HTMLResponse, RedirectResponse
# from fastapi.templating import Jinja2Templates
# # websocket security
# from fastapi.security import APIKeyHeader
# from passlib.context import CryptContext
# from starlette.middleware.sessions import SessionMiddleware
# from fastapi.websockets import WebSocketDisconnect
# ## limiting the requests to prevent attacks
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded
# ## for emailing
# from pydantic import EmailStr
# from typing import Optional
# from models import UserCreate, PatientCreate,ECGData, User,Patient,ECG,UserPatient
# from dotenv import load_dotenv
# import json
# import os
# import models
# import asyncio
# import smtplib
# from email.message import EmailMessage
# from database import get_db,engine,Base
# from sqlalchemy.orm import Session
# import logging


# app = FastAPI()

# # Add Session Middleware
# app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "a-strong-default-key"))

# # Password hashing context
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# # Simulated user and patient databases


# # Templates setup
# templates = Jinja2Templates(directory="templates")

# ## setting up the logger to properly inspect the code
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# # Utility Functions
# async def hash_password(password: str) -> str:
#     return pwd_context.hash(password)

# async def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)

# async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
#     email = request.session.get("user")
#     if not email:
#         return None
#     return db.query(User).filter(User.email == email).first()

# ## create tables.
# Base.metadata.create_all(bind=engine)
# #loading the files in the  env fie
# load_dotenv()
# ## Logic to send a message
# async def send_email(to_email: str, subject: str, body: str):
#     smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
#     smtp_port = int(os.getenv("SMTP_PORT", 587))
#     smtp_user = os.getenv("SMTP_USER", "default-email@example.com")
#     smtp_password = os.getenv("SMTP_PASSWORD", "default-password")

#     # Email sending logic
#     message = EmailMessage()
#     message["From"] = smtp_user
#     message["To"] = to_email
#     message["Subject"] = subject
#     message.set_content(body)

#     try:
#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             server.starttls()
#             server.login(smtp_user, smtp_password)
#             server.send_message(message)
#         logger.info(f"Email sent to {to_email}")
#     except Exception as e:
#         logger.error(f"Failed to send email to {to_email}. Error: {str(e)}")  
        
 
#  # Intializing the rate timer.
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

 
# #getting the doctor fot the specific doctor
# def get_user_by_patient_id(db: Session, patient_id: int):
#     return db.query(User).select_from(User).join(UserPatient).join(Patient).filter(Patient.id == patient_id).first()

#  ## Saving the ecg data      
# async def save_ecg_to_db(db: Session, ecg_data: ECGData):
#     db_ecg = ECG(
#         patient_id=ecg_data.patient_id,
#         ecg=json.dumps(ecg_data.ecg),
#         bpm=ecg_data.bpm
#     )
#     db.add(db_ecg)
#     db.commit()

      

# ## WEBSOCKECT CTION MAN
# class ConnectionManager:
#     def __init__(self):
#         self.active_connections: Dict[int, List[WebSocket]] = {}

#     async def connect(self, websocket: WebSocket, patient_id: int):
#         await websocket.accept()
#         if patient_id not in self.active_connections:
#             self.active_connections[patient_id] = []
#         self.active_connections[patient_id].append(websocket)

#     def disconnect(self, websocket: WebSocket, patient_id: int):
#         try:
#             self.active_connections[patient_id].remove(websocket)
#             if not self.active_connections[patient_id]:
#                 del self.active_connections[patient_id]
#         except ValueError:
#             logger.warning(f"Attempted to remove non-existent WebSocket for patient {patient_id}")

#     async def broadcast(self, message: str, patient_id: int):
#         if patient_id in self.active_connections:
#             to_remove = []
#             for connection in self.active_connections[patient_id]:
#                 try:
#                     await connection.send_text(message)
#                 except Exception as e:
#                     logger.error(f"Failed to send message to WebSocket: {e}")
#                     to_remove.append(connection)
            
#             # Clean up any closed connections
#             for conn in to_remove:
#                 self.disconnect(conn, patient_id)

# manager = ConnectionManager()
# # Routes
# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#     error = request.query_params.get("error")
#     return templates.TemplateResponse("home.html", {"request": request, "error": error})

# @app.get("/signup", response_class=HTMLResponse)
# async def signup_form(request: Request):
#     return templates.TemplateResponse("signup.html", {"request": request})

# @app.post("/signup", response_class=HTMLResponse)
# @limiter.limit("5/minute")
# async def signup(request: Request, user: UserCreate = Depends(UserCreate.as_form),db:Session=Depends(get_db)):
#     db_user=db.query(User).filter(User.id==user.email).first()
#     if db_user:
#         return templates.TemplateResponse(
#             "signup.html", {"request": request, "error": "Email already registered"}
#         )

#     # Validate password explicitly
#     if not UserCreate.validate_password(user.password):
#         return templates.TemplateResponse(
#             "signup.html",
#             {
#                 "request": request,
#                 "error": "Password must be at least 7 characters long and include uppercase, lowercase, digits, and special characters.",
#             },
#         )

#     hashed_password=await hash_password(user.password)
#     db_user=User(name=user.name,idnumber=user.idnumber,email=user.email,password=hashed_password)
        
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return RedirectResponse("/", status_code=302)

# @app.get("/login", response_class=HTMLResponse)
# async def login_form(request: Request):
#     return templates.TemplateResponse("login.html", {"request": request})

# @app.post("/login", response_class=HTMLResponse)
# @limiter.limit("5/minute")
# async def login(
#     request: Request,
#     email: EmailStr = Form(...),
#     password: str = Form(...),
#     db: Session = Depends(get_db),
# ):
#     # Query the user by email
#     user = db.query(User).filter(User.email == email).first()

#     # Check if user exists and verify password
#     if not user or not await verify_password(password, user.password):
#         return templates.TemplateResponse(
#             "login.html", {"request": request, "error": "Invalid email or password"}
#         )

#     # Store user info in session
#     request.session["user"] = email
#     return RedirectResponse("/dashboard", status_code=302)

# @app.get("/welcome", response_class=HTMLResponse)
# async def welcome(request: Request):
#     username = request.session.get("user")
#     if not username:
#         return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)

#     return templates.TemplateResponse("welcome.html", {"request": request, "user": username})

# @app.get("/logout")
# async def logout(request: Request):
#     request.session.clear()
#     return RedirectResponse("/", status_code=302)

# @app.get("/dashboard", response_class=HTMLResponse)
# async def dashboard(request: Request, current_user: dict = Depends(get_current_user),db: Session = Depends(get_db)):
#     if not current_user:
#         return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
#     patients = db.query(Patient).all()
#     return templates.TemplateResponse(
#         "dashboard.html", {"request": request, "user": current_user, "patients": patients}
#     )



# @app.get("/patient/{patient_id}", response_class=HTMLResponse)
# async def patient_detail(request: Request, patient_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
#     if not current_user:
#          return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
    
#     # Query the patient from the database
#     patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
#     # If no patient is found, raise a 404 error
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")
    
#     # Return the patient details in the template response
#     return templates.TemplateResponse("patient_detail.html", {"request": request, "patient": patient})

# @app.get("/add-patient", response_class=HTMLResponse)
# async def show_add_patient_form(request: Request, current_user: dict = Depends(get_current_user)):
#     if not current_user:
#          return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
#     return templates.TemplateResponse("add_patient.html", {"request": request})

# @app.post("/add-patient", response_class=HTMLResponse)
# async def add_patient(patient: PatientCreate = Depends(PatientCreate.as_form), current_user: dict = Depends(get_current_user),db: Session = Depends(get_db)):
#     if not current_user:
#          return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
#     new_patient = Patient(**patient.dict())
#     db.add(new_patient)
#     db.commit()
#     db.refresh(new_patient)
    
#     ##Associate the patient with the current user
#     user_patient = UserPatient(user_id=current_user.id, patient_id=new_patient.id)
#     db.add(user_patient)
#     db.commit()
#     return RedirectResponse("/dashboard", status_code=302)

# @app.get("/patient/{patient_id}", response_class=HTMLResponse)
# async def patient_detail(request: Request, patient_id: int, current_user: dict = Depends(get_current_user)):
#     if not current_user:
#          return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
#     patient = db.query(Patient).filter(Patient.id == patient_id).first()
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")
#     return templates.TemplateResponse("patient_detail.html", {"request": request, "patient": patient})

# # WEB SOCKECKT FOR ecg dta

# # WEB SOCKET FOR ECG DATA
# @app.websocket("/ws/{patient_id}")
# async def websocket_endpoint(websocket: WebSocket, patient_id: int, db: Session = Depends(get_db)):
#     await manager.connect(websocket, patient_id)
#     try:
#         while True:
#             try:
#                 data = await asyncio.wait_for(websocket.receive_json(), timeout=60)

#                 # Process ECG data
#                 ecg_data = ECGData(patient_id=patient_id, **data)
#                 heart_rate = ecg_data.bpm
#                 alarm = heart_rate < 60 or heart_rate > 100

#                 logger.info(f"Received ECG data: {ecg_data.dict()}")
#                 logger.info(f"Computed heart rate: {heart_rate}, Alarm: {alarm}")

#                 # Save to DB
#                 await save_ecg_to_db(db, ecg_data)

#                 # Send Email if Alarm
#                 if alarm:
#                     user = get_user_by_patient_id(db, patient_id)
#                     if user:
#                         subject = "Heart Rate Alert"
#                         body = (
#                             f"Dear {user.name},\n\n"
#                             f"Your patient with ID {patient_id} has an abnormal heart rate of {heart_rate} bpm.\n"
#                             "Please take immediate action.\n\n"
#                             "Best regards,\n"
#                             "Healthcare Monitoring System"
#                         )
#                         await send_email(user.email, subject, body)

#                 # Broadcast to active WebSocket connections
#                 await manager.broadcast(json.dumps({
#                     "patient_id": patient_id,
#                     "ecg": ecg_data.ecg[-1],
#                     "bpm": heart_rate,
#                     "alarm": alarm
#                 }), patient_id)

#             except asyncio.TimeoutError:
#                 await websocket.send_text(json.dumps({"message": "ping"}))

#     except WebSocketDisconnect:
#         logger.info(f"WebSocket disconnected for patient {patient_id}")
#         manager.disconnect(websocket, patient_id)
#         await manager.broadcast(json.dumps({"message": f"Patient {patient_id} disconnected"}), patient_id)

#     except Exception as e:
#         logger.error(f"Unexpected error: {e}")

#     finally:
#         # Ensure WebSocket closes properly
#         if not websocket.client_state.closed:
#             await websocket.close()

# # Other routes (signup, login, dashboard, etc.) should be updated to use database operations instead of in-memory storage


# ## Editting the deails of the patient        
# @app.get("/edit_patient/{patient_id}",response_class=HTMLResponse)
# async def edit_patient_form(request: Request, patient_id:int,current_user:dict=Depends(get_current_user),db: Session = Depends(get_db)):
#     if not current_user:
#         return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
#     patient = db.query(Patient).filter(Patient.id == patient_id).first()
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")
#     return templates.TemplateResponse("edit_patient.html", {"request": request, "patient": patient})
 
# @app.post("/edit_patient/{patient_id}")
# async def edit_patient(
#     patient_id: int,
#     updated_patient: PatientCreate = Depends(PatientCreate.as_form),
#     current_user: dict = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     if not current_user:
#         raise HTTPException(status_code=401, detail="Unauthorized")
#     patient = db.query(Patient).filter(Patient.id == patient_id).first()
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")
#     patient.name = updated_patient.name
#     patient.age = updated_patient.age
#     patient.height = updated_patient.height
#     patient.weight = updated_patient.weight
#     db.commit()
#     return RedirectResponse("/dashboard", status_code=302)

# ## Deleting of a patienttt.
# from fastapi.encoders import jsonable_encoder

# @app.get("/delete_patient/{patient_id}", response_class=HTMLResponse)
# async def delete_patient_confirm(request: Request, patient_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
#     if not current_user:
#         return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)

#     # Query the patient to be deleted
#     patient = db.query(Patient).filter(Patient.id == patient_id).first()
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Render confirmation page
#     return templates.TemplateResponse("delete_patient.html", {"request": request, "patient": jsonable_encoder(patient)})


# @app.post("/delete_patient/{patient_id}", response_class=HTMLResponse)
# async def delete_patient(
#     request: Request, patient_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
# ):
#     if not current_user:
#         return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)

#     # Query the patient to be deleted
#     patient = db.query(Patient).filter(Patient.id == patient_id).first()
#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Delete the patient and associated UserPatient relation
#     db.query(UserPatient).filter(UserPatient.patient_id == patient_id).delete()
#     db.delete(patient)
#     db.commit()

#     # Redirect back to the dashboard
#     return RedirectResponse("/dashboard", status_code=302)

# logger = logging.getLogger(__name__)

