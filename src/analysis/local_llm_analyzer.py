# analysis/local_llm_analyzer.py
import logging
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime


class LocalLLMClient:
    def __init__(self, model_name: str = "mistral:latest", base_url: str = "http://localhost:11434"):
        self.setup_logging()
        self.base_url = base_url
        self.model_name = model_name
        self.is_available = False
        self._check_connection()

    def setup_logging(self):
        self.logger = logging.getLogger(__name__)

    def _check_connection(self):
        """Check if local LLM server is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.is_available = True
                self.logger.info(f"✅ Local LLM connected: {self.base_url}")

                # Check if our model is available
                models = response.json().get('models', [])
                available_models = [model['name'] for model in models]
                self.logger.info(f"Available models: {available_models}")

                if self.model_name not in available_models and available_models:
                    # Use first available model
                    self.model_name = available_models[0]
                    self.logger.info(f"Using available model: {self.model_name}")
            else:
                self.logger.warning("LLM server responded with non-200 status")
        except Exception as e:
            self.logger.warning(f"❌ Local LLM not available: {e}")
            self.is_available = False

    def _call_llm(self, prompt: str, system_prompt: str = None, max_tokens: int = 500) -> str:
        """Make API call to local LLM"""
        if not self.is_available:
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

            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result['message']['content']
            else:
                self.logger.error(f"LLM API error: {response.status_code}")
                return self._get_fallback_response(prompt)

        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return self._get_fallback_response(prompt)

    def _get_fallback_response(self, prompt: str) -> str:
        """Provide fallback responses when LLM is unavailable"""
        self.logger.info("Using fallback response")

        if "motivational" in prompt.lower():
            return "Stay focused and keep making progress! Every minute you spend productively brings you closer to your goals. 💪"

        elif "recommendation" in prompt.lower() or "study" in prompt.lower():
            return "Continue with your current productive work. Consider exploring official documentation, online tutorials, or practice exercises to deepen your skills."

        return "Keep up the good work! Stay consistent with your productive activities."

    def generate_motivational_quote(self, activity: Dict) -> str:
        """Generate context-aware motivational quote based on current activity"""
        app_name = activity.get('app_name', 'current application')
        category = activity.get('category', 'unknown')
        score = activity.get('productivity_score', 50)

        system_prompt = """You are a motivational coach specializing in productivity and focus. 
        Provide short, inspiring quotes (1-2 sentences) that encourage users to stay focused 
        and maintain productivity. Be positive and encouraging."""

        prompt = f"""
        The user is currently using: {app_name} (category: {category})
        Productivity score: {score}/100

        Generate a motivational quote to help them stay focused and productive.
        Keep it brief (1-2 sentences), positive, and actionable.
        """

        quote = self._call_llm(prompt, system_prompt, max_tokens=100)
        self.logger.info(f"Generated motivational quote for {app_name}")
        return quote.strip()

    def generate_study_recommendations(self, activities: List[Dict]) -> List[str]:
        """Generate personalized study recommendations based on productive activities"""
        if not activities:
            return ["Start tracking productive activities to get personalized recommendations!"]

        # Analyze activity patterns
        productive_categories = {}
        for activity in activities:
            category = activity.get('category', 'general')
            duration = activity.get('duration', 0)
            productive_categories[category] = productive_categories.get(category, 0) + duration

        # Get top categories
        top_categories = sorted(productive_categories.items(), key=lambda x: x[1], reverse=True)[:3]

        system_prompt = """You are an expert learning advisor and career coach. 
        Provide specific, actionable study recommendations and learning resources 
        based on the user's productive activities. Focus on practical next steps."""

        prompt = f"""
        Based on the user's productive activities in these categories:
        {', '.join([f'{cat} ({duration}s)' for cat, duration in top_categories])}

        Provide 3-4 specific study recommendations. For each recommendation:
        - Be specific and actionable
        - Include types of resources (websites, books, courses, projects)
        - Focus on practical skill development
        - Keep each recommendation concise

        Format as a bulleted list without markdown.
        """

        recommendations_text = self._call_llm(prompt, system_prompt, max_tokens=300)

        # Parse the response into a list
        recommendations = []
        for line in recommendations_text.split('\n'):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                # Clean up the line
                clean_line = line.lstrip('•- ').lstrip('1234567890. ')
                if clean_line:
                    recommendations.append(clean_line)

        return recommendations[:4] if recommendations else [
            "Practice consistently with small, daily learning sessions",
            "Build projects to apply your knowledge practically",
            "Join online communities related to your interests",
            "Review and reflect on your progress weekly"
        ]


# Keep the existing ProductivityAgent class for backward compatibility
class ProductivityAgent:
    def __init__(self):
        self.setup_logging()
        from analysis.llm_integration import LocalLLMClient as NewLLMClient
        self.analyzer = NewLLMClient()
        self.analysis_interval = 300
        self.running = True
        self.logger.info("Productivity Agent initialized with LocalLLMAnalyzer")

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def start_background_analysis(self):
        """Run productivity analysis in background thread"""

        def analysis_loop():
            self.logger.info("🔄 Starting background analysis loop")
            while self.running:
                try:
                    self.perform_analysis()
                except Exception as e:
                    self.logger.error(f"Analysis loop error: {e}")
                for _ in range(self.analysis_interval):
                    if not self.running:
                        break
                    time.sleep(1)
            self.logger.info("🛑 Background analysis stopped")

        analysis_thread = threading.Thread(target=analysis_loop, daemon=True)
        analysis_thread.start()

    def perform_analysis(self):
        """Perform single analysis cycle"""
        self.logger.info("🔍 Performing productivity analysis...")
        # Implementation here...

    def stop(self):
        """Stop the agent"""
        self.logger.info("🛑 Stopping Productivity Agent...")
        self.running = False