# analysis/llm_integration.py
import logging
import requests
import json
import random
from typing import List, Dict, Optional, Any
from datetime import datetime


class DataBridge:
    """Bridge between database and LLM for analysis"""

    def __init__(self, database_manager=None, llm_client=None):
        self.db = database_manager
        self.llm_client = llm_client

    def get_activities_for_analysis(self, hours=24, limit=50):
        """Get recent activities formatted for LLM analysis - FIXED VERSION"""
        try:
            activities = []
            if self.db:
                if hasattr(self.db, 'get_recent_activities'):
                    # Use the fixed method with hours parameter
                    activities = self.db.get_recent_activities(limit=limit, hours=hours)
                else:
                    print("⚠️ Database has no get_activities method")

            if not activities:
                return []

            # Format activities for LLM consumption
            formatted_activities = []
            for activity in activities:
                # Handle different date formats
                start_time = activity.get('start_time', '')
                if hasattr(start_time, 'strftime'):
                    time_str = start_time.strftime('%H:%M')
                else:
                    time_str = str(start_time)[:19]  # Take first 19 chars

                formatted = {
                    'app_name': activity.get('app_name', 'Unknown'),  # Fixed: use app_name consistently
                    'window_title': activity.get('window_title', '')[:100],
                    'category': activity.get('category', 'unknown'),
                    'productivity_score': activity.get('productivity_score', 50),
                    'duration': activity.get('duration', 0),
                    'time': time_str
                }
                formatted_activities.append(formatted)

            return formatted_activities

        except Exception as e:
            print(f"❌ Error getting activities for analysis: {e}")
            return []

    def prepare_analysis_context(self, activities):
        """Prepare context for LLM analysis"""
        if not activities:
            return "No activity data available for analysis."

        # Calculate basic statistics
        total_activities = len(activities)
        productive_activities = [a for a in activities if a.get('productivity_score', 0) > 60]
        unproductive_activities = [a for a in activities if a.get('productivity_score', 0) < 40]

        productive_time = sum(a.get('duration', 0) for a in productive_activities)
        total_time = sum(a.get('duration', 0) for a in activities)
        productivity_ratio = (productive_time / total_time * 100) if total_time > 0 else 0

        # Get top categories and apps
        categories = {}
        apps = {}
        for activity in activities:
            category = activity.get('category', 'unknown')
            app_name = activity.get('app_name', 'unknown')
            categories[category] = categories.get(category, 0) + 1
            apps[app_name] = apps.get(app_name, 0) + 1

        top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else 'unknown'
        top_app = max(apps.items(), key=lambda x: x[1])[0] if apps else 'unknown'

        context = f"""
ACTIVITY ANALYSIS DATA:
- Total activities: {total_activities}
- Productive activities: {len(productive_activities)} ({len(productive_activities) / total_activities * 100:.1f}%)
- Unproductive activities: {len(unproductive_activities)} ({len(unproductive_activities) / total_activities * 100:.1f}%)
- Productivity ratio: {productivity_ratio:.1f}%
- Most used category: {top_category}
- Most used app: {top_app}

RECENT ACTIVITIES:
"""
        # Add recent activities
        for i, activity in enumerate(activities[:10], 1):
            context += f"{i}. {activity['app_name']} - {activity['window_title']} ({activity['category']}, score: {activity['productivity_score']}, {activity['duration']}s)\n"

        return context


class LocalLLMClient:
    def __init__(self, model_name: str = "llama3.2:latest", base_url: str = "http://localhost:11434"):
        self.setup_logging()
        self.base_url = base_url
        self.model_name = model_name
        self.is_available = False
        self.available_models = []
        self.data_bridge = DataBridge()
        self._check_connection()

    def setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _check_connection(self):
        """Check if local LLM server is available and update available models"""
        try:
            self.logger.info(f"🔍 Checking LLM connection to {self.base_url}...")
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                self.is_available = True
                models_data = response.json().get('models', [])
                self.available_models = [model['name'] for model in models_data]
                self.logger.info(f"✅ Local LLM connected. Available models: {self.available_models}")

                # Check if our current model is available
                if self.available_models:
                    if self.model_name not in self.available_models:
                        self.logger.warning(
                            f"Model {self.model_name} not found. Using first available: {self.available_models[0]}")
                        self.model_name = self.available_models[0]
                else:
                    self.logger.warning("No models available. Please pull a model with: ollama pull llama3.2:latest")
                return True
        except Exception as e:
            self.logger.warning(f"❌ Local LLM not available: {e}")
            self.is_available = False
            self.available_models = []
        return False

    def test_connection_detailed(self):
        """Test LLM connection with detailed diagnostics"""
        try:
            print("🔍 Testing LLM Connection...")

            # Test basic connectivity
            if not self.is_available:
                print("❌ LLM not available - checking connection...")
                self._check_connection()

            if not self.is_available:
                print("❌ LLM server is not running or inaccessible")
                print("💡 Make sure Ollama is running: ollama serve")
                print("💡 Check if port 11434 is available")
                return False

            print(f"✅ LLM Server: {self.base_url}")
            print(f"✅ Available Models: {self.available_models}")
            print(f"✅ Current Model: {self.model_name}")

            # Test a simple prompt
            test_prompt = "Say 'Hello World' in one sentence."
            response = self._call_llm(test_prompt, "You are a helpful assistant.", 50)

            if response and len(response) > 0:
                print(f"✅ LLM Response Test: {response}")
                return True
            else:
                print("❌ LLM responded with empty string")
                return False

        except Exception as e:
            print(f"❌ LLM Connection Error: {e}")
            return False

    def set_model(self, model_name: str) -> bool:
        """Change the LLM model and verify it's available"""
        old_model = self.model_name
        self.model_name = model_name

        # Refresh connection to check if new model is available
        if self._check_connection():
            if self.model_name in self.available_models:
                self.logger.info(f"✅ Model changed from {old_model} to {self.model_name}")
                return True
            else:
                self.logger.warning(f"❌ Model {model_name} not available. Reverting to {old_model}")
                self.model_name = old_model
                return False
        return False

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        self._check_connection()  # Refresh the list
        return self.available_models

    def _call_llm(self, prompt: str, system_prompt: str = None, max_tokens: int = 300) -> str:
        """Make API call to local LLM with enhanced error handling"""
        if not self.is_available:
            self.logger.warning("LLM not available, using fallback response")
            return self._get_fallback_response(prompt)

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": max_tokens
                }
            }

            self.logger.info(f"🤖 Calling LLM with model: {self.model_name}")
            self.logger.debug(f"Prompt: {prompt[:100]}...")

            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60  # Increased timeout
            )

            if response.status_code == 200:
                result = response.json()
                content = result['message']['content'].strip()
                self.logger.info(f"✅ LLM Response received ({self.model_name}): {content[:100]}...")
                return content
            else:
                self.logger.error(f"❌ LLM API error: {response.status_code} - {response.text}")
                return self._get_fallback_response(prompt)

        except requests.exceptions.Timeout:
            self.logger.error("❌ LLM request timeout")
            return self._get_fallback_response(prompt)
        except requests.exceptions.ConnectionError:
            self.logger.error("❌ LLM connection error - server may be down")
            self.is_available = False
            return self._get_fallback_response(prompt)
        except Exception as e:
            self.logger.error(f"❌ LLM call failed: {e}")
            return self._get_fallback_response(prompt)

    def _get_fallback_response(self, prompt: str) -> str:
        """Provide intelligent fallback responses"""
        self.logger.info("Using fallback response")

        # Motivational quotes and prompts
        if "motivational" in prompt.lower() or "quote" in prompt.lower():
            motivational_quotes = [
                "Every minute you spend productively brings you closer to your goals! 🚀",
                "Stay focused - your future self will thank you for the effort you put in today! 💪",
                "Small, consistent actions lead to big results. Keep going! 🌟",
                "You're capable of amazing things when you stay focused and determined! ✨",
                "Progress, not perfection. Every step forward counts! 🎯",
                "Your dedication to productivity today builds your success tomorrow! 🌈",
                "Keep pushing forward - every focused moment matters! ⚡"
            ]
            return random.choice(motivational_quotes)

        # Study recommendations
        elif "recommendation" in prompt.lower() or "study" in prompt.lower():
            study_recommendations = [
                "Check out freeCodeCamp for hands-on coding projects and certifications",
                "Practice problem-solving on LeetCode to improve your coding skills",
                "Read official documentation and build a small project to apply your knowledge",
                "Join online communities like Stack Overflow for peer learning and support",
                "Watch tutorial videos and follow along with code examples to reinforce learning",
                "Work on personal projects to apply theoretical knowledge in practical scenarios",
                "Participate in coding challenges on HackerRank to sharpen your skills"
            ]
            return "\n".join(random.sample(study_recommendations, 3))

        # Productivity analysis fallback
        elif "analysis" in prompt.lower() or "productivity" in prompt.lower():
            analysis_fallbacks = [
                "Based on your activity patterns, maintaining consistent work sessions will boost your productivity. Try the Pomodoro technique!",
                "Your work habits show potential for increased focus. Consider scheduling deep work sessions without distractions.",
                "Tracking your activities is the first step to improvement. Keep monitoring to identify patterns and optimize your workflow."
            ]
            return random.choice(analysis_fallbacks)

        return "Keep up the great work! Stay consistent with your learning journey and track your progress."

    def _get_fallback_analysis(self, activities: List[Dict]) -> Dict:
        """Provide intelligent fallback when LLM is unavailable"""
        self.logger.info("🔄 Using fallback analysis...")

        if not activities:
            return {
                "insight": "Start tracking your activities to get personalized insights!",
                "productivity_score": 50,
                "activities_analyzed": 0,
                "model_used": "fallback",
                "status": "no_data"
            }

        # Basic analysis without LLM
        productive_activities = [a for a in activities if a.get('productivity_score', 0) > 60]
        unproductive_activities = [a for a in activities if a.get('productivity_score', 0) < 40]

        productive_time = sum(a.get('duration', 0) for a in productive_activities)
        total_time = sum(a.get('duration', 0) for a in activities)
        productivity_ratio = (productive_time / total_time * 100) if total_time > 0 else 0

        # Get top categories
        categories = {}
        for activity in activities:
            category = activity.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1

        top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else 'unknown'

        # Simple rule-based insights
        if productivity_ratio > 70:
            insight = f"Excellent work! You're maintaining high productivity ({productivity_ratio:.1f}%). Your focus on {top_category} is paying off!"
        elif productivity_ratio > 50:
            insight = f"Good balance! You're at {productivity_ratio:.1f}% productivity. Try scheduling focused sessions for {top_category} to reach the next level."
        else:
            insight = f"Time for optimization! At {productivity_ratio:.1f}% productivity, consider minimizing distractions during {top_category} work. You can do this!"

        return {
            "productivity_score": int(productivity_ratio),
            "insight": insight,
            "activities_analyzed": len(activities),
            "productive_ratio": f"{productivity_ratio:.1f}%",
            "model_used": "fallback_analysis",
            "status": "fallback"
        }

    def generate_motivational_quote(self, activity: Dict) -> str:
        """Generate context-aware motivational quote based on current activity - FIXED VERSION"""
        app_name = activity.get('app_name', 'current application')
        category = activity.get('category', 'unknown')
        score = activity.get('productivity_score', 50)

        system_prompt = """You are an enthusiastic productivity coach. Generate short, inspiring, 
        and personalized motivational quotes that relate to the user's specific current activity. 
        Be positive, specific, and actionable."""

        prompt = f"""
        User is currently using: {app_name}
        Category: {category}
        Productivity score: {score}/100

        Context:
        - If score < 30: They're likely distracted and need motivation to focus
        - If score 30-70: They're in neutral territory, encourage productive choices
        - If score > 70: They're being productive, encourage continuation

        Generate ONE short, personalized motivational quote (just 1 sentence) that:
        - Specifically relates to {app_name} and {category}
        - Is appropriate for their productivity level ({score}/100)
        - Encourages the right behavior (focus vs. continuation vs. redirection)
        - Maximum 15 words
        - Feel authentic and personalized

        Quote only (no explanations):
        """

        self.logger.info(f"🎯 Generating quote for {app_name} (score: {score})")

        quote = self._call_llm(prompt, system_prompt, max_tokens=50)
        result = quote.strip('"').strip()

        self.logger.info(f"🎯 Generated quote: {result}")

        return result

    def generate_study_recommendations(self, activities: List[Dict]) -> List[str]:
        """Generate personalized study recommendations based on productive activities"""
        if not activities:
            return ["Start tracking productive work to get personalized recommendations!"]

        # Analyze what the user has been working on
        productive_activities = [act for act in activities if act.get('productivity_score', 0) > 60]

        if not productive_activities:
            return ["Keep tracking your work to receive personalized learning suggestions!"]

        # Find common categories and apps
        categories = {}
        apps = {}

        for activity in productive_activities[-10:]:  # Last 10 productive activities
            category = activity.get('category', 'general')
            app_name = activity.get('app_name', '')
            categories[category] = categories.get(category, 0) + 1
            if app_name:
                apps[app_name] = apps.get(app_name, 0) + 1

        top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else 'programming'
        top_app = max(apps.items(), key=lambda x: x[1])[0] if apps else ''

        system_prompt = """You are a expert learning advisor and career coach. Provide specific, 
        actionable study recommendations based on the user's work patterns. Focus on practical 
        next steps that build on their current skills."""

        prompt = f"""
        User's productive work pattern:
        - Most common category: {top_category}
        - Frequently used app: {top_app}
        - Recent productive activities: {len(productive_activities)}
        - Current LLM Model: {self.model_name}

        Provide 3 SPECIFIC, ACTIONABLE study recommendations that:
        1. Build on their current {top_category} work
        2. Are practical and immediately useful
        3. Include specific resources or next steps
        4. Are concise (one line each)

        Format as a numbered list without markdown:
        1. First recommendation
        2. Second recommendation  
        3. Third recommendation
        """

        response = self._call_llm(prompt, system_prompt, max_tokens=200)

        # Parse the response
        recommendations = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Clean up the line
                clean_line = line.lstrip('1234567890.-• ').strip()
                if clean_line and len(clean_line) > 10:  # Meaningful content
                    recommendations.append(clean_line)

        return recommendations[:3] if recommendations else [
            f"Deepen your {top_category} skills with hands-on projects",
            f"Explore advanced features of {top_app} through tutorials",
            "Join relevant online communities for knowledge sharing"
        ]

    def analyze_productivity_trend(self, activities: List[Dict]) -> Dict:
        """Analyze productivity patterns and provide insights - FIXED VERSION"""
        self.logger.info("🤖 Starting productivity analysis...")

        if len(activities) < 3:
            return {
                "insight": "Need more activity data for analysis! Track at least 3 activities.",
                "productivity_score": 50,
                "activities_analyzed": len(activities),
                "model_used": self.model_name,
                "status": "insufficient_data"
            }

        try:
            # Test LLM connection first
            if not self.is_available:
                self.logger.warning("LLM not available, using fallback analysis")
                return self._get_fallback_analysis(activities)

            # Calculate REAL metrics from actual activities
            productive_activities = [a for a in activities if a.get('productivity_score', 0) > 60]
            unproductive_activities = [a for a in activities if a.get('productivity_score', 0) < 40]

            productive_time = sum(a.get('duration', 0) for a in productive_activities)
            total_time = sum(a.get('duration', 0) for a in activities)
            productivity_ratio = (productive_time / total_time * 100) if total_time > 0 else 0

            # Get actual categories and apps from real data
            categories = {}
            apps = {}
            for activity in activities[-10:]:  # Last 10 activities
                category = activity.get('category', 'unknown')
                app_name = activity.get('app_name', 'unknown')
                categories[category] = categories.get(category, 0) + 1
                apps[app_name] = apps.get(app_name, 0) + 1

            top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else 'unknown'
            top_app = max(apps.items(), key=lambda x: x[1])[0] if apps else 'unknown'

            system_prompt = """You are a productivity analyst. Provide brief, actionable insights 
            about work patterns. Be constructive and encouraging. Use the actual data provided.
            Focus on specific observations and practical suggestions."""

            prompt = f"""
            REAL USER DATA - Analyze this actual productivity data:

            Recent Activities ({len(activities)} total):
            {chr(10).join([f"- {a.get('app_name', 'Unknown')} ({a.get('category', 'unknown')}): Score {a.get('productivity_score', 50)}/100, Duration: {a.get('duration', 0)}s" for a in activities[-5:]])}

            Key Metrics:
            - Productive activities: {len(productive_activities)}/{len(activities)}
            - Unproductive activities: {len(unproductive_activities)}/{len(activities)}
            - Productivity ratio: {productivity_ratio:.1f}%
            - Most used category: {top_category}
            - Most used app: {top_app}

            Provide a brief analysis (2-3 sentences) with:
            1. One observation about their actual work patterns
            2. One specific suggestion based on their real app usage
            3. Keep it encouraging and actionable

            Analysis:
            """

            self.logger.info(f"📊 Sending to LLM: {len(activities)} activities, productivity: {productivity_ratio:.1f}%")

            analysis = self._call_llm(prompt, system_prompt, max_tokens=200)

            if not analysis or analysis.strip() == "":
                self.logger.warning("LLM returned empty analysis, using fallback")
                return self._get_fallback_analysis(activities)

            self.logger.info(f"✅ LLM Analysis received: {analysis[:100]}...")

            return {
                "productivity_score": int(productivity_ratio),
                "insight": analysis.strip(),
                "activities_analyzed": len(activities),
                "productive_ratio": f"{productivity_ratio:.1f}%",
                "model_used": self.model_name,
                "status": "success"
            }

        except Exception as e:
            self.logger.error(f"❌ Error in productivity analysis: {e}")
            return self._get_fallback_analysis(activities)

    def analyze_productivity_trend_enhanced(self, activities: List[Dict]) -> Dict:
        """Enhanced productivity analysis with proper error handling"""
        self.logger.info("🤖 Starting ENHANCED LLM productivity analysis...")

        if not activities or len(activities) < 3:
            return {
                "insight": "Need more activity data for analysis! Track more activities first.",
                "productivity_score": 50,
                "activities_analyzed": len(activities) if activities else 0,
                "model_used": self.model_name,
                "status": "insufficient_data"
            }

        try:
            # Test LLM connection first
            if not self.is_available:
                self.logger.warning("LLM not available, using fallback analysis")
                return self._get_fallback_analysis(activities)

            # Prepare data for LLM using DataBridge
            context = self.data_bridge.prepare_analysis_context(activities)

            system_prompt = """You are a productivity analyst. Analyze the user's computer activity patterns and provide:
            1. One specific observation about their work habits
            2. One actionable suggestion for improvement
            3. Keep it encouraging and practical (2-3 sentences total)

            Be specific about the apps and categories mentioned in the data."""

            prompt = f"""
            Please analyze this productivity data and provide brief, actionable insights:

            {context}

            Analysis (2-3 sentences, be specific and encouraging):
            """

            self.logger.info(f"📊 Sending enhanced analysis request to LLM...")
            self.logger.info(f"📝 Activities: {len(activities)}, Model: {self.model_name}")

            analysis = self._call_llm(prompt, system_prompt, max_tokens=200)

            if not analysis or analysis.strip() == "":
                self.logger.warning("LLM returned empty analysis")
                return self._get_fallback_analysis(activities)

            self.logger.info(f"✅ LLM Enhanced Analysis received: {analysis[:100]}...")

            # Calculate metrics
            productive_time = sum(a.get('duration', 0) for a in activities if a.get('productivity_score', 0) > 60)
            total_time = sum(a.get('duration', 0) for a in activities)
            productivity_ratio = (productive_time / total_time * 100) if total_time > 0 else 0

            return {
                "productivity_score": int(productivity_ratio),
                "insight": analysis.strip(),
                "activities_analyzed": len(activities),
                "productive_ratio": f"{productivity_ratio:.1f}%",
                "model_used": self.model_name,
                "status": "success"
            }

        except Exception as e:
            self.logger.error(f"❌ Error in enhanced productivity analysis: {e}")
            return self._get_fallback_analysis(activities)

    def generate_quick_feedback(self, current_activity: Dict, previous_activity: Dict = None) -> str:
        """Generate quick feedback for activity transitions"""
        current_app = current_activity.get('app_name', 'Unknown')
        current_score = current_activity.get('productivity_score', 50)

        system_prompt = """You are a focus coach. Provide very brief (5-7 words) feedback 
        when users switch activities. Be supportive and guiding."""

        if current_score >= 70:
            prompt = f"User just switched to {current_app} (productive). Give quick positive feedback:"
        elif current_score <= 30:
            prompt = f"User just switched to {current_app} (distracting). Give gentle reminder:"
        else:
            prompt = f"User just switched to {current_app} (neutral). Give balanced feedback:"

        feedback = self._call_llm(prompt, system_prompt, max_tokens=30)
        return feedback.strip()

    def test_connection(self) -> Dict:
        """Test LLM connection and return detailed status"""
        try:
            if not self.is_available:
                return {
                    "status": "offline",
                    "message": "LLM not available",
                    "model": self.model_name
                }

            # Test motivational quote generation
            test_activity = {"app_name": "VS Code", "category": "development", "productivity_score": 85}
            quote = self.generate_motivational_quote(test_activity)

            # Test recommendations
            recommendations = self.generate_study_recommendations([test_activity])

            # Test analysis
            analysis = self.analyze_productivity_trend([test_activity])

            return {
                "status": "online",
                "model": self.model_name,
                "available_models": self.available_models,
                "test_quote": quote,
                "test_recommendations": recommendations,
                "test_analysis": analysis.get('insight', 'No analysis'),
                "message": f"LLM is working correctly with model: {self.model_name}"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"LLM test failed: {e}",
                "model": self.model_name
            }

    def get_status(self) -> Dict:
        """Get current LLM status"""
        return {
            "available": self.is_available,
            "model": self.model_name,
            "available_models": self.available_models,
            "base_url": self.base_url,
            "timestamp": datetime.now().isoformat()
        }


# Diagnosis function
def diagnose_llm_issues():
    """Diagnose common LLM integration issues"""
    print("🔍 Diagnosing LLM Integration Issues...")
    print("=" * 50)

    # Check Ollama installation
    print("1. Checking Ollama installation...")
    try:
        import subprocess
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ollama is installed")
            if result.stdout.strip():
                print(f"   Available models:\n{result.stdout}")
            else:
                print("   No models found. Pull a model with: ollama pull llama3.2:latest")
        else:
            print("❌ Ollama not found in PATH")
            print("💡 Install from: https://ollama.ai")
    except Exception as e:
        print(f"❌ Cannot check Ollama: {e}")

    # Check if Ollama is running
    print("2. Checking Ollama service...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama service is running")
            models = response.json().get('models', [])
            if models:
                print(f"   Models via API: {[m['name'] for m in models]}")
            else:
                print("   No models available via API")
        else:
            print(f"❌ Ollama service not responding (status: {response.status_code})")
            print("💡 Start with: ollama serve")
    except Exception as e:
        print(f"❌ Cannot connect to Ollama service: {e}")

    # Check Python dependencies
    print("3. Checking Python dependencies...")
    try:
        import requests
        print("✅ requests module available")
    except ImportError:
        print("❌ requests module missing")
        print("💡 Install: pip install requests")

    # Test LLM client
    print("4. Testing LLM client...")
    try:
        llm = LocalLLMClient()
        status = llm.get_status()
        print(f"✅ LLM client initialized")
        print(f"   Available: {status['available']}")
        print(f"   Model: {status['model']}")
        print(f"   Available models: {status['available_models']}")

        if status['available']:
            test_result = llm.test_connection_detailed()
            if test_result:
                print("✅ LLM client test PASSED")
            else:
                print("❌ LLM client test FAILED")
        else:
            print("❌ LLM client cannot connect to server")

    except Exception as e:
        print(f"❌ LLM client error: {e}")

    print("=" * 50)
    print("💡 Next steps:")
    print("   1. Ensure Ollama is installed and running: ollama serve")
    print("   2. Pull a model: ollama pull llama3.2:latest")
    print("   3. Check if port 11434 is accessible")
    print(
        "   4. Test with: python -c 'from llm_integration import LocalLLMClient; llm = LocalLLMClient(); print(llm.test_connection_detailed())'")


if __name__ == "__main__":
    # Run diagnosis when script is executed directly
    diagnose_llm_issues()

    # Also test the LLM client
    print("\n" + "=" * 50)
    print("Testing LLM Client...")
    llm = LocalLLMClient()

    if llm.is_available:
        print("✅ LLM Client is ready!")

        # Test a simple analysis
        test_activities = [
            {"app_name": "VS Code", "category": "development", "productivity_score": 85, "duration": 1800,
             "window_title": "main.py"},
            {"app_name": "Chrome", "category": "research", "productivity_score": 75, "duration": 1200,
             "window_title": "Python Documentation"},
            {"app_name": "Spotify", "category": "entertainment", "productivity_score": 20, "duration": 600,
             "window_title": "Music Playlist"}
        ]

        analysis = llm.analyze_productivity_trend_enhanced(test_activities)
        print(f"📊 Test Analysis: {analysis['insight']}")
        print(f"📈 Score: {analysis['productivity_score']}%")
        print(f"🔧 Status: {analysis['status']}")
    else:
        print("❌ LLM Client is not available. Run the diagnosis above to fix issues.")