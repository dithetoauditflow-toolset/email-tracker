"""
Script to create the initial admin account
Run this once before first use: python create_admin.py
"""
from data.db_manager import DatabaseManager
import getpass


def create_admin():
    """Interactive script to create admin account"""
    print("=" * 50)
    print("Email Follow-Up Audit Tool - Admin Setup")
    print("=" * 50)
    print()
    
    db = DatabaseManager()
    
    print("This will create the admin account for the system.")
    print("You only need to do this once.\n")
    
    username = input("Enter admin username: ").strip()
    
    if not username:
        print("❌ Username cannot be empty")
        return
    
    password = getpass.getpass("Enter admin password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    if password != confirm_password:
        print("❌ Passwords do not match")
        return
    
    if len(password) < 6:
        print("❌ Password must be at least 6 characters")
        return
    
    # Create admin
    success = db.create_admin(username, password)
    
    if success:
        print()
        print("=" * 50)
        print("✅ Admin account created successfully!")
        print("=" * 50)
        print(f"Username: {username}")
        print("\nYou can now run the application:")
        print("  streamlit run main.py")
        print()
    else:
        print()
        print("=" * 50)
        print("⚠️  Admin account already exists")
        print("=" * 50)
        print("If you need to reset the admin password,")
        print("delete the data/main.db file and run this script again.")
        print()


if __name__ == "__main__":
    create_admin()
