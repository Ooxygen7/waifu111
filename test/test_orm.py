import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from utils.database.core import SessionLocal, engine, init_db
from utils.database.models import User

def test_orm():
    """
    Tests the basic functionality of the SQLAlchemy ORM setup.
    - Initializes the database.
    - Creates a new user.
    - Queries for the user.
    - Prints the result.
    """
    print("Initializing the database...")
    init_db()
    print("Database initialized.")

    db: Session = SessionLocal()

    try:
        # Create a new user
        test_user = User(
            uid=99999,
            first_name="Test",
            last_name="User",
            user_name="testuser",
            account_tier=1,
            balance=100.0
        )
        print(f"Attempting to add user: {test_user.user_name}")
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print("User added and committed.")

        # Query the user
        print("Querying for the test user...")
        queried_user = db.query(User).filter(User.uid == 99999).first()

        if queried_user:
            print("\n--- ORM Test Successful ---")
            print(f"Found user: {queried_user.user_name}")
            print(f"  UID: {queried_user.uid}")
            print(f"  Full Name: {queried_user.first_name} {queried_user.last_name}")
            print(f"  Balance: {queried_user.balance}")
            print("---------------------------\n")
        else:
            print("\n--- ORM Test Failed ---")
            print("Could not find the test user after adding.")
            print("-----------------------\n")

    except Exception as e:
        print(f"\n--- ORM Test Errored ---")
        print(f"An error occurred: {e}")
        print("------------------------\n")
        db.rollback()
    finally:
        # Clean up the test user
        user_to_delete = db.query(User).filter(User.uid == 99999).first()
        if user_to_delete:
            db.delete(user_to_delete)
            db.commit()
            print("Test user cleaned up.")
        db.close()
        print("Database session closed.")

if __name__ == "__main__":
    test_orm()