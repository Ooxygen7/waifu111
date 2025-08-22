import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.config_utils import project_root
from .models import Base

# Define the database file path
DATABASE_URL = f"sqlite:///{os.path.join(project_root, 'data', 'data.db')}"

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=True  # Set to False in production
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency to get a database session.
    Ensures the session is always closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes the database and creates tables if they don't exist.
    """
    # This will create all tables defined in conv_model.py that inherit from Base
    Base.metadata.create_all(bind=engine)

# You can call init_db() when your application starts to ensure tables are created.
# For example, in your main application entry point:
#
# if __name__ == "__main__":
#     init_db()
#     # ... start your application