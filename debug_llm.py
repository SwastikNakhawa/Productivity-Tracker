# debug_llm.py
import sys
import os
import requests

print("🚀 Starting LLM Connection Test...")
print("=" * 60)

# Add the parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

print(f"📁 Current directory: {current_dir}")
print(f"📁 Parent directory: {parent_dir}")
print(f"📦 Python path: {sys.path}")

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
    print("   💡 Make sure Ollama is running: ollama serve")

print("\n" + "=" * 60)

# Test 2: Check if we can import the LLM client with different approaches
print("2. 📦 Checking imports...")

# Try different import approaches
try:
    # Approach 1: Direct import
    from analysis.llm_integration import LocalLLMClient

    print("   ✅ Import successful using: from analysis.llm_integration import LocalLLMClient")
    import_method = 1
except ImportError as e:
    print(f"   ❌ Approach 1 failed: {e}")
    try:
        # Approach 2: Import the file directly
        import importlib.util

        spec = importlib.util.spec_from_file_location("llm_integration",
                                                      os.path.join(current_dir, "analysis", "llm_integration.py"))
        llm_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(llm_module)
        LocalLLMClient = llm_module.LocalLLMClient
        print("   ✅ Import successful using direct file import")
        import_method = 2
    except Exception as e2:
        print(f"   ❌ Approach 2 failed: {e2}")
        try:
            # Approach 3: Check if files exist
            analysis_dir = os.path.join(current_dir, "analysis")
            llm_file = os.path.join(analysis_dir, "llm_integration.py")
            print(f"   📁 Analysis directory exists: {os.path.exists(analysis_dir)}")
            print(f"   📄 LLM integration file exists: {os.path.exists(llm_file)}")

            if os.path.exists(llm_file):
                print("   📝 File structure looks correct, but import is failing")
            else:
                print("   ❌ LLM integration file not found!")

            LocalLLMClient = None
            import_method = 0
        except Exception as e3:
            print(f"   ❌ Approach 3 failed: {e3}")
            LocalLLMClient = None
            import_method = 0

print("\n" + "=" * 60)

# Test 3: Test LLM client if import was successful
if LocalLLMClient:
    print("3. 🤖 Testing LLM client...")
    try:
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

    except Exception as e:
        print(f"   ❌ LLM client test failed: {e}")
        import traceback

        traceback.print_exc()
else:
    print("3. ❌ Cannot test LLM client - import failed")

print("\n" + "=" * 60)
print("🎯 Summary:")
print(f"   • Ollama: {'✅ Running' if 'Ollama is running' in locals() else '❌ Not running'}")
print(f"   • Models: {'✅ Available' if 'available_models' in locals() and available_models else '❌ No models'}")
print(f"   • LLM Import: {'✅ Success' if LocalLLMClient else '❌ Failed'}")
print(f"   • LLM Client: {'✅ Created' if 'llm' in locals() else '❌ Not created'}")

print("\n" + "=" * 60)
print("💡 Next steps:")
if not LocalLLMClient:
    print("   1. Check your file structure - make sure 'analysis' folder exists")
    print("   2. Make sure 'llm_integration.py' is in the analysis folder")
    print("   3. Try running from the correct directory")

input("Press Enter to exit...")