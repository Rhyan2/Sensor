import os
from datetime import datetime, timedelta
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from fastapi import APIRouter, Depends, Request, Form, HTTPException, WebSocket, Request,Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import UserCreate, PatientCreate, ECGData, User, Patient, ECG, UserPatient
from utils import hash_password, verify_password, get_current_user, send_email, get_user_by_patient_id, save_ecg_to_db
from websocket import manager
from typing import Optional
from pydantic import EmailStr,ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address
import uuid
import json
import asyncio
from fastapi.websockets import WebSocketDisconnect
from starlette.websockets import WebSocketState
from fastapi.encoders import jsonable_encoder
import logging


router = APIRouter()
templates = Jinja2Templates(directory="templates")# template setup
logger = logging.getLogger(__name__)
# Initialize route-specific limiter
limiter = Limiter(key_func=get_remote_address)
## Templary store tokens for password reset
temporary_reset_tokens = {}
 
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    error = request.query_params.get("error")
    return templates.TemplateResponse( "home.html", {"request": request, "error": error})

@router.get("/signup", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def signup_form(request: Request):
    return templates.TemplateResponse( "signup.html", {"request": request})

@router.post("/signup", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def signup(request: Request, user: UserCreate = Depends(UserCreate.as_form),db:Session=Depends(get_db)):
    db_user=db.query(User).filter(User.id==user.email).first()
    if db_user:
        return templates.TemplateResponse(
             "signup.html", {"request": request, "error": "Email already registered"}
        )

    # Validate password explicitly
    if not UserCreate.validate_password(user.password):
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error": "Password must be at least 7 characters long and include uppercase, lowercase, digits, and special characters.",
            },
        )

    hashed_password=await hash_password(user.password)
    db_user=User(name=user.name,idnumber=user.idnumber,email=user.email,password=hashed_password)
        
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return templates.TemplateResponse( "home.html", {
        "request": request, 
        "message": "Successfully signed up" })
     

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    email: EmailStr = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # Query the user by email
    user = db.query(User).filter(User.email == email).first()

    # Check if user exists and verify password
    if not user or not await verify_password(password, user.password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid email or password"}
        )

    # Store user info in session
    request.session["user"] = email
    return RedirectResponse("/dashboard", status_code=302)



@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

@router.get("/dashboard", response_class=HTMLResponse)
@limiter.limit("50/minute")
async def dashboard(
    request: Request,
    query: Optional[str] = Query(None),  # Accept search query from URL
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)

    # If a search query is provided, filter patients by name or ID
    if query:
        patients = db.query(Patient).join(UserPatient).filter(
            (Patient.name.ilike(f"%{query}%")) | (Patient.id == query), 
            UserPatient.user_id == current_user.id
        ).all()
    else:
        # Otherwise, fetch all patients associated with the current user
        patients = db.query(Patient).join(UserPatient).filter(
            UserPatient.user_id == current_user.id
        ).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": current_user, "patients": patients, "query": query},
    )



@router.get("/patient/{patient_id}", response_class=HTMLResponse)
@limiter.limit("50/minute")
async def patient_detail(request: Request, patient_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user:
         return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
    
    # Query the patient from the database
    patient = db.query(Patient).join(UserPatient).filter(
        Patient.id == patient_id,
        UserPatient.user_id == current_user.id
    ).first()
    
    # If no patient is found, raise a 404 error
    if not patient:
        return RedirectResponse("/dashboard?error=Patient%20not%20found", status_code=302)
    
    # Return the patient details in the template response
    return templates.TemplateResponse("patient_detail.html", {"request": request, "patient": patient})
@router.get("/add-patient", response_class=HTMLResponse)
async def show_add_patient_form(request: Request, current_user: dict = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
    return templates.TemplateResponse( "add_patient.html", {"request": request})

@router.post("/add-patient", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def add_patient(
    request:Request,
    patient: PatientCreate = Depends(PatientCreate.as_form),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)

    try:
        # Attempt to create a new patient
        new_patient = Patient(**patient.dict())
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)

        # Associate the patient with the current user
        user_patient = UserPatient(user_id=current_user.id, patient_id=new_patient.id)
        db.add(user_patient)
        db.commit()

        return RedirectResponse("/dashboard", status_code=302)

    except ValidationError as e:
        # Handle validation errors
        error_messages = e.errors()
        error_detail = ", ".join([f"{err['loc'][0]}: {err['msg']}" for err in error_messages])
        logger.error(f"Validation Error: {error_detail}")  # Log the error
        return templates.TemplateResponse("add_patient.html", {
            "request": request,
            "error": f"Validation Error: {error_detail}"
        })


@router.get("/patient/{patient_id}", response_class=HTMLResponse)
async def patient_detail(request: Request, patient_id: int, current_user: dict = Depends(get_current_user)):
    if not current_user:
         return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse( "patient_detail.html", {"request": request, "patient": patient})

# WEB SOCKECKT FOR ecg dta

# WEB SOCKET FOR ECG DATA
@router.websocket("/ws/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, patient_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=420)
                # for milliseconds to isoformart string
                data['timestamp'] = datetime.fromtimestamp(data['timestamp'] / 1000).isoformat()
                # for seconds to isoformart string
                #data['timestamp'] = datetime.fromisoformat(data['timestamp']).isoformat()
                 # Process ECG data
                
                ecg_data = ECGData(patient_id=patient_id, **data)
                heart_rate = ecg_data.bpm
                alarm = heart_rate < 50 or heart_rate > 100
                
                

                logger.info(f"Received ECG data: {ecg_data.dict()}")
                logger.info(f"Computed heart rate: {heart_rate}, Alarm: {alarm}")

                # Save to DB
                await save_ecg_to_db(db, ecg_data)

                # Send Email if Alarm
                if alarm:
                    user = get_user_by_patient_id(db, patient_id)
                    if user:
                        subject = "Heart Rate Alert"
                        body = (
                            f"Dear {user.name},\n\n"
                            f"Your patient with ID {patient_id} has an abnormal heart rate of {heart_rate} bpm.\n"
                            "Please take immediate action.\n\n"
                            "Best regards,\n"
                            "Healthcare Monitoring System"
                        )
                        await send_email(user.email, subject, body)

                # Broadcast to active WebSocket connections
                await manager.broadcast(json.dumps(jsonable_encoder({
                    "patient_id": patient_id,
                    
                    "ecg": ecg_data.ecg[-1],
                    "bpm": heart_rate,
                    "alarm": alarm,
                    "timestamp": ecg_data.timestamp
                })), patient_id)

            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"message": "ping"}))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for patient {patient_id}")
        #manager.disconnect(websocket, patient_id)
        #await manager.broadcast(json.dumps({"message": f"Patient {patient_id} disconnected"}), patient_id)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        # Ensure WebSocket closes properly
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1000, reason="Client closed connection")
        



## Editting the deails of the patient        
@router.get("/edit_patient/{patient_id}", response_class=HTMLResponse)
async def edit_patient_form(
    request: Request,
    patient_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
    
):
    # Ensure the user is logged in
    if not current_user:
        return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)

    # Retrieve the patient, ensuring they are associated with the current user
    patient = db.query(Patient).join(UserPatient).filter(
        Patient.id == patient_id,
        UserPatient.user_id == current_user.id
    ).first()

    # If the patient is not found or doesn't belong to the current user, raise a 404
    if not patient:
         return RedirectResponse("/dashboard?error=Patient%20not%20found", status_code=302)

    # Render the edit form with the patient's data (only if authorized)
    return templates.TemplateResponse(
        "edit_patient.html",
        {"request": request, "patient": patient}
    )

 
@router.post("/edit_patient/{patient_id}")
@limiter.limit("3/minute")
async def edit_patient(
    request: Request,
    patient_id: int,
    updated_patient: PatientCreate = Depends(PatientCreate.as_form),  # Handles form input
    current_user: dict = Depends(get_current_user),  # Get the current user from the session
    db: Session = Depends(get_db),  # Database session
):
    # Ensure the user is logged in
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Query the patient, ensuring it belongs to the current user
    patient = db.query(Patient).join(UserPatient).filter(
        Patient.id == patient_id,
        UserPatient.user_id == current_user.id
    ).first()

    # If the patient is not found or doesn't belong to the current user, raise an exception
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update the patient's details with the provided data
    patient.name = updated_patient.name
    patient.age = updated_patient.age
    patient.height = updated_patient.height
    patient.weight = updated_patient.weight

    # Commit the changes to the database
    db.commit()
    db.refresh(patient)  # Refresh to get the updated state

    # Redirect to the dashboard with a success message
    return RedirectResponse("/dashboard?success=Patient%20updated%20successfully", status_code=302)

## Deleting of a patienttt.
from fastapi.encoders import jsonable_encoder

@router.get("/delete_patient/{patient_id}", response_class=HTMLResponse)
async def delete_patient_confirm(request: Request, patient_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user:
        return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)

    # Query the patient to be deleted
    patient = db.query(Patient).join(UserPatient).filter(
        Patient.id == patient_id,
        UserPatient.user_id == current_user.id
    ).first()
    if not patient:
        return RedirectResponse("/dashboard?error=Patient%20not%20found", status_code=302)

        

    # Render confirmation page
    return templates.TemplateResponse( "delete_patient.html", {"request": request, "patient": jsonable_encoder(patient)})


@router.post("/delete_patient/{patient_id}", response_class=HTMLResponse)
@limiter.limit("1/minute")
async def delete_patient(
    request: Request,
    patient_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/?error=Please%20Login%20or%20Register", status_code=302)

    # Query the patient to be deleted
    patient = db.query(Patient).join(UserPatient).filter(
        Patient.id == patient_id,
        UserPatient.user_id == current_user.id
    ).first()
    
    if not patient:
        return RedirectResponse("/dashboard?error=Patient%20not%20found", status_code=302)


    # Delete associated ECG data
    db.query(ECG).filter(ECG.patient_id == patient.id).delete()  # Delete all ECG records for this patient

    # Delete the patient and associated UserPatient relation
    db.query(UserPatient).filter(UserPatient.patient_id == patient_id).delete()
    
    db.delete(patient)
    db.commit()

    # Redirect back to the dashboard
    return RedirectResponse( "/dashboard", status_code=302)

## Adding a forgot password link
@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    logger.debug("GET /forgot-password route accessed")
    return templates.TemplateResponse( "forgot_password.html", {"request": request})

@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    logger.info(f"POST /forgot-password route accessed for email: {email}")
    
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            
            return templates.TemplateResponse("forgot_password.html", {"request": request, "error": "Email not found."})
        # Generate a reset token
        reset_token = str(uuid.uuid4())
        temporary_reset_tokens[reset_token] = {
            "email": email,
            "expires": datetime.utcnow() + timedelta(hours=1)  # Token valid for 1 hour
        }

        # Send email with the reset link
        reset_link = f"http://localhost:8000/reset-password?token={reset_token}"
        subject = "Forgot Password"
        body = f"Password reset Request, Click here to reset your password: {reset_link}"
        try:
            await send_email(user.email, subject, body) 
        except Exception as e: 
            return templates.TemplateResponse("forgot_password.html", {"request": request, "error": f"Failed to send email: {str(e)}"})

        return templates.TemplateResponse("forgot_password.html", {"request": request, "message": "Reset link sent!"})
    
    except Exception as e:
        return templates.TemplateResponse( "forgot_password.html", {"request": request, "error": "An unexpected error occurred."})
## resetting password logic
@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    if token not in temporary_reset_tokens:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")
    
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password(request: Request, token: str = Form(...), new_password: str = Form(...)):
    if token not in temporary_reset_tokens:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    # Check if the token has expired
    token_info = temporary_reset_tokens[token]
    if datetime.utcnow() > token_info["expires"]:
        del temporary_reset_tokens[token]  # Remove expired token
        raise HTTPException(status_code=400, detail="Token has expired.")

    # Update user's password (assuming you have hash_password function)
    email = token_info["email"]
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        hashed_password = await hash_password(new_password)  # Use your hashing function here
        user.password = hashed_password
        db.commit()

        # Clean up the used token
        del temporary_reset_tokens[token]

        return RedirectResponse("/", status_code=302)

    raise HTTPException(status_code=404, detail="User not found.")


logger = logging.getLogger(__name__)

@router.get("/features", response_class=HTMLResponse)
async def features_page(request: Request):
    return templates.TemplateResponse( "features.html", {"request": request})

@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@router.post("/submit-contact", response_class=HTMLResponse)
async def submit_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
):
    # You can handle the contact form submission logic here, such as saving to the database
    # or sending an email.
    return templates.TemplateResponse(
        "contact.html",
        {
            "request": request,
            "message": "Thank you for reaching out! We'll get back to you shortly.",
        },
    )
@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse( "about.html", {"request": request})
