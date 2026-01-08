# check_gui.py
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

print("🔍 Checking for GUI files...")
print("Current directory:", current_dir)

# Check for GUI files
gui_files = [
    "ui/main_modern_gui.py",
    "main_modern_gui.py",
    "main_modern_gui.ipynb",
    "ui/main_modern_gui.ipynb"
]

for file_path in gui_files:
    full_path = os.path.join(current_dir, file_path)
    if os.path.exists(full_path):
        print(f"✅ FOUND: {file_path}")
        # Check if it's a Python file or notebook
        if file_path.endswith('.ipynb'):
            print("   📓 This is a Jupyter notebook - needs conversion to .py")
    else:
        print(f"❌ MISSING: {file_path}")

# Check for customtkinter
try:
    import customtkinter as ctk
    print("✅ customtkinter: INSTALLED")
except ImportError:
    print("❌ customtkinter: NOT INSTALLED")
    print("💡 Run: pip install customtkinter")

# Check for tkinter
try:
    import tkinter as tk
    print("✅ tkinter: AVAILABLE")
except ImportError:
    print("❌ tkinter: NOT AVAILABLE")

print("\n💡 Next steps:")
print("1. If you have main_modern_gui.ipynb, convert it to .py file")
print("2. If no GUI files exist, we'll create a simple one")