import logging
import sys
import os
import time
import threading
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from collections import deque, defaultdict

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  requests module not available - browser tracking limited")

try:
    from urllib.parse import urlparse

    HAS_URLPARSE = True
except ImportError:
    HAS_URLPARSE = False


class FocusSessionTracker:
    """Track focused work sessions across browser activities"""

    def __init__(self, session_threshold: int = 300):  # 5 minutes
        self.session_threshold = session_threshold
        self.current_session = None
        self.sessions = []
        self.session_id_counter = 0

    def _is_productive_activity(self, activity: Dict) -> bool:
        """Check if activity is considered productive"""
        return activity.get('productivity_score', 0) > 60

    def update_session(self, activity: Dict) -> Optional[Dict]:
        """Update current focus session and return session data if completed"""
        if self._is_productive_activity(activity):
            if not self.current_session:
                # Start new session
                self.session_id_counter += 1
                self.current_session = {
                    'session_id': self.session_id_counter,
                    'start_time': activity['start_time'],
                    'end_time': activity['end_time'],
                    'activities': [activity],
                    'total_duration': activity['duration'],
                    'category': activity['category']
                }
            else:
                # Continue session - check if it's the same category
                time_gap = (activity['start_time'] - self.current_session['end_time']).total_seconds()

                if (time_gap < 600 and  # Less than 10 minutes gap
                        activity['category'] == self.current_session['category']):
                    # Continue existing session
                    self.current_session['activities'].append(activity)
                    self.current_session['total_duration'] += activity['duration']
                    self.current_session['end_time'] = activity['end_time']
                else:
                    # End current session and start new one
                    completed_session = self._finalize_session()
                    self.current_session = {
                        'session_id': self.session_id_counter + 1,
                        'start_time': activity['start_time'],
                        'end_time': activity['end_time'],
                        'activities': [activity],
                        'total_duration': activity['duration'],
                        'category': activity['category']
                    }
                    self.session_id_counter += 1
                    return completed_session
        else:
            # End current session if it was productive and long enough
            if self.current_session and self._is_productive_activity(self.current_session['activities'][0]):
                return self._finalize_session()

        return None

    def _finalize_session(self) -> Optional[Dict]:
        """Finalize current session and return it if it meets threshold"""
        if (self.current_session and
                self.current_session['total_duration'] >= self.session_threshold):
            completed_session = self.current_session.copy()
            self.sessions.append(completed_session)
            self.current_session = None
            return completed_session
        self.current_session = None
        return None

    def get_focus_metrics(self) -> Dict[str, Any]:
        """Get focus session metrics"""
        if not self.sessions:
            return {
                'total_focus_sessions': 0,
                'total_focus_minutes': 0,
                'avg_session_minutes': 0,
                'longest_session_minutes': 0,
                'focus_efficiency': 0
            }

        total_focus_time = sum(s['total_duration'] for s in self.sessions)
        avg_session_length = total_focus_time / len(self.sessions)
        longest_session = max(s['total_duration'] for s in self.sessions)

        # Calculate focus efficiency (longer sessions are more efficient)
        max_possible_session = 3600  # 1 hour
        focus_efficiency = min(100, (avg_session_length / max_possible_session) * 100)

        return {
            'total_focus_sessions': len(self.sessions),
            'total_focus_minutes': total_focus_time / 60,
            'avg_session_minutes': avg_session_length / 60,
            'longest_session_minutes': longest_session / 60,
            'focus_efficiency': round(focus_efficiency, 1)
        }


class BrowserActivityTracker:
    """
    Enhanced browser activity tracker with deep context analysis and focus tracking
    """

    def __init__(self, database_manager=None, port=3000, llm_client=None):
        self.db = database_manager
        self.llm_client = llm_client
        self.logger = self._setup_logging()
        self.is_running = False
        self.server_thread = None
        self.port = port

        # Enhanced browser activity classification rules
        self.browser_rules = {
            'productive': [
                # Development & Learning
                'github.com', 'gitlab.com', 'stackoverflow.com', 'stackexchange.com',
                'docs.python.org', 'docs.microsoft.com', 'developer.mozilla.org',
                'w3schools.com', 'freecodecamp.org', 'codecademy.com', 'udemy.com',
                'coursera.org', 'edx.org', 'khanacademy.org', 'pluralsight.com',
                'leetcode.com', 'hackerrank.com', 'codewars.com', 'exercism.org',
                # Professional
                'linkedin.com', 'meet.google.com', 'teams.microsoft.com',
                'webex.com', 'zoom.us', 'slack.com', 'jira.com', 'trello.com',
                'notion.so', 'confluence.com', 'figma.com', 'miro.com',
                # Documentation & Research
                'arxiv.org', 'researchgate.net', 'scholar.google.com',
                'jstor.org', 'ieee.org', 'acm.org', 'springer.com', 'sciencedirect.com'
            ],
            'learning': [
                'youtube.com/watch', 'youtube.com/playlist', 'ted.com/talks',
                'khanacademy.org', 'brilliant.org', 'quizlet.com', 'duolingo.com',
                'memrise.com', 'skillshare.com', 'udacity.com', 'datacamp.com',
                'lynda.com', 'futurelearn.com', 'mit.edu/opencourseware'
            ],
            'research': [
                'wikipedia.org', 'researchgate.net', 'academia.edu',
                'scholar.google.com', 'ieeexplore.ieee.org', 'dl.acm.org',
                'springerlink.com', 'sciencedirect.com', 'pubmed.ncbi.nlm.nih.gov',
                'arxiv.org', 'ssrn.com', 'jstor.org'
            ],
            'communication': [
                'mail.google.com', 'outlook.live.com', 'yahoo.com/mail',
                'protonmail.com', 'discord.com', 'web.whatsapp.com',
                'telegram.org', 'signal.org', 'messenger.com',
                'facebook.com/messages', 'twitter.com/messages',
                'slack.com', 'teams.microsoft.com'
            ],
            'entertainment': [
                'youtube.com', 'netflix.com', 'twitch.tv', 'hulu.com',
                'disneyplus.com', 'primevideo.com', 'hbomax.com',
                'spotify.com', 'soundcloud.com', 'pandora.com',
                'facebook.com', 'instagram.com', 'twitter.com',
                'tiktok.com', 'reddit.com', 'pinterest.com',
                '9gag.com', 'buzzfeed.com', 'imgur.com', 'memes.com'
            ],
            'shopping': [
                'amazon.com', 'ebay.com', 'walmart.com', 'target.com',
                'bestbuy.com', 'aliexpress.com', 'etsy.com',
                'flipkart.com', 'myntra.com', 'ajio.com'
            ],
            'news': [
                'news.google.com', 'bbc.com/news', 'cnn.com', 'reuters.com',
                'apnews.com', 'theguardian.com', 'nytimes.com',
                'washingtonpost.com', 'foxnews.com', 'aljazeera.com'
            ],
            'neutral': [
                'google.com/search', 'bing.com/search', 'duckduckgo.com',
                'weather.com', 'maps.google.com', 'calendar.google.com',
                'drive.google.com', 'dropbox.com', 'onedrive.live.com'
            ]
        }

        # Focus session tracking
        self.focus_tracker = FocusSessionTracker()

        # Activity history for pattern detection
        self.activity_history = deque(maxlen=100)
        self.distraction_patterns = defaultdict(int)

        # Initialize Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'productivity_tracker_secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        self.setup_routes()
        self.logger.info(f"Enhanced browser tracker initialized on port {self.port}")

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('browser_tracking.log', mode='a', encoding='utf-8')
            ]
        )
        return logging.getLogger(__name__)

    def setup_routes(self):
        """Setup Flask routes for browser extension communication"""

        @self.app.route('/api/browser-activity', methods=['POST'])
        def handle_browser_activity():
            """Receive browser activity data from extension"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': 'No JSON data'}), 400

                self.logger.info(f"Received browser activity: {data.get('url', 'Unknown')}")

                # Process and save the activity
                success = self.process_browser_activity(data)

                if success:
                    return jsonify({'status': 'success', 'message': 'Activity recorded'})
                else:
                    return jsonify({'status': 'error', 'message': 'Failed to process activity'}), 500

            except Exception as e:
                self.logger.error(f"Error processing browser activity: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'service': 'browser_tracker',
                'timestamp': datetime.now().isoformat(),
                'features': ['deep_context_analysis', 'focus_tracking', 'pattern_detection']
            })

        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            """Get browser tracking statistics"""
            stats = self.get_tracking_stats()
            return jsonify(stats)

        @self.app.route('/api/focus-metrics', methods=['GET'])
        def get_focus_metrics():
            """Get focus session metrics"""
            metrics = self.focus_tracker.get_focus_metrics()
            return jsonify(metrics)

    def analyze_browser_content_deep(self, url: str, title: str) -> Dict[str, Any]:
        """Deep analysis of browser content with enhanced context detection"""
        analysis = {
            'content_type': 'unknown',
            'learning_intent': False,
            'work_related': False,
            'time_sensitive': False,
            'complexity_level': 'medium',
            'confidence': 0.7,
            'keywords_found': []
        }

        url_lower = url.lower()
        title_lower = title.lower()
        combined_text = f"{url_lower} {title_lower}"

        # YouTube content analysis
        if 'youtube.com/watch' in url_lower:
            # Analyze video title for educational content
            edu_keywords = ['tutorial', 'course', 'lecture', 'how to', 'guide', 'educational',
                            'learning', 'explained', 'step by step', 'beginner', 'advanced']
            entertainment_keywords = ['music', 'funny', 'comedy', 'vlog', 'prank', 'memes',
                                      'gaming', 'stream', 'react', 'challenge']

            edu_score = sum(1 for kw in edu_keywords if kw in title_lower)
            ent_score = sum(1 for kw in entertainment_keywords if kw in title_lower)

            if edu_score > ent_score:
                analysis.update({
                    'content_type': 'educational_video',
                    'learning_intent': True,
                    'work_related': edu_score > 2,
                    'complexity_level': 'beginner' if 'beginner' in title_lower else 'advanced',
                    'confidence': min(0.9, 0.7 + (edu_score * 0.1))
                })
                analysis['keywords_found'].extend([kw for kw in edu_keywords if kw in title_lower])
            else:
                analysis.update({
                    'content_type': 'entertainment_video',
                    'learning_intent': False,
                    'confidence': min(0.9, 0.7 + (ent_score * 0.1))
                })

        # GitHub analysis
        elif 'github.com' in url_lower:
            if '/issues/' in url_lower or '/pull/' in url_lower:
                analysis.update({
                    'content_type': 'development_collaboration',
                    'work_related': True,
                    'time_sensitive': True,
                    'confidence': 0.85
                })
            elif '/blob/' in url_lower or any(ext in url_lower for ext in ['.py', '.js', '.java', '.cpp', '.ts']):
                analysis.update({
                    'content_type': 'code_review',
                    'work_related': True,
                    'complexity_level': 'high',
                    'confidence': 0.8
                })
            elif '/search' in url_lower or any(kw in combined_text for kw in ['documentation', 'wiki', 'readme']):
                analysis.update({
                    'content_type': 'technical_research',
                    'work_related': True,
                    'learning_intent': True,
                    'confidence': 0.75
                })
            else:
                analysis.update({
                    'content_type': 'development_platform',
                    'work_related': True,
                    'confidence': 0.7
                })

        # Stack Overflow & Documentation
        elif any(site in url_lower for site in ['stackoverflow.com', 'stackexchange.com', 'docs.python.org']):
            analysis.update({
                'content_type': 'problem_solving',
                'work_related': True,
                'learning_intent': True,
                'time_sensitive': 'error' in title_lower or 'issue' in title_lower,
                'confidence': 0.8
            })

        # Learning Platforms
        elif any(site in url_lower for site in ['udemy.com', 'coursera.org', 'edx.org', 'khanacademy.org']):
            analysis.update({
                'content_type': 'structured_learning',
                'learning_intent': True,
                'work_related': True,
                'confidence': 0.9
            })

        return analysis

    def classify_browser_activity(self, url: str, title: str = "") -> tuple[str, int, Dict[str, Any]]:
        """Enhanced browser activity classification with deep context analysis"""
        url_lower = url.lower()
        title_lower = title.lower()

        # Deep content analysis
        content_analysis = self.analyze_browser_content_deep(url, title)

        # Check each category with enhanced domain matching
        for category, domains in self.browser_rules.items():
            for domain in domains:
                if domain in url_lower:
                    base_score = self.get_browser_productivity_score(category)

                    # Adjust score based on content analysis
                    adjusted_score = self.calculate_dynamic_score(
                        category, content_analysis, base_score
                    )

                    self.logger.debug(f"Classified {url} as {category} (score: {adjusted_score})")
                    return category, adjusted_score, content_analysis

        # Check page title for additional context with enhanced matching
        for category, domains in self.browser_rules.items():
            for domain in domains:
                domain_keywords = domain.split('.')[0]  # Get main domain keyword
                if (domain_keywords in title_lower and len(domain_keywords) > 2):
                    base_score = self.get_browser_productivity_score(category)
                    adjusted_score = self.calculate_dynamic_score(
                        category, content_analysis, base_score
                    )
                    self.logger.debug(f"Classified by title {title} as {category} (score: {adjusted_score})")
                    return category, adjusted_score, content_analysis

        # Use content analysis for default classification
        if content_analysis['learning_intent']:
            return 'learning', 75, content_analysis
        elif content_analysis['work_related']:
            return 'productive', 70, content_analysis

        # Default classification with content context
        self.logger.debug(f"Classified {url} as neutral (default)")
        return 'neutral', 50, content_analysis

    def get_browser_productivity_score(self, category: str) -> int:
        """Get base productivity score for browser activity category"""
        scores = {
            'productive': 85,
            'learning': 80,
            'research': 75,
            'communication': 65,
            'news': 60,
            'neutral': 50,
            'shopping': 30,
            'entertainment': 25
        }
        return scores.get(category, 50)

    def calculate_dynamic_score(self, category: str, context: Dict, base_score: int) -> int:
        """Calculate dynamic productivity score based on multiple factors"""
        adjustments = 0

        # Content-based adjustments
        if context.get('learning_intent'):
            adjustments += 10
        if context.get('work_related'):
            adjustments += 15
        if context.get('time_sensitive'):
            adjustments += 5

        # Complexity adjustments
        if context.get('complexity_level') == 'high':
            adjustments += 10
        elif context.get('complexity_level') == 'beginner':
            adjustments += 5

        # Confidence-based adjustments
        confidence = context.get('confidence', 0.7)
        adjustments += int((confidence - 0.7) * 20)  # ±6 points based on confidence

        # Time of day adjustment
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17 and category in ['productive', 'learning']:
            adjustments += 5  # Bonus during work hours
        elif 22 <= current_hour <= 6 and category in ['entertainment']:
            adjustments -= 10  # Penalty late at night

        final_score = max(0, min(100, base_score + adjustments))
        return final_score

    def process_browser_activity(self, activity_data: Dict[str, Any]) -> bool:
        """Enhanced browser activity processing with focus tracking"""
        try:
            url = activity_data.get('url', '')
            title = activity_data.get('title', '')
            tab_id = activity_data.get('tabId')
            timestamp = activity_data.get('timestamp', datetime.now().isoformat())
            duration = activity_data.get('duration', 0)

            # Enhanced classification with deep context analysis
            category, score, content_analysis = self.classify_browser_activity(url, title)

            # Extract domain from URL
            if HAS_URLPARSE:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace('www.', '')
            else:
                # Fallback domain extraction
                domain = url.split('//')[-1].split('/')[0].replace('www.', '')

            # Create enhanced activity record
            browser_activity = {
                'app_name': f'browser:{domain}',
                'window_title': title[:200],
                'category': category,
                'productivity_score': score,
                'start_time': datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
                'end_time': datetime.now(),
                'duration': duration,
                'url': url,
                'domain': domain,
                'tab_id': tab_id,
                'tags': ['browser', category, domain],
                'content_analysis': content_analysis,
                'metadata': {
                    'time_of_day': datetime.now().hour,
                    'day_of_week': datetime.now().weekday(),
                    'confidence': content_analysis.get('confidence', 0.7),
                    'content_type': content_analysis.get('content_type', 'unknown')
                }
            }

            # Add to activity history
            self.activity_history.append(browser_activity)

            # Update focus session tracking
            completed_session = self.focus_tracker.update_session(browser_activity)
            if completed_session:
                self.logger.info(f"🎯 Focus session completed: {completed_session['category']} "
                                 f"for {completed_session['total_duration']}s")

            # Check for distraction patterns
            self._check_distraction_patterns(browser_activity)

            # Save to database if available
            if self.db:
                activity_id = self.db.insert_activity(browser_activity)
                self.logger.info(f"💾 Saved enhanced browser activity: {domain} -> {category} "
                                 f"(score: {score}, confidence: {content_analysis['confidence']:.2f})")
                return True
            else:
                self.logger.info(f"🌐 Browser activity: {domain} -> {category} "
                                 f"(score: {score}, context: {content_analysis['content_type']})")
                return True

        except Exception as e:
            self.logger.error(f"Error processing browser activity: {e}")
            return False

    def _check_distraction_patterns(self, activity: Dict):
        """Check for distraction patterns and trigger alerts if needed"""
        if activity['productivity_score'] < 40:  # Unproductive activity
            domain = activity['domain']
            self.distraction_patterns[domain] += 1

            # Check if this domain is becoming a frequent distraction
            if self.distraction_patterns[domain] >= 3:  # 3+ visits to same distracting site
                total_duration = sum(a['duration'] for a in self.activity_history
                                     if a.get('domain') == domain and a['productivity_score'] < 40)

                if total_duration > 900:  # 15 minutes total distraction time
                    self.logger.warning(f"🚨 Distraction pattern detected: {domain} "
                                        f"({self.distraction_patterns[domain]} visits, {total_duration}s)")
                    # Here you could trigger a notification to the user

    def start_server(self):
        """Start the Flask server in a separate thread"""

        def run_server():
            try:
                self.logger.info(f"Starting enhanced browser tracker server on port {self.port}")
                self.socketio.run(
                    self.app,
                    host='127.0.0.1',
                    port=self.port,
                    debug=False,
                    use_reloader=False,
                    allow_unsafe_werkzeug=True
                )
            except Exception as e:
                self.logger.error(f"Browser tracker server error: {e}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True

        # Wait a moment for server to start
        time.sleep(2)

        # Test server connectivity
        if self.test_server_connection():
            self.logger.info(f"✅ Enhanced browser tracker server started successfully on port {self.port}")
            return True
        else:
            self.logger.error("❌ Browser tracker server failed to start")
            return False

    def test_server_connection(self) -> bool:
        """Test if the server is running and accessible"""
        if not HAS_REQUESTS:
            return True  # Skip test if requests not available

        try:
            response = requests.get(f'http://127.0.0.1:{self.port}/api/health', timeout=5)
            return response.status_code == 200
        except:
            return False

    def stop_server(self):
        """Stop the Flask server"""
        self.is_running = False
        self.logger.info("Enhanced browser tracker server stopped")

    def start(self):
        """Start browser tracking"""
        if self.is_running:
            self.logger.warning("Browser tracker is already running")
            return True

        return self.start_server()

    def stop(self):
        """Stop browser tracking"""
        self.stop_server()

    def get_tracking_stats(self) -> Dict[str, Any]:
        """Get enhanced browser tracking statistics"""
        if not self.db:
            return {"status": "Database not available"}

        try:
            # Get browser activities from database
            activities = self.db.get_activities()
            browser_activities = [a for a in activities if a.get('url')]

            if not browser_activities:
                return {
                    "status": "No browser activities tracked",
                    "total_activities": 0,
                    "domains_tracked": 0,
                    "features": ["deep_context_analysis", "focus_tracking"]
                }

            # Calculate enhanced stats
            total_duration = sum(a['duration'] for a in browser_activities)
            domains = set(a.get('domain', '') for a in browser_activities if a.get('domain'))

            # Enhanced category breakdown with content types
            category_time = {}
            content_types = {}

            for activity in browser_activities:
                category = activity['category']
                content_type = activity.get('content_analysis', {}).get('content_type', 'unknown')

                if category not in category_time:
                    category_time[category] = 0
                category_time[category] += activity['duration']

                if content_type not in content_types:
                    content_types[content_type] = 0
                content_types[content_type] += 1

            # Focus metrics
            focus_metrics = self.focus_tracker.get_focus_metrics()

            return {
                "status": "Active" if self.is_running else "Stopped",
                "total_activities": len(browser_activities),
                "total_duration_minutes": total_duration / 60,
                "domains_tracked": len(domains),
                "category_breakdown": category_time,
                "content_type_breakdown": content_types,
                "focus_metrics": focus_metrics,
                "top_domains": list(domains)[:10],
                "distraction_patterns": dict(self.distraction_patterns),
                "features": ["deep_context_analysis", "focus_tracking", "pattern_detection"]
            }

        except Exception as e:
            self.logger.error(f"Error getting browser stats: {e}")
            return {"status": f"Error: {str(e)}"}


# Mock for testing when dependencies are missing
class MockBrowserTracker:
    def __init__(self, *args, **kwargs):
        self.is_running = False
        print("⚠️  Using mock browser tracker (install: pip install flask flask-socketio)")

    def start(self):
        print("❌ Browser tracking not available - install required packages")
        return False

    def stop(self):
        pass

    def get_tracking_stats(self):
        return {"status": "Browser tracking not available"}


# Export appropriate class based on dependencies
try:
    from flask import Flask
    from flask_socketio import SocketIO

    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

if HAS_FLASK and HAS_REQUESTS:
    BrowserActivityTracker = BrowserActivityTracker
else:
    BrowserActivityTracker = MockBrowserTracker


def test_enhanced_browser_tracker():
    """Test the enhanced browser tracker"""
    print("🧪 Testing Enhanced Browser Tracker...")

    # Create a mock database for testing
    class MockDB:
        def __init__(self):
            self.activities = []

        def insert_activity(self, activity):
            self.activities.append(activity)
            return len(self.activities)

        def get_activities(self, limit=1000):
            return self.activities[:limit]

    tracker = BrowserActivityTracker(MockDB())

    # Test enhanced classification
    test_urls = [
        ("https://github.com/python/cpython", "Python Source Code - GitHub"),
        ("https://www.youtube.com/watch?v=python-tutorial", "Python Tutorial for Beginners"),
        ("https://www.youtube.com/watch?v=funny-cats", "Funny Cat Videos Compilation"),
        ("https://stackoverflow.com/questions/123", "Python Error: How to fix?"),
        ("https://web.whatsapp.com", "WhatsApp Web"),
        ("https://www.amazon.com/product", "Shopping - Amazon"),
        ("https://news.google.com", "Latest News"),
        ("https://docs.python.org/3/library/", "Python Standard Library"),
        ("https://leetcode.com/problems/two-sum", "Two Sum Problem - LeetCode"),
    ]

    print("\n🔍 Testing Enhanced URL Classification:")
    print("-" * 80)
    print(f"{'URL':50} {'Category':12} {'Score':5} {'Content Type':20} {'Confidence':10}")
    print("-" * 80)

    for url, title in test_urls:
        category, score, analysis = tracker.classify_browser_activity(url, title)
        content_type = analysis.get('content_type', 'unknown')
        confidence = analysis.get('confidence', 0)
        print(f"🌐 {url:48} -> {category:12} {score:5} {content_type:20} {confidence:.2f}")

    print("\n✅ Enhanced browser tracker test completed!")


if __name__ == "__main__":
    test_enhanced_browser_tracker()