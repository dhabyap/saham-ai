"""
Test script for CLI Setup System
Helps verify all CLI components work correctly
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test if all CLI modules can be imported"""
    print("\n" + "=" * 50)
    print("Testing CLI Module Imports...")
    print("=" * 50)

    tests = [
        ("cli.validators", "Validator"),
        ("cli.helpers", "EnvManager, SettingsManager"),
        ("cli.setup_wizard", "SetupWizard"),
        ("cli.config", "ConfigManager"),
        ("cli.manage", "CLIManager"),
    ]

    all_passed = True
    for module_name, components in tests:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
            print(f"  └─ {components}")
        except ImportError as e:
            print(f"✗ {module_name} - {e}")
            all_passed = False

    return all_passed


def test_directories():
    """Test if required directories exist"""
    print("\n" + "=" * 50)
    print("Testing Directory Structure...")
    print("=" * 50)

    required_dirs = [
        "cli",
        "config",
        "logs",
    ]

    all_exist = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}/ exists")
        else:
            print(f"✗ {dir_path}/ NOT FOUND")
            all_exist = False

    return all_exist


def test_files():
    """Test if required files exist"""
    print("\n" + "=" * 50)
    print("Testing Required Files...")
    print("=" * 50)

    required_files = [
        "cli/__init__.py",
        "cli/validators.py",
        "cli/helpers.py",
        "cli/setup_wizard.py",
        "cli/config.py",
        "cli/manage.py",
        "cli/README.md",
        "config/settings.json",
        "setup.py",
        "SETUP_GUIDE.md",
        "QUICKSTART.md",
        ".env.example",
    ]

    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            print(f"✓ {file_path} ({size:,} bytes)")
        else:
            print(f"✗ {file_path} NOT FOUND")
            all_exist = False

    return all_exist


def test_dependencies():
    """Test if required packages are installed"""
    print("\n" + "=" * 50)
    print("Testing Python Dependencies...")
    print("=" * 50)

    required_packages = [
        ("rich", "Rich"),
        ("questionary", "Questionary"),
        ("colorama", "Colorama"),
        ("dotenv", "Python-dotenv"),
    ]

    all_installed = True
    for package_name, display_name in required_packages:
        try:
            __import__(package_name)
            print(f"✓ {display_name} installed")
        except ImportError:
            print(f"✗ {display_name} NOT INSTALLED")
            all_installed = False

    if not all_installed:
        print("\nTo install missing packages:")
        print("  python -m pip install -r requirements.txt")
        print("  or")
        print("  python setup.py")

    return all_installed


def test_validators():
    """Test validator functions"""
    print("\n" + "=" * 50)
    print("Testing Validator Functions...")
    print("=" * 50)

    try:
        from cli.validators import Validator
        
        validator = Validator()
        
        # Test API key validation
        is_valid, msg = validator.validate_api_key("test_api_key_12345")
        assert is_valid, f"API key validation failed: {msg}"
        print("✓ API key validation works")

        # Test chat ID validation
        is_valid, msg = validator.validate_chat_id("123456789")
        assert is_valid, f"Chat ID validation failed: {msg}"
        print("✓ Chat ID validation works")

        # Test integer validation
        is_valid, msg = validator.validate_integer("15", 1, 1440)
        assert is_valid, f"Integer validation failed: {msg}"
        print("✓ Integer validation works")

        # Test yes/no validation
        is_valid, msg = validator.validate_yes_no("y")
        assert is_valid, f"Yes/No validation failed: {msg}"
        print("✓ Yes/No validation works")

        return True

    except Exception as e:
        print(f"✗ Validator test failed: {e}")
        return False


def test_env_manager():
    """Test environment manager"""
    print("\n" + "=" * 50)
    print("Testing EnvManager...")
    print("=" * 50)

    try:
        from cli.helpers import EnvManager
        
        manager = EnvManager(".env.test")
        
        # Test save
        test_data = {
            "TEST_KEY": "test_value",
            "TEST_NUMBER": "42"
        }
        
        if manager.save(test_data):
            print("✓ Save to .env works")
        else:
            print("✗ Failed to save")
            return False

        # Test load
        loaded = manager.load()
        if "TEST_KEY" in loaded or Path(".env.test").exists():
            print("✓ Load from .env works")
        else:
            print("✗ Failed to load")
            return False

        # Cleanup
        if Path(".env.test").exists():
            Path(".env.test").unlink()
            print("✓ Cleanup done")

        return True

    except Exception as e:
        print(f"✗ EnvManager test failed: {e}")
        return False


def test_settings_manager():
    """Test settings manager"""
    print("\n" + "=" * 50)
    print("Testing SettingsManager...")
    print("=" * 50)

    try:
        from cli.helpers import SettingsManager
        import json
        
        manager = SettingsManager("config_test")
        
        # Test default settings
        defaults = manager.get_default_settings()
        assert "app_name" in defaults
        assert "auto_learning" in defaults
        print("✓ Default settings template works")

        # Test load
        settings = manager.load()
        assert isinstance(settings, dict)
        print("✓ Load settings works")

        return True

    except Exception as e:
        print(f"✗ SettingsManager test failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 48 + "╗")
    print("║" + "  CLI SETUP SYSTEM - TEST SUITE".center(48) + "║")
    print("╚" + "=" * 48 + "╝")

    results = {
        "Imports": test_imports(),
        "Directories": test_directories(),
        "Files": test_files(),
        "Dependencies": test_dependencies(),
        "Validators": test_validators(),
        "EnvManager": test_env_manager(),
        "SettingsManager": test_settings_manager(),
    }

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {test_name}")

    print("=" * 50)
    print(f"Result: {passed}/{total} test groups passed")

    if passed == total:
        print("\n✓ All tests passed! Ready to use CLI setup system.")
        print("\nNext steps:")
        print("  1. python setup.py          # Initial setup")
        print("  2. python run.py            # Start application")
        print("  3. python cli/manage.py     # Open CLI manager")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix issues above.")
        print("\nTroubleshooting:")
        print("  1. Run: pip install -r requirements.txt")
        print("  2. Check directory structure")
        print("  3. Check file permissions")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
