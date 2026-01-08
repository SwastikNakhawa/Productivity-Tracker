import logging
import sys
import os
import time
import threading
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from collections import deque, defaultdict

# Windows API imports
try:
    import win32gui
    import win32process
    import psutil

    HAS_WINDOWS_API = True
    print("✅ Windows API modules loaded successfully")
except ImportError as e:
    HAS_WINDOWS_API = False
    print(f"⚠️  Windows API not available: {e}")
    print("   Run: pip install pywin32 psutil")


class MockDatabase:
    """Mock database for testing when real database isn't available"""

    def __init__(self):
        self.activities = []
        print("✅ Using mock database for testing")

    def insert_activity(self, activity_data):
        self.activities.append(activity_data)
        activity_id = len(self.activities)
        print(f"💾 Mock DB: Saved activity #{activity_id} - {activity_data['app_name']}")
        return activity_id

    def get_activities(self, limit=1000):
        return self.activities[:limit]

    def log_activity(self, activity_data):
        """Alias for insert_activity for compatibility"""
        return self.insert_activity(activity_data)


@dataclass
class WindowInfo:
    """Enhanced data class to store window information"""
    app_name: str
    window_title: str
    process_id: int
    executable_path: str
    category: str = "unknown"
    productivity_score: int = 50
    context_analysis: Dict[str, Any] = None


class FocusSessionTracker:
    """Track focused work sessions for window activities"""

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
                    'category': activity['category'],
                    'app_name': activity['app_name']
                }
            else:
                # Continue session - check if it's similar activity
                time_gap = (activity['start_time'] - self.current_session['end_time']).total_seconds()

                if (time_gap < 600 and  # Less than 10 minutes gap
                        activity['category'] == self.current_session['category'] and
                        activity['app_name'] == self.current_session['app_name']):
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
                        'category': activity['category'],
                        'app_name': activity['app_name']
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


class RealWindowsTracker:
    """
    Enhanced Windows API-based activity tracker with intelligent classification and focus tracking
    """

    def __init__(self, database_manager=None, llm_client=None):
        self.db = database_manager or MockDatabase()
        self.llm_client = llm_client
        self.logger = self._setup_logging()
        self.is_tracking = False
        self.tracking_thread = None
        self._stop_event = threading.Event()

        # Track current and previous window
        self.current_window: Optional[WindowInfo] = None
        self.previous_window: Optional[WindowInfo] = None
        self.window_start_time: Optional[datetime] = None

        # Activity buffer to filter short activities
        self.activity_buffer = []
        self.min_duration = 5  # Minimum duration in seconds to save activity

        # Focus session tracking
        self.focus_tracker = FocusSessionTracker()

        # NEW: Enhanced activity history for UI display and pattern analysis
        self.activity_history = deque(maxlen=100)
        self.switch_patterns = defaultdict(int)

        # Enhanced productivity classification rules
        self.productivity_rules = {
            'productive': [
                # Development IDEs & Tools
                'vscode', 'visual studio', 'pycharm', 'intellij', 'sublime', 'webstorm', 'rider',
                'android studio', 'code.exe', 'devenv.exe', 'pycharm64.exe', 'notepad++', 'npp.exe',
                'cmd', 'powershell', 'terminal', 'windows terminal', 'wt.exe', 'git', 'github desktop',
                'postman', 'dbeaver', 'mysql', 'pgadmin', 'docker', 'wsl', 'ubuntu', 'putty',

                # Programming file extensions in window titles
                '.py', '.js', '.ts', '.java', '.cpp', '.c', '.html', '.css', '.sql', '.json',
                '.xml', '.yaml', '.md', '.rb', '.php', '.go', '.rs', '.swift', '.kt',

                # Development contexts
                'debug', 'test', 'spec.', 'main.', 'app.', 'src/', 'build', 'compile',
                'visual studio code', 'pycharm', 'intellij', 'sublime text', 'atom'
            ],
            'learning': [
                # Learning platforms
                'coursera', 'udemy', 'khan academy', 'edx', 'pluralsight', 'codecademy',
                'freecodecamp', 'datacamp', 'linkedin learning', 'skillshare', 'udacity',

                # Documentation & Tutorials
                'tutorial', 'course', 'learning', 'study', 'lecture', 'documentation',
                'how to', 'getting started', 'examples', 'sample code', 'guide', 'manual',
                'stackoverflow', 'github.com', 'gitlab.com', 'docs.microsoft.com', 'developer.',
                'w3schools', 'mdn web docs', 'readthedocs', 'java docs', 'python docs'
            ],
            'research': [
                'wikipedia', 'research', 'paper', 'academic', 'scholar', 'journal',
                'arxiv', 'researchgate', 'google scholar', 'ieee', 'springer',
                'thesis', 'dissertation', 'analysis of', 'survey of', 'study on'
            ],
            'design': [
                'figma', 'adobe photoshop', 'illustrator', 'premiere', 'after effects',
                'blender', 'maya', '3ds max', 'sketch', 'invision', 'canva', 'gimp',
                'affinity designer', 'coreldraw', 'lightroom', 'premiere pro'
            ],
            'communication': [
                'slack', 'discord', 'teams', 'whatsapp', 'telegram', 'signal', 'skype',
                'zoom', 'meet', 'outlook', 'thunderbird', 'gmail', 'mail', 'calendar',
                'messages', 'chat', 'conference', 'meeting', 'webex', 'gotomeeting'
            ],
            'entertainment': [
                # Video & Music
                'youtube', 'netflix', 'spotify', 'twitch', 'disney+', 'prime video', 'hulu',
                'tiktok', 'instagram', 'facebook', 'twitter', 'reddit', 'pinterest',
                'music', 'video', 'movie', 'stream', 'reels', 'shorts', 'tunes',

                # Games & Gaming
                'game', 'steam', 'epic games', 'origin', 'battle.net', 'minecraft',
                'fortnite', 'valorant', 'league of legends', 'overwatch', 'counter-strike',
                'xbox', 'playstation', 'nintendo', 'roblox', 'among us'
            ],
            'system': [
                # Windows System Processes
                'applicationframehost', 'runtimebroker', 'searchui', 'startmenuexperiencehost',
                'systemsettings', 'task manager', 'control panel', 'settings', 'file explorer',
                'windows explorer', 'calculator', 'notepad', 'wordpad', 'system32',
                'svchost', 'winlogon', 'services', 'explorer', 'dwm', 'ctfmon'
            ],
            'neutral': [
                # Browsers (context will be analyzed separately)
                'chrome', 'firefox', 'edge', 'safari', 'browser',

                # Office & Productivity
                'word', 'excel', 'powerpoint', 'office', 'adobe reader', 'pdf',
                'onenote', 'notion', 'evernote', 'trello', 'jira', 'confluence',

                # File Management
                'explorer', 'file explorer', 'winrar', '7zip', 'winzip'
            ]
        }

        self.logger.info("Enhanced RealWindowsTracker with focus tracking initialized")

    # NEW: Enhanced methods for GUI integration and analytics
    def get_current_activity(self):
        """Get current activity for UI display"""
        if self.current_window:
            duration = int((datetime.now() - self.window_start_time).total_seconds()) if self.window_start_time else 0
            return {
                'app_name': self.current_window.app_name,
                'window_title': self.current_window.window_title,
                'category': self.current_window.category,
                'productivity_score': self.current_window.productivity_score,
                'duration': duration,
                'start_time': self.window_start_time,
                'end_time': datetime.now(),
                'context_analysis': self.current_window.context_analysis
            }
        return None

    def get_recent_activities(self, limit=20):
        """Get recent activities for UI display"""
        return list(self.activity_history)[-limit:]

    def get_todays_activities(self):
        """Get today's activities for analysis"""
        today = datetime.now().date()
        return [a for a in self.activity_history
                if a.get('start_time', datetime.now()).date() == today]

    def get_switch_frequency(self) -> Dict[str, Any]:
        """Calculate window switch frequency metrics"""
        if len(self.activity_history) < 2:
            return {'total_switches': 0, 'switches_per_hour': 0, 'avg_session_duration': 0}

        switches = len(self.activity_history) - 1
        total_time = (datetime.now() - self.activity_history[0]['start_time']).total_seconds() / 3600
        avg_duration = sum(a['duration'] for a in self.activity_history) / len(self.activity_history)

        return {
            'total_switches': switches,
            'switches_per_hour': switches / total_time if total_time > 0 else 0,
            'avg_session_duration': avg_duration,
            'focus_score': max(0, 100 - (switches / total_time * 10)) if total_time > 0 else 100
        }

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('window_tracking.log', mode='a', encoding='utf-8')
            ]
        )
        return logging.getLogger(__name__)

    def get_active_window_info(self) -> Optional[WindowInfo]:
        """
        Get enhanced information about the currently active window using Windows API
        """
        if not HAS_WINDOWS_API:
            return None

        try:
            # Get the foreground window
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or not win32gui.IsWindowVisible(hwnd):
                return None

            # Get window title
            window_title = win32gui.GetWindowText(hwnd)

            # Get process ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # Get process information
            try:
                process = psutil.Process(pid)
                app_name = process.name()
                executable_path = process.exe()

                # Create enhanced window info object
                window_info = WindowInfo(
                    app_name=app_name,
                    window_title=window_title,
                    process_id=pid,
                    executable_path=executable_path
                )

                # Enhanced classification with context analysis
                window_info.category, window_info.productivity_score, window_info.context_analysis = self.classify_activity(
                    {
                        'app_name': app_name,
                        'window_title': window_title
                    })

                return window_info

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process might have ended or we don't have access
                return None

        except Exception as e:
            self.logger.error(f"Error getting window info: {e}")
            return None

    def _analyze_deep_context(self, window_title: str, app_name: str) -> Dict[str, Any]:
        """Deep context analysis using multiple factors"""
        context = {
            'is_development': False,
            'is_meeting': False,
            'is_research': False,
            'is_learning': False,
            'is_entertainment': False,
            'complexity': 'medium',
            'urgency': 'low',
            'confidence': 0.7,
            'keywords_found': []
        }

        combined_text = f"{app_name} {window_title}".lower()

        # Development context analysis
        dev_patterns = [
            r'\b(debug|test|spec|build|compile|deploy|run|execute)\b',
            r'\.(py|js|ts|java|cpp|c|html|css|sql|json|xml|yaml|md|rb|php|go|rs|swift|kt)$',
            r'\b(main|app|src|lib|module|package|class|function|method)\b',
            r'\b(error|exception|bug|fix|issue|problem)\b',
            r'\b(git|commit|push|pull|merge|branch|fork)\b'
        ]

        # Meeting context
        meeting_patterns = [
            r'\b(meeting|call|conference|standup|retro|demo|presentation)\b',
            r'\b(review|planning|sprint|scrum|agile|team|collaboration)\b'
        ]

        # Research context
        research_patterns = [
            r'\b(research|paper|thesis|study|analysis|survey|experiment)\b',
            r'\b(documentation|tutorial|guide|manual|reference|help)\b'
        ]

        # Learning context
        learning_patterns = [
            r'\b(learn|tutorial|course|training|education|lesson)\b',
            r'\b(how to|guide|walkthrough|example|sample|beginner|advanced)\b'
        ]

        # Check patterns and update context
        for pattern in dev_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                context['is_development'] = True
                context['keywords_found'].append(pattern)
                context['confidence'] = min(0.95, context['confidence'] + 0.1)

        for pattern in meeting_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                context['is_meeting'] = True
                context['keywords_found'].append(pattern)
                context['urgency'] = 'medium'

        for pattern in research_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                context['is_research'] = True
                context['keywords_found'].append(pattern)
                context['complexity'] = 'high'

        for pattern in learning_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                context['is_learning'] = True
                context['keywords_found'].append(pattern)

        # Entertainment detection
        entertainment_keywords = ['music', 'video', 'game', 'movie', 'stream', 'funny', 'comedy']
        if any(kw in combined_text for kw in entertainment_keywords):
            context['is_entertainment'] = True

        return context

    def classify_activity(self, window_info) -> tuple[str, int, Dict[str, Any]]:
        """Enhanced activity classification with deep context analysis"""
        app_name = window_info.get('app_name', '').lower()
        window_title = window_info.get('window_title', '').lower()

        # Deep context analysis
        context_analysis = self._analyze_deep_context(window_title, app_name)

        # First, check for system processes that should be ignored or classified as system
        system_keywords = ['applicationframehost', 'runtimebroker', 'searchui', 'startmenuexperiencehost']
        if any(sys_keyword in app_name for sys_keyword in system_keywords):
            return 'system', 10, context_analysis  # Very low score for system processes

        # Enhanced window title context analysis
        title_context = self._analyze_window_title_context(window_title, context_analysis)
        if title_context:
            return title_context

        # Enhanced app context analysis
        app_context = self._analyze_app_context(app_name, window_title, context_analysis)
        if app_context:
            return app_context

        # Use context analysis for default classification
        if context_analysis['is_development']:
            return 'productive', 85, context_analysis
        elif context_analysis['is_learning']:
            return 'learning', 80, context_analysis
        elif context_analysis['is_research']:
            return 'research', 75, context_analysis

        # Default classification with context
        return 'neutral', 50, context_analysis

    def _analyze_window_title_context(self, window_title: str, context_analysis: Dict) -> Optional[
        tuple[str, int, Dict]]:
        """Enhanced window title context analysis"""
        if not window_title or window_title == '':
            return None

        window_lower = window_title.lower()

        # Programming and development context with enhanced patterns
        dev_keywords = {
            'productive': [
                '.py', '.js', '.ts', '.java', '.cpp', '.c', '.html', '.css', '.sql', '.json',
                '.xml', '.yaml', '.md', 'debug', 'test', 'spec.', 'main.', 'app.', 'src/',
                'visual studio code', 'pycharm', 'intellij', 'sublime text', 'debugging',
                'git commit', 'pull request', 'code review', 'branch', 'merge', 'feature',
                'bug', 'error', 'exception', 'stack trace', 'log', 'console'
            ],
            'learning': [
                'tutorial', 'course', 'learning', 'study', 'documentation', 'guide',
                'how to', 'getting started', 'examples', 'sample', 'walkthrough',
                'step by step', 'beginner', 'advanced', 'masterclass', 'workshop'
            ],
            'research': [
                'research', 'paper', 'thesis', 'dissertation', 'academic', 'study on',
                'analysis of', 'survey of', 'literature review', 'methodology', 'results'
            ]
        }

        for category, keywords in dev_keywords.items():
            for keyword in keywords:
                if keyword in window_lower:
                    base_score = self.get_productivity_score(category)
                    adjusted_score = self.calculate_dynamic_score(category, context_analysis, base_score)
                    context_analysis['classification_reason'] = f'title_keyword_{keyword}'
                    return category, adjusted_score, context_analysis

        return None

    def _analyze_app_context(self, app_name: str, window_title: str, context_analysis: Dict) -> Optional[
        tuple[str, int, Dict]]:
        """Enhanced app context analysis with dynamic scoring"""
        # Special cases for common apps with context
        special_cases = {
            'python.exe': self._classify_python_context(window_title, context_analysis),
            'pythonw.exe': self._classify_python_context(window_title, context_analysis),
            'chrome.exe': self._classify_browser_context(window_title, context_analysis),
            'msedge.exe': self._classify_browser_context(window_title, context_analysis),
            'firefox.exe': self._classify_browser_context(window_title, context_analysis),
            'code.exe': ('productive', 90, {**context_analysis, 'is_development': True}),  # VS Code
            'pycharm64.exe': ('productive', 95, {**context_analysis, 'is_development': True}),  # PyCharm
            'devenv.exe': ('productive', 92, {**context_analysis, 'is_development': True}),  # Visual Studio
        }

        if app_name in special_cases:
            return special_cases[app_name]

        # General classification using enhanced rules
        for category, keywords in self.productivity_rules.items():
            # Check app name
            if any(keyword in app_name for keyword in keywords):
                base_score = self.get_productivity_score(category)
                adjusted_score = self.calculate_dynamic_score(category, context_analysis, base_score)
                context_analysis['classification_reason'] = f'app_keyword_match'
                return category, adjusted_score, context_analysis

            # Check window title for additional context
            if any(keyword in window_title.lower() for keyword in keywords):
                base_score = self.get_productivity_score(category)
                adjusted_score = self.calculate_dynamic_score(category, context_analysis, base_score)
                context_analysis['classification_reason'] = f'title_keyword_match'
                return category, adjusted_score, context_analysis

        return None

    def _classify_python_context(self, window_title: str, context_analysis: Dict) -> tuple[str, int, Dict]:
        """Enhanced Python process classification"""
        window_lower = window_title.lower()

        # Python scripts with meaningful names are likely productive
        if any(ext in window_lower for ext in ['.py', 'python']):
            # Enhanced context detection
            if any(keyword in window_lower for keyword in ['script', 'app', 'main', 'test', 'debug', 'server', 'api']):
                context_analysis.update({'is_development': True, 'complexity': 'high'})
                return 'productive', 85, context_analysis
            elif any(keyword in window_lower for keyword in ['install', 'setup', 'package', 'pip', 'requirements']):
                context_analysis.update({'is_development': True, 'complexity': 'medium'})
                return 'productive', 70, context_analysis
            elif 'idle' in window_lower:
                context_analysis.update({'is_development': True, 'complexity': 'low'})
                return 'productive', 80, context_analysis  # Python IDLE
            else:
                context_analysis['classification_reason'] = 'python_process_unknown'
                return 'neutral', 60, context_analysis  # Unknown Python process

        context_analysis['classification_reason'] = 'python_generic'
        return 'neutral', 50, context_analysis

    def _classify_browser_context(self, window_title: str, context_analysis: Dict) -> tuple[str, int, Dict]:
        """Enhanced browser activity classification"""
        if not window_title:
            return 'neutral', 50, context_analysis

        window_lower = window_title.lower()

        # Productive websites
        productive_sites = [
            'github', 'stackoverflow', 'gitlab', 'docs.microsoft', 'developer.',
            'w3schools', 'mdn', 'freecodecamp', 'codecademy', 'leetcode',
            'coursera', 'udemy', 'edx', 'khan academy', 'pluralsight',
            'jira', 'trello', 'notion', 'confluence', 'figma', 'slack',
            'google docs', 'google sheets', 'google drive', 'onedrive',
            'calendar', 'gmail', 'outlook', 'teams'
        ]

        # Learning & Research
        learning_sites = [
            'wikipedia', 'researchgate', 'arxiv', 'google scholar', 'ieee',
            'springer', 'science direct', 'pubmed', 'academia.edu'
        ]

        # Entertainment websites
        entertainment_sites = [
            'youtube', 'netflix', 'twitch', 'tiktok', 'instagram', 'facebook',
            'twitter', 'reddit', 'pinterest', 'spotify', 'disney+', 'hulu',
            '9gag', 'memes', 'funny', 'gaming', 'netflix', 'crunchyroll'
        ]

        # Check for productive sites
        for site in productive_sites:
            if site in window_lower:
                # YouTube could be educational
                if 'youtube' in window_lower and any(
                        edu in window_lower for edu in ['tutorial', 'course', 'lecture', 'educational']):
                    context_analysis.update({'is_learning': True, 'content_type': 'educational_video'})
                    return 'learning', 75, context_analysis
                context_analysis.update({'is_development': True, 'work_related': True})
                return 'productive', 80, context_analysis

        # Check for learning sites
        for site in learning_sites:
            if site in window_lower:
                context_analysis.update({'is_learning': True, 'is_research': True})
                return 'learning', 85, context_analysis

        # Check for entertainment sites
        for site in entertainment_sites:
            if site in window_lower:
                context_analysis.update({'is_entertainment': True})
                return 'entertainment', 20, context_analysis

        # Default browser classification
        return 'neutral', 50, context_analysis

    def get_productivity_score(self, category):
        """Enhanced productivity scoring"""
        scores = {
            'productive': 90,
            'learning': 85,
            'research': 80,
            'design': 75,
            'communication': 65,
            'neutral': 50,
            'system': 10,
            'entertainment': 20
        }
        return scores.get(category, 50)

    def calculate_dynamic_score(self, category: str, context: Dict, base_score: int) -> int:
        """Calculate dynamic productivity score based on multiple factors"""
        adjustments = 0

        # Context-based adjustments
        if context.get('is_development'):
            adjustments += 10
        if context.get('is_meeting'):
            adjustments += 5
        if context.get('is_learning'):
            adjustments += 15
        if context.get('is_research'):
            adjustments += 10

        # Complexity adjustments
        if context.get('complexity') == 'high':
            adjustments += 10
        elif context.get('complexity') == 'low':
            adjustments -= 5

        # Urgency adjustments
        if context.get('urgency') == 'medium':
            adjustments += 5
        elif context.get('urgency') == 'high':
            adjustments += 10

        # Confidence-based adjustments
        confidence = context.get('confidence', 0.7)
        adjustments += int((confidence - 0.7) * 20)

        # Time of day adjustment
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17 and category in ['productive', 'learning']:
            adjustments += 5
        elif 22 <= current_hour <= 6 and category in ['entertainment']:
            adjustments -= 10

        final_score = max(0, min(100, base_score + adjustments))
        return final_score

    def has_window_changed(self, new_window: Optional[WindowInfo]) -> bool:
        """Enhanced window change detection"""
        if not self.current_window and new_window:
            return True

        if not new_window and self.current_window:
            return True

        if not self.current_window and not new_window:
            return False

        # Enhanced change detection with context awareness
        if (self.current_window.app_name != new_window.app_name or
                self._is_significant_title_change(self.current_window.window_title, new_window.window_title)):
            return True

        return False

    def _is_significant_title_change(self, old_title: str, new_title: str) -> bool:
        """Enhanced significant title change detection"""
        if old_title == new_title:
            return False

        if not old_title or not new_title:
            return True

        # Enhanced heuristic for document changes in same app
        common_indicators = [' - ', ' | ', ' — ', ' • ', ' : ']
        for indicator in common_indicators:
            if indicator in old_title and indicator in new_title:
                old_prefix = old_title.split(indicator)[0]
                new_prefix = new_title.split(indicator)[0]
                if old_prefix == new_prefix:
                    return False  # Same app, just different document/tab

        # Browser tab changes are significant
        if any(browser in old_title.lower() for browser in ['chrome', 'firefox', 'edge']):
            return True

        return True

    def save_activity(self, window_info: WindowInfo, start_time: datetime, end_time: datetime):
        """Enhanced activity saving with focus tracking"""
        duration = int((end_time - start_time).total_seconds())

        # Enhanced duration filtering
        if duration < self.min_duration:
            self.logger.debug(f"⏱️  Skipping short activity: {window_info.app_name} ({duration}s)")
            return None

        # Enhanced system process filtering
        if window_info.category == 'system' and duration < 10:
            self.logger.debug(f"⚙️  Skipping short system activity: {window_info.app_name}")
            return None

        # Create enhanced activity data with context
        activity_data = {
            'app_name': window_info.app_name,
            'window_title': window_info.window_title,
            'category': window_info.category,
            'productivity_score': window_info.productivity_score,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'process_id': window_info.process_id,
            'tags': ['enhanced_tracking', window_info.category],
            'context_analysis': window_info.context_analysis,
            'metadata': self._get_enhanced_metadata(window_info, duration)
        }

        # Add to activity history
        self.activity_history.append(activity_data)

        # Update focus session tracking
        completed_session = self.focus_tracker.update_session(activity_data)
        if completed_session:
            self.logger.info(f"🎯 Focus session completed: {completed_session['category']} "
                             f"for {completed_session['total_duration']}s")

        # Track window switches
        if self.previous_window:
            switch_key = f"{self.previous_window.app_name}→{window_info.app_name}"
            self.switch_patterns[switch_key] += 1

        # Save to database
        activity_id = self.db.log_activity(activity_data)
        self.logger.info(
            f"💾 Tracked {window_info.app_name} for {duration}s - {window_info.category} "
            f"(score: {window_info.productivity_score}, confidence: {window_info.context_analysis.get('confidence', 0.7):.2f})")

        return activity_id

    def _get_enhanced_metadata(self, window_info: WindowInfo, duration: int) -> Dict[str, Any]:
        """Get enhanced metadata for activity"""
        return {
            'time_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
            'duration_category': 'short' if duration < 300 else 'medium' if duration < 1800 else 'long',
            'complexity': window_info.context_analysis.get('complexity', 'medium'),
            'urgency': window_info.context_analysis.get('urgency', 'low'),
            'keywords_found': window_info.context_analysis.get('keywords_found', []),
            'classification_reason': window_info.context_analysis.get('classification_reason', 'default')
        }

    def tracking_loop(self):
        """Enhanced tracking loop with pattern detection"""
        self.logger.info("🎯 Starting enhanced window tracking loop with focus tracking")
        check_interval = 2  # Check every 2 seconds

        while not self._stop_event.is_set():
            try:
                # Get current active window
                current_window = self.get_active_window_info()

                if current_window and self.has_window_changed(current_window):
                    # Save previous activity
                    if self.current_window and self.window_start_time:
                        self.save_activity(
                            self.current_window,
                            self.window_start_time,
                            datetime.now()
                        )

                    # Start tracking new window
                    self.previous_window = self.current_window
                    self.current_window = current_window
                    self.window_start_time = datetime.now()

                    # Enhanced logging with context
                    if self.previous_window:
                        self.logger.info(
                            f"🔄 {self.previous_window.app_name} ({self.previous_window.category}) → "
                            f"{current_window.app_name} ({current_window.category}) "
                            f"[confidence: {current_window.context_analysis.get('confidence', 0.7):.2f}]"
                        )
                    else:
                        self.logger.info(
                            f"🎯 Started tracking: {current_window.app_name} ({current_window.category}) "
                            f"[confidence: {current_window.context_analysis.get('confidence', 0.7):.2f}]"
                        )

                # Wait before next check
                self._stop_event.wait(check_interval)

            except Exception as e:
                self.logger.error(f"Error in tracking loop: {e}")
                if not self._stop_event.is_set():
                    self._stop_event.wait(5)

    def start_tracking(self):
        """Start enhanced real-time window tracking"""
        if self.is_tracking:
            self.logger.warning("Tracking is already running")
            return False

        if not HAS_WINDOWS_API:
            self.logger.error("❌ Cannot start tracking - Windows API not available")
            return False

        # Reset stop event
        self._stop_event.clear()
        self.is_tracking = True

        # Start tracking thread
        self.tracking_thread = threading.Thread(target=self.tracking_loop, daemon=True)
        self.tracking_thread.start()

        self.logger.info("🏁 Enhanced window tracking with focus tracking STARTED")
        return True

    def stop_tracking(self):
        """Stop real-time window tracking gracefully"""
        if not self.is_tracking:
            return

        print("\n⏳ Stopping enhanced tracker...")
        self.is_tracking = False
        self._stop_event.set()

        # Save the current activity before stopping
        if self.current_window and self.window_start_time:
            self.save_activity(
                self.current_window,
                self.window_start_time,
                datetime.now()
            )

        # Wait for thread to finish
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=3.0)
            if self.tracking_thread.is_alive():
                print("⚠️  Tracking thread taking too long to stop, forcing exit...")

        self.logger.info("🛑 Enhanced window tracking STOPPED")
        print("✅ Enhanced tracker stopped successfully!")

    def get_tracking_stats(self) -> Dict[str, Any]:
        """Get enhanced tracking statistics"""
        activities = self.db.get_activities()

        if not activities:
            return {
                "status": "No activities tracked yet",
                "total_activities": 0,
                "total_tracked_time_minutes": 0,
                "productive_time_minutes": 0,
                "entertainment_time_minutes": 0,
                "current_window": "None",
                "productivity_ratio": 0,
                "focus_metrics": self.focus_tracker.get_focus_metrics(),
                "switch_metrics": self.get_switch_frequency()
            }

        total_duration = sum(a['duration'] for a in activities)
        productive_time = sum(a['duration'] for a in activities if a['category'] == 'productive')
        learning_time = sum(a['duration'] for a in activities if a['category'] == 'learning')
        entertainment_time = sum(a['duration'] for a in activities if a['category'] == 'entertainment')

        # Calculate productivity ratio (productive + learning time)
        productive_learning_time = productive_time + learning_time
        productivity_ratio = (productive_learning_time / total_duration * 100) if total_duration > 0 else 0

        return {
            "status": "Tracking active" if self.is_tracking else "Tracking stopped",
            "total_activities": len(activities),
            "total_tracked_time_minutes": total_duration / 60,
            "productive_time_minutes": productive_time / 60,
            "learning_time_minutes": learning_time / 60,
            "entertainment_time_minutes": entertainment_time / 60,
            "current_window": self.current_window.app_name if self.current_window else "None",
            "current_category": self.current_window.category if self.current_window else "None",
            "productivity_ratio": productivity_ratio,
            "focus_metrics": self.focus_tracker.get_focus_metrics(),
            "switch_metrics": self.get_switch_frequency(),
            "features": ["deep_context_analysis", "focus_tracking", "pattern_detection"]
        }

    def get_recent_activities_formatted(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Get recent activities with enhanced formatting for display"""
        activities = self.db.get_activities(limit=limit)
        formatted_activities = []

        for activity in activities:
            duration_min = activity['duration'] / 60

            # Skip very short activities in display
            if duration_min < 0.1:  # Less than 6 seconds
                continue

            # Enhanced emoji mapping based on score and category
            score = activity['productivity_score']
            category = activity['category']
            context = activity.get('context_analysis', {})

            if category == 'system':
                emoji = "⚙️"
            elif score >= 80:
                emoji = "🚀"
            elif score >= 70:
                emoji = "💪"
            elif score >= 60:
                emoji = "📚"
            elif score >= 40:
                emoji = "⚡"
            elif score >= 20:
                emoji = "💬"
            else:
                emoji = "🎮"

            # Create enhanced display name with context
            app_name = activity['app_name'][:15]
            window_title = activity.get('window_title', '')[:30]

            if window_title and window_title not in app_name and len(window_title) > 3:
                display_name = f"{app_name} - {window_title}"
            else:
                display_name = app_name

            # Add context indicators
            context_indicators = []
            if context.get('is_development'):
                context_indicators.append("🔧")
            if context.get('is_learning'):
                context_indicators.append("📖")
            if context.get('is_meeting'):
                context_indicators.append("👥")

            context_str = " ".join(context_indicators) if context_indicators else ""

            formatted_activities.append({
                'emoji': emoji,
                'display_name': display_name,
                'context_indicators': context_str,
                'duration_min': round(duration_min, 1),
                'category': category,
                'score': score,
                'confidence': context.get('confidence', 0.7),
                'raw_data': activity
            })

        return formatted_activities


def simple_input_stop():
    """Simple and reliable method - just wait for Enter key"""
    print("\n" + "=" * 60)
    print("🎯 ENHANCED Tracking is now ACTIVE!")
    print("📊 Features: Deep context analysis, Focus tracking, Pattern detection")
    print("🔍 Better classification with confidence scores")
    print("🎯 Focus session tracking for productive work")
    print("🛑 Switch back to this window and press Enter to stop tracking")
    print("=" * 60)
    input()
    return True


def main():
    """Main function with enhanced tracking demo"""
    print("🎯 ENHANCED WINDOWS ACTIVITY TRACKER")
    print("=" * 70)
    print("✨ Features: Deep context analysis, Focus tracking, Pattern detection")
    print("   Confidence scoring, Enhanced classification, Switch frequency analysis")

    if not HAS_WINDOWS_API:
        print("❌ Windows API not available. Please install required packages:")
        print("   pip install pywin32 psutil")
        if os.name == 'nt':
            input("Press Enter to exit...")
        return

    # Initialize enhanced tracker
    tracker = RealWindowsTracker()

    print("\n🔍 Testing Enhanced Window Detection:")
    print("-" * 70)

    # Test window detection
    print("Detecting current active window with deep context analysis...")
    window_info = tracker.get_active_window_info()

    if window_info:
        print(f"✅ Current Window: {window_info.app_name}")
        print(f"📝 Title: {window_info.window_title}")
        print(f"📊 Category: {window_info.category} (score: {window_info.productivity_score})")
        print(f"🔧 PID: {window_info.process_id}")
        print(f"🎯 Context: {window_info.context_analysis}")
        print(f"💡 Confidence: {window_info.context_analysis.get('confidence', 0.7):.2f}")

    else:
        print("❌ Could not detect current window")
        if os.name == 'nt':
            input("Press Enter to exit...")
        return

    # Enhanced demo with focus on new features
    print("\n🚀 Start enhanced real-time tracking with focus session detection?")
    response = input("Type 'yes' to start tracking, or anything else for demo: ").lower().strip()

    if response == 'yes':
        if tracker.start_tracking():
            print("\n✅ Enhanced tracker with focus tracking started successfully!")

            try:
                if simple_input_stop():
                    print("\n🛑 Stop signal received!")

            except KeyboardInterrupt:
                print("\n\n🛑 Ctrl+C detected - stopping tracker...")
            except Exception as e:
                print(f"\n\n❌ Error: {e}")

            finally:
                tracker.stop_tracking()

        # Show enhanced summary
        stats = tracker.get_tracking_stats()
        print("\n" + "=" * 70)
        print("📊 ENHANCED TRACKING SUMMARY:")
        print(f"Total Activities: {stats['total_activities']}")
        print(f"Total Tracked Time: {stats['total_tracked_time_minutes']:.1f} minutes")
        print(f"Productive Time: {stats['productive_time_minutes']:.1f} minutes")
        print(f"Learning Time: {stats['learning_time_minutes']:.1f} minutes")
        print(f"Entertainment Time: {stats['entertainment_time_minutes']:.1f} minutes")
        print(f"Overall Productivity: {stats['productivity_ratio']:.1f}%")

        # Focus metrics
        focus_metrics = stats['focus_metrics']
        print(f"🎯 Focus Sessions: {focus_metrics['total_focus_sessions']}")
        print(f"⏱️  Avg Focus Session: {focus_metrics['avg_session_minutes']:.1f} minutes")
        print(f"📈 Focus Efficiency: {focus_metrics['focus_efficiency']:.1f}%")

        # Switch metrics
        switch_metrics = stats['switch_metrics']
        print(f"🔄 Window Switches: {switch_metrics['total_switches']}")
        print(f"⚡ Switches per Hour: {switch_metrics['switches_per_hour']:.1f}")
        print(f"🎯 Focus Score: {switch_metrics['focus_score']:.1f}%")

        # Enhanced activity list
        activities = tracker.get_recent_activities_formatted(limit=20)
        if activities:
            print(f"\n📋 ENHANCED ACTIVITIES ({len(activities)} meaningful activities):")
            print("-" * 90)
            print(f"{'No.':3} {'':2} {'Application & Context':40} {'Time':6} {'Cat':8} {'Score':5} {'Conf':5}")
            print("-" * 90)
            for i, activity in enumerate(activities, 1):
                print(f"{i:2}. {activity['emoji']:2} {activity['display_name']:40} "
                      f"{activity['duration_min']:5.1f}m {activity['category']:8} "
                      f"{activity['score']:3} {activity['confidence']:.2f} {activity['context_indicators']}")

    else:
        # Enhanced demo mode
        print("\n🔍 Running in enhanced demo mode...")
        print("Switch to different windows to see deep context analysis (15 seconds):")

        tracked_windows = {}
        start_time = datetime.now()
        demo_duration = 15

        try:
            while (datetime.now() - start_time).total_seconds() < demo_duration:
                window_info = tracker.get_active_window_info()
                if window_info and window_info.app_name not in tracked_windows:
                    tracked_windows[window_info.app_name] = window_info
                    confidence = window_info.context_analysis.get('confidence', 0.7)

                    # Enhanced emoji based on context
                    if window_info.context_analysis.get('is_development'):
                        context_emoji = "🔧"
                    elif window_info.context_analysis.get('is_learning'):
                        context_emoji = "📖"
                    elif window_info.context_analysis.get('is_meeting'):
                        context_emoji = "👥"
                    else:
                        context_emoji = "⚡"

                    print(f"{context_emoji} {window_info.app_name:25} - {window_info.category:12} "
                          f"(score: {window_info.productivity_score:2}) "
                          f"[conf: {confidence:.2f}] - {window_info.window_title[:25]}")

                remaining = demo_duration - (datetime.now() - start_time).total_seconds()
                print(f"\r⏰ Time remaining: {remaining:5.1f}s | Windows detected: {len(tracked_windows)}",
                      end="", flush=True)
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Demo interrupted by user")

        print(f"\n\n📊 Enhanced demo completed - Detected {len(tracked_windows)} unique applications")

        if tracked_windows:
            print("\n📋 Detected Applications with Deep Context Analysis:")
            for i, (app_name, window_info) in enumerate(tracked_windows.items(), 1):
                confidence = window_info.context_analysis.get('confidence', 0.7)
                context_desc = []
                if window_info.context_analysis.get('is_development'):
                    context_desc.append("development")
                if window_info.context_analysis.get('is_learning'):
                    context_desc.append("learning")
                if window_info.context_analysis.get('is_meeting'):
                    context_desc.append("meeting")

                context_str = ", ".join(context_desc) if context_desc else "general"
                print(f"  {i}. {app_name:20} → {window_info.category:12} (score: {window_info.productivity_score:2}) "
                      f"[conf: {confidence:.2f}, context: {context_str}]")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()

    if os.name == 'nt':
        input("\nPress Enter to exit...")