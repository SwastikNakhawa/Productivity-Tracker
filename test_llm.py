# test_src_structure.py
import sys
import os
import requests

print("🚀 Testing LLM with src/ folder structure...")
print("=" * 60)

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")

print(f"📁 Current directory: {current_dir}")
print(f"📁 Source directory: {src_dir}")

# Add src to path
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

print(f"📦 Python path: {[p for p in sys.path if 'Productivity' in p]}")

print("\n" + "=" * 60)

# Test 1: Check if Ollama is running
print("1. 🔍 Checking Ollama service...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("   ✅ Ollama is running!")
        models_data = response.json().get('models', [])
        if models_data:
            available_models = [model['name'] for model in models_data]
            print(f"   📚 Available models: {available_models}")
        else:
            print("   ⚠️  No models found.")
    else:
        print(f"   ❌ Ollama responded with status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Cannot connect to Ollama: {e}")

print("\n" + "=" * 60)

# Test 2: Check if we can import from src folder
print("2. 📦 Checking imports from src/...")

# Check if src folder exists
if not os.path.exists(src_dir):
    print(f"   ❌ src folder not found at: {src_dir}")
    print("   💡 Make sure your files are in a 'src' folder")
else:
    print(f"   ✅ src folder exists")

    # Check what's in src folder
    print("   📁 Contents of src folder:")
    for item in os.listdir(src_dir):
        item_path = os.path.join(src_dir, item)
        if os.path.isdir(item_path):
            print(f"      📂 {item}/")
        else:
            print(f"      📄 {item}")

try:
    from analysis.llm_integration import LocalLLMClient

    print("   ✅ Import successful: from analysis.llm_integration import LocalLLMClient")

    print("\n3. 🤖 Testing LLM client...")
    llm = LocalLLMClient()
    print(f"   ✅ LLM client created")
    print(f"   📡 Available: {llm.is_available}")
    print(f"   🎯 Model: {llm.model_name}")

    if llm.is_available:
        print("\n4. 🧪 Testing LLM functions...")

        # Test a simple prompt
        print("   Testing simple prompt...")
        response = llm._call_llm("Say 'Hello World' in one sentence.", "You are a helpful assistant.")
        print(f"   💬 Response: {response}")

        # Test motivational quote
        print("   Testing motivational quote...")
        test_activity = {"app_name": "VS Code", "category": "development", "productivity_score": 85}
        quote = llm.generate_motivational_quote(test_activity)
        print(f"   💫 Quote: {quote}")

        print("\n   ✅ All tests passed! LLM is working correctly.")
    else:
        print("\n   ❌ LLM client is not available")
        print("   💡 Check Ollama installation and models")

except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    print("\n   🔧 Trying alternative import approaches...")

    # Try alternative import
    try:
        import importlib.util

        llm_path = os.path.join(src_dir, "analysis", "llm_integration.py")
        if os.path.exists(llm_path):
            print(f"   ✅ LLM file exists at: {llm_path}")
            spec = importlib.util.spec_from_file_location("llm_integration", llm_path)
            llm_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(llm_module)
            LocalLLMClient = llm_module.LocalLLMClient
            print("   ✅ Import successful using direct file path")

            # Test the client
            llm = LocalLLMClient()
            print(f"   🤖 LLM Client created! Available: {llm.is_available}")
        else:
            print(f"   ❌ LLM file not found at: {llm_path}")
    except Exception as e2:
        print(f"   ❌ Alternative import also failed: {e2}")

print("\n" + "=" * 60)
print("🎯 Summary:")
print(f"   • src folder: {'✅ Found' if os.path.exists(src_dir) else '❌ Missing'}")
print(f"   • Imports: {'✅ Working' if 'LocalLLMClient' in locals() else '❌ Failed'}")
print(f"   • LLM Available: {'✅ Yes' if 'llm' in locals() and llm.is_available else '❌ No'}")

input("Press Enter to exit...")