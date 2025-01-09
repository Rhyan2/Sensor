import re
import datetime
from fastapi import Form
from pydantic import BaseModel, EmailStr,Field,conint,validator
from typing import List
from sqlalchemy import Column, String, Integer, Float, ForeignKey,DateTime
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.dialects.postgresql import JSON  # JSON is fine for both PostgreSQL and MySQL with newer versions

class UserCreate(BaseModel):
    name: str
    idnumber: str
    email: EmailStr
    password: str

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        idnumber: str = Form(...),
        email: EmailStr = Form(...),
        password: str = Form(...),
    ):
        return cls(name=name, idnumber=idnumber, email=email, password=password)
    
    @staticmethod
    def validate_password(password: str) -> bool:
        if len(password) < 7:
            return False
        if not re.search(r'[A-Z]', password):  # Check for uppercase letter
            return False
        if not re.search(r'[a-z]', password):  # Check for lowercase letter
            return False
        if not re.search(r'\d', password):  # Check for digit
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  # Check for special character
            return False
        return True

class PatientCreate(BaseModel):
    name: str
    age: conint(gt=0)
    id: int
    height: conint(gt=0)
    weight: conint(gt=0)

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        age: int = Form(...),
        id: int = Form(...),
        height: int = Form(...),
        weight: int = Form(...),
    ):
        return cls(name=name, age=age, id=id, height=height, weight=weight)
    
class ECGData(BaseModel):
    patient_id: int
    timestamp:str
    ecg: List[float]
    bpm: float
    
    @validator("timestamp", pre=True)
    def parse_timestamp(cls, value):
        if isinstance(value, str):
            return value  # Return the ISO format string as is
        elif isinstance(value, datetime.datetime):
            return value.isoformat()  # Convert datetime to ISO format string
        raise ValueError("Invalid timestamp format")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # Updated
    name = Column(String(100))
    idnumber = Column(String(50))
    email = Column(String(100), unique=True, index=True)
    password = Column(String(100))
    patients = relationship("Patient", secondary="user_patient", back_populates="users")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # Updated
    name = Column(String(100))
    age = Column(Integer,nullable=False)
    height = Column(Integer,nullable=False)
    weight = Column(Integer,nullable=False)
    users = relationship("User", secondary="user_patient", back_populates="patients")
    ecg_data = relationship("ECG", back_populates="patient")

class ECG(Base):
    __tablename__ = "ecg_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # Updated
    patient_id = Column(String(36), ForeignKey("patients.id",ondelete="CASCADE",))  # Updated
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    ecg = Column(JSON)  # Store ECG data as JSON
    bpm = Column(Float)
    patient = relationship("Patient", back_populates="ecg_data")
    
class UserPatient(Base):
    __tablename__ = "user_patient"
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)  # Updated
    patient_id = Column(String(36), ForeignKey("patients.id"), primary_key=True)  # Updated
