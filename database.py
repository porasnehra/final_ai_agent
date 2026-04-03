from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DATABASE_URL = "sqlite:///./multi_user_agent.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    credentials = relationship("UserCredentials", back_populates="user", uselist=False)

class UserCredentials(Base):
    __tablename__ = "user_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # We will store keys as plain text / JSON text for basic implementation.
    google_api_key = Column(String, nullable=True) # gemini API key
    google_token_json = Column(Text, nullable=True) # calendar refresh token
    notion_token = Column(String, nullable=True)
    notion_database_id = Column(String, nullable=True)
    todoist_api_token = Column(String, nullable=True)

    user = relationship("User", back_populates="credentials")

# Create tables
Base.metadata.create_all(bind=engine)
