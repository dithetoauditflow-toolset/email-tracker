"""
Test script to verify the setup is working correctly
Run: python test_setup.py
"""
import sys
import os
from pathlib import Path

# Fix unicode encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from data.db_manager import DatabaseManager
        print("✅ Database manager imported")
        
        from auth.session_manager import init_session
        print("✅ Session manager imported")
        
        from email_sync.imap_handler import IMAPHandler
        print("✅ IMAP handler imported")
        
        from email_sync.sync_manager import EmailSyncManager
        print("✅ Sync manager imported")
        
        from utils.encryption import encrypt_email_config
        print("✅ Encryption utilities imported")
        
        from utils.date_utils import WorkingDayCalculator
        print("✅ Date utilities imported")
        
        from ui.admin_panel import show_admin_panel
        print("✅ Admin panel imported")
        
        from ui.auditor_dashboard import show_auditor_dashboard
        print("✅ Auditor dashboard imported")
        
        return True
    
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def test_database():
    """Test database initialization"""
    print("\nTesting database setup...")
    
    try:
        from data.db_manager import DatabaseManager
        
        db = DatabaseManager()
        print("✅ Main database initialized")
        
        # Test auditor DB creation
        db.init_auditor_db(999)  # Test with ID 999
        print("✅ Auditor database creation works")
        
        # Clean up test DB
        test_db = Path("data/auditor_999.db")
        if test_db.exists():
            test_db.unlink()
            print("✅ Test database cleaned up")
        
        return True
    
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def test_utilities():
    """Test utility functions"""
    print("\nTesting utilities...")
    
    try:
        from utils.date_utils import WorkingDayCalculator
        from datetime import datetime, timedelta
        
        calc = WorkingDayCalculator()
        
        # Test working day calculation
        start = datetime(2025, 1, 6)  # Monday
        end = datetime(2025, 1, 10)   # Friday
        days = calc.working_days_between(start, end)
        
        if days == 4:  # Mon to Thu = 4 days
            print(f"✅ Working day calculation correct (got {days} days)")
        else:
            print(f"⚠️  Working day calculation unexpected (got {days}, expected 4)")
        
        return True
    
    except Exception as e:
        print(f"❌ Utility error: {e}")
        return False


def test_encryption():
    """Test encryption/decryption"""
    print("\nTesting encryption...")
    
    try:
        from utils.encryption import encrypt_email_config, decrypt_email_config
        
        # Test data
        test_config = {
            "imap_host": "imap.test.com",
            "imap_port": 993,
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "email": "test@test.com",
            "password": "secret123"
        }
        
        # Encrypt
        encrypted = encrypt_email_config(
            test_config["imap_host"],
            test_config["imap_port"],
            test_config["smtp_host"],
            test_config["smtp_port"],
            test_config["email"],
            test_config["password"]
        )
        print("✅ Encryption successful")
        
        # Decrypt
        decrypted = decrypt_email_config(encrypted)
        
        if decrypted["email"] == test_config["email"]:
            print("✅ Decryption successful")
            return True
        else:
            print("❌ Decryption failed - data mismatch")
            return False
    
    except Exception as e:
        print(f"❌ Encryption error: {e}")
        return False


def check_dependencies():
    """Check if all required packages are installed"""
    print("\nChecking dependencies...")
    
    required = [
        'streamlit',
        'bcrypt',
        'cryptography',
        'pandas',
        'openpyxl'
    ]
    
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Email Follow-Up Audit Tool - Setup Test")
    print("=" * 60)
    print()
    
    tests = [
        ("Dependencies", check_dependencies),
        ("Imports", test_imports),
        ("Database", test_database),
        ("Utilities", test_utilities),
        ("Encryption", test_encryption)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("  1. Run: python create_admin.py")
        print("  2. Run: streamlit run main.py")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    print()


if __name__ == "__main__":
    main()
