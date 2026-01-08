import sys
import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List
import json

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# #region agent log helper (debug mode)
def _dbg_log(hypothesis_id: str, location: str, message: str, data: dict = None, run_id: str = "pre-fix"):
    """Lightweight debug logger that writes NDJSON to the debug log path."""
    try:
        payload = {
            "sessionId": "debug-session",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000)
        }
        with open(r"c:\Users\swast\Productivity Tracker\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
# #endregion

print("🚀 Starting Productivity Tracker...")

# Import LLM Client
try:
    from analysis.llm_integration import LocalLLMClient, DataBridge, diagnose_llm_issues

    print("✅ LocalLLMClient imported successfully")
except ImportError as e:
    print(f"❌ LocalLLMClient import error: {e}")


    # Create a simple fallback
    class LocalLLMClient:
        def __init__(self, *args, **kwargs):
            self.is_available = False
            self.model_name = "fallback"
            self.available_models = ["fallback"]

        def generate_motivational_quote(self, activity):
            quotes = [
                "Stay focused and keep making progress! 💪",
                "Every minute counts toward your goals! 🚀",
                "Consistency is the key to success! 🔑",
                "You're doing great - keep pushing forward! 🌟",
                "Small steps lead to big achievements! 🎯"
            ]
            import random
            return random.choice(quotes)

        def generate_study_recommendations(self, activities):
            return [
                "Practice consistently with daily learning sessions",
                "Build projects to apply your knowledge",
                "Join online communities for support and learning"
            ]

        def analyze_productivity_trend(self, activities):
            return {
                "insight": "Keep tracking to get personalized insights!",
                "productivity_score": 50,
                "activities_analyzed": len(activities),
                "status": "fallback"
            }

        def analyze_productivity_trend_enhanced(self, activities):
            return self.analyze_productivity_trend(activities)

        def generate_quick_feedback(self, current_activity, previous_activity=None):
            return "Keep up the good work! 🚀"

        def set_model(self, model_name):
            self.model_name = model_name
            return True

        def get_available_models(self):
            return ["fallback"]

        def test_connection(self):
            return {
                "status": "offline",
                "model": self.model_name,
                "message": "LLM not available"
            }

        def test_connection_detailed(self):
            return False

        def get_status(self):
            return {
                "available": False,
                "model": self.model_name,
                "available_models": self.available_models
            }


    class DataBridge:
        def __init__(self, *args, **kwargs):
            pass

        def prepare_analysis_context(self, activities):
            return "No data available"


    def diagnose_llm_issues():
        print("❌ LLM integration not available")

try:
    from database.db import DatabaseManager

    HAS_DATABASE = True
    print("✅ DatabaseManager imported successfully")
except ImportError as e:
    HAS_DATABASE = False
    print(f"❌ DatabaseManager import failed: {e}")

try:
    from trackers.window_tracker import RealWindowsTracker

    HAS_TRACKER = True
    print("✅ RealWindowsTracker imported successfully")
except ImportError as e:
    HAS_TRACKER = False
    print(f"❌ RealWindowsTracker import failed: {e}")

try:
    from notifications import show_notification

    HAS_NOTIFICATIONS = True
    print("✅ Notifications imported successfully")
except ImportError as e:
    HAS_NOTIFICATIONS = False
    print(f"❌ Notifications import failed: {e}")

# Import the learning system
try:
    from analysis.llm_learning_system import LLMLearningSystem

    HAS_LEARNING_SYSTEM = True
    print("✅ LLMLearningSystem imported successfully")
except ImportError as e:
    HAS_LEARNING_SYSTEM = False
    print(f"❌ LLMLearningSystem import failed: {e}")


class ProductivityAgent:
    def __init__(self, use_gui_tracker=False):
        """
        Args:
            use_gui_tracker: If True, won't create its own tracker (GUI will handle it)
        """
        self.setup_logging()

        # Initialize components
        self.db = self.setup_database()

        # Initialize LLM client with enhanced diagnostics
        print("🤖 Initializing LLM Client...")
        self.llm_client = LocalLLMClient()

        # Test LLM connection immediately
        llm_status = self.llm_client.test_connection_detailed()
        if llm_status:
            print("✅ LLM Client initialized successfully")
        else:
            print("⚠️ LLM Client initialized with limited functionality")

        self.logger.info(f"🤖 LLM Client initialized - Available: {self.llm_client.is_available}")

        # Initialize Data Bridge for LLM analysis
        self.data_bridge = DataBridge(self.db, self.llm_client)
        print("✅ Data Bridge initialized")

        # Initialize learning system if available
        if HAS_LEARNING_SYSTEM and self.db:
            self.llm_learning_system = LLMLearningSystem(self.db, self.llm_client)
            self.logger.info("🧠 LLM Learning System initialized")
        else:
            self.llm_learning_system = None
            self.logger.warning("LLM Learning System not available")

        # Only create tracker if not using GUI's tracker
        self.use_gui_tracker = use_gui_tracker
        if not use_gui_tracker:
            self.tracker = self.setup_tracker()
        else:
            self.tracker = None

        self.analysis_interval = 300  # 5 minutes
        self.running = True
        self.last_notification_time = None
        self.notification_cooldown = 600  # 10 minutes

        self.logger.info("Productivity Agent initialized")

        # Activity tracking
        self.current_activity = None
        self.previous_activity = None
        self.activity_history = []

        # LLM interaction tracking
        self.llm_interaction_count = 0
        self.last_llm_analysis = None
        self.llm_insights = []

        # Learning system state
        self.learning_cycle_count = 0
        self.last_learning_time = None

        # Debug counters
        self.activity_change_count = 0
        self.llm_call_count = 0

        # Enhanced tracking
        self.llm_success_count = 0
        self.llm_failure_count = 0

        # Goal tracking integration
        try:
            from utils.goal_tracker import GoalTracker
            self.goal_tracker = GoalTracker() if self.db else None
            if self.goal_tracker:
                self.logger.info("✅ Goal Tracker initialized")
        except ImportError:
            self.goal_tracker = None
            self.logger.warning("Goal Tracker not available")

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('productivity_agent.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        if HAS_DATABASE:
            try:
                db = DatabaseManager()
                self.logger.info("✅ Database setup completed")
                return db
            except Exception as e:
                self.logger.error(f"Database setup failed: {e}")
        else:
            self.logger.warning("Database not available - running in memory-only mode")
        return None

    def setup_tracker(self):
        if HAS_TRACKER:
            try:
                tracker = RealWindowsTracker(self.db)
                return tracker
            except Exception as e:
                self.logger.error(f"Tracker setup failed: {e}")
        return None

    def start_tracking(self):
        """Start activity tracking - only if we have our own tracker"""
        if self.tracker and hasattr(self.tracker, 'start_tracking'):
            try:
                success = self.tracker.start_tracking()
                if success:
                    self.logger.info("✅ Activity tracking started")
                    return True
            except Exception as e:
                self.logger.error(f"Failed to start tracking: {e}")
        elif self.use_gui_tracker:
            self.logger.info("✅ Using GUI's tracker")
            return True
        return False

    def start_smart_monitoring(self):
        """Start smart monitoring with ACTIVE LLM integration"""

        def monitoring_loop():
            self.logger.info("🔄 Starting SMART monitoring loop with LLM")
            last_analysis_time = datetime.now()

            while self.running:
                try:
                    # Only monitor if we have our own tracker
                    if self.tracker:
                        self.check_current_activity()
                        self.perform_periodic_analysis()
                        self.log_activity_to_database()

                        # Perform LLM analysis every 10 minutes if we have activities
                        current_time = datetime.now()
                        if (len(self.activity_history) >= 3 and
                                (current_time - last_analysis_time).seconds > 600):
                            self.perform_llm_analysis()
                            last_analysis_time = current_time
                        
                        # Check and update goals every 5 minutes
                        if self.goal_tracker and len(self.activity_history) > 0:
                            self.check_goals_progress()

                    else:
                        # If using GUI tracker, just sleep
                        time.sleep(10)
                except Exception as e:
                    self.logger.error(f"Monitoring loop error: {e}")
                    time.sleep(10)

            self.logger.info("🛑 Smart monitoring stopped")

        monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitor_thread.start()
        return monitor_thread

    def start_learning_cycle(self):
        """Start the periodic learning cycle for LLM improvement"""
        if not self.llm_learning_system:
            self.logger.warning("Learning system not available - skipping learning cycle")
            return None

        def learning_loop():
            self.logger.info("🧠 Starting LLM learning system...")

            # Wait a bit for initial data to accumulate
            time.sleep(60)

            while self.running:
                try:
                    self.learning_cycle_count += 1
                    self.logger.info(f"🔄 Running learning cycle #{self.learning_cycle_count}")

                    # Run learning analysis
                    self.llm_learning_system.analyze_and_learn()
                    self.last_learning_time = datetime.now()

                    self.logger.info(f"✅ Learning cycle #{self.learning_cycle_count} completed")

                    # Sleep for 6 hours between learning cycles
                    for _ in range(6 * 3600):
                        if not self.running:
                            break
                        time.sleep(1)

                except Exception as e:
                    self.logger.error(f"Learning loop error: {e}")
                    # Wait 1 hour on error before retrying
                    time.sleep(3600)

        learning_thread = threading.Thread(target=learning_loop, daemon=True)
        learning_thread.start()
        return learning_thread

    def log_activity_to_database(self):
        """Log current activity to database for learning"""
        if not self.db or not self.current_activity:
            return

        try:
            # Enhance activity data with additional context
            activity_data = self.current_activity.copy()
            activity_data['start_time'] = datetime.now() - timedelta(seconds=activity_data.get('duration', 0))
            activity_data['end_time'] = datetime.now()

            # Add tags based on category and productivity score
            tags = self._generate_activity_tags(activity_data)
            activity_data['tags'] = tags

            # Log to database
            activity_id = self.db.log_activity(activity_data)

            # If this is a significant activity, log LLM context
            if activity_id and activity_data.get('productivity_score', 50) >= 70:
                self._log_llm_context(activity_id, activity_data)

        except Exception as e:
            self.logger.error(f"Error logging activity to database: {e}")

    def _generate_activity_tags(self, activity: Dict) -> List[str]:
        """Generate tags for activity based on context"""
        tags = []

        # Productivity level tags
        score = activity.get('productivity_score', 50)
        if score >= 80:
            tags.extend(['high_productivity', 'focused'])
        elif score >= 60:
            tags.extend(['medium_productivity', 'productive'])
        elif score >= 40:
            tags.extend(['low_productivity', 'neutral'])
        else:
            tags.extend(['unproductive', 'distraction'])

        # Time-based tags
        current_hour = datetime.now().hour
        if 6 <= current_hour < 12:
            tags.append('morning')
        elif 12 <= current_hour < 18:
            tags.append('afternoon')
        elif 18 <= current_hour < 22:
            tags.append('evening')
        else:
            tags.append('night')

        # Category-based tags
        category = activity.get('category', 'unknown')
        tags.append(f'category_{category}')

        return tags

    def _log_llm_context(self, activity_id: int, activity: Dict):
        """Log context for LLM learning"""
        if not self.db:
            return

        context = {
            'current_activity': activity,
            'time_of_day': datetime.now().strftime("%H:%M"),
            'day_of_week': datetime.now().strftime("%A"),
            'recent_productivity': self.calculate_current_productivity(),
            'activity_history_count': len(self.activity_history)
        }

        # Store context for future LLM learning
        self.db.log_llm_interaction(
            activity_id=activity_id,
            prompt="activity_context",
            response="stored_for_learning",
            context=context
        )

    def perform_llm_analysis(self):
        """Perform active LLM analysis on current patterns - ENHANCED VERSION"""
        if not self.llm_client.is_available:
            self.logger.debug("LLM not available for analysis")
            return

        if len(self.activity_history) < 3:
            self.logger.debug(f"Not enough activities for analysis. Have: {len(self.activity_history)}, Need: 3")
            return

        try:
            self.logger.info(f"🧠 Starting LLM analysis with {len(self.activity_history)} activities")

            # Use enhanced analysis method
            analysis = self.llm_client.analyze_productivity_trend_enhanced(self.activity_history)

            # Track success/failure
            if analysis.get('status') == 'success':
                self.llm_success_count += 1
            else:
                self.llm_failure_count += 1

            # Store for GUI to display
            self.last_llm_analysis = datetime.now()
            self.llm_interaction_count += 1
            self.llm_call_count += 1

            # Store insight
            insight_data = {
                'timestamp': datetime.now().isoformat(),
                'insight': analysis.get('insight', ''),
                'score': analysis.get('productivity_score', 0),
                'activities_analyzed': len(self.activity_history),
                'model_used': analysis.get('model_used', 'unknown'),
                'status': analysis.get('status', 'unknown')
            }
            self.llm_insights.append(insight_data)
            self.llm_insights = self.llm_insights[-10:]  # Keep last 10 insights

            self.logger.info(f"💡 LLM Analysis completed - Score: {analysis.get('productivity_score', 0)}%")

            # Send notification for significant insights
            if (analysis.get('productivity_score', 0) < 40 and
                    len(self.activity_history) > 10 and
                    analysis.get('status') == 'success'):
                quote = self.llm_client.generate_motivational_quote(
                    self.current_activity or {}
                )
                self.show_notification(
                    "📈 Productivity Insight",
                    f"{analysis.get('insight', 'Consider focusing more on productive work')}\n\n{quote}"
                )

        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            self.llm_failure_count += 1

    def check_current_activity(self):
        """Check current activity and send SMART notifications with LLM"""
        if not self.tracker:
            return

        try:
            current_activity = self.tracker.get_current_activity()
            if current_activity:
                if current_activity != self.current_activity:
                    # Store previous activity
                    self.previous_activity = self.current_activity
                    self.current_activity = current_activity
                    self.activity_history.append(current_activity)
                    self.activity_change_count += 1

                    # Keep last 100 activities
                    self.activity_history = self.activity_history[-100:]

                    self.logger.debug(f"Activity changed to: {current_activity.get('app_name')}")

                    # Generate LLM feedback for activity transition
                    if self.llm_client.is_available and self.previous_activity:
                        try:
                            quick_feedback = self.llm_client.generate_quick_feedback(
                                current_activity, self.previous_activity
                            )
                            self.logger.debug(f"Activity transition feedback: {quick_feedback}")
                        except Exception as e:
                            self.logger.debug(f"Quick feedback generation failed: {e}")

                    # Check if we should send a notification
                    self.check_activity_notification(current_activity)

        except Exception as e:
            self.logger.error(f"Error checking current activity: {e}")

    def check_activity_notification(self, activity: dict):
        """Check if we should send SMART notifications with LLM"""
        if not activity:
            return

        # Check cooldown
        now = datetime.now()
        if (self.last_notification_time and
                (now - self.last_notification_time).seconds < self.notification_cooldown):
            return

        category = activity.get('category', 'unknown')
        score = activity.get('productivity_score', 50)
        app_name = activity.get('app_name', 'this app')

        # Send notification for very unproductive activities
        if score < 30:
            quote = self.llm_client.generate_motivational_quote(activity)

            # Log this interaction for learning
            if self.db:
                self._log_notification_feedback(activity, quote, 'unproductive_alert')

            self.show_notification(
                "⚠️ Stay Focused!",
                f"You're on {app_name} ({category})\n\n{quote}"
            )
            self.last_notification_time = now
            self.logger.info(f"Sent focus notification for {app_name}")

        # Send positive reinforcement for very productive activities
        elif score > 80:
            productive_activities = [
                act for act in self.activity_history
                if act.get('productivity_score', 0) > 60
            ]

            if productive_activities and self.llm_client.is_available:
                recommendations = self.llm_client.generate_study_recommendations(productive_activities)
                if recommendations:
                    rec_text = "\n• ".join(recommendations)

                    # Log this interaction for learning
                    if self.db:
                        self._log_notification_feedback(activity, '\n'.join(recommendations),
                                                        'productive_recommendation')

                    self.show_notification(
                        "🎯 Learning Opportunity!",
                        f"Great work on {app_name}!\n\nNext steps:\n• {rec_text}"
                    )
                    self.last_notification_time = now
                    self.logger.info(f"Sent learning recommendation for {app_name}")

    def _log_notification_feedback(self, activity: Dict, llm_response: str, notification_type: str):
        """Log notification interactions for LLM learning"""
        if not self.db:
            return

        context = {
            'notification_type': notification_type,
            'activity': activity,
            'user_response': 'implicit',
            'timestamp': datetime.now().isoformat()
        }

        # Log a placeholder activity for this notification context
        activity_data = {
            'app_name': 'ProductivityTracker',
            'window_title': f'Notification: {notification_type}',
            'category': 'system',
            'productivity_score': 100,
            'duration': 0,
            'start_time': datetime.now(),
            'tags': ['notification', notification_type]
        }

        activity_id = self.db.log_activity(activity_data)
        if activity_id:
            self.db.log_llm_interaction(
                activity_id=activity_id,
                prompt=f"Generate {notification_type}",
                response=llm_response,
                context=context
            )

    def perform_periodic_analysis(self):
        """Perform periodic productivity analysis - only if we have our own tracker"""
        if not self.tracker:
            return

        current_time = datetime.now()

        # Only analyze every 5 minutes
        if (self.last_notification_time and
                (current_time - self.last_notification_time).seconds < 300):
            return

        if len(self.activity_history) > 5:  # Only analyze if we have enough data
            productive_activities = [
                act for act in self.activity_history
                if act.get('productivity_score', 0) > 60
            ]
            unproductive_activities = [
                act for act in self.activity_history
                if act.get('productivity_score', 0) < 40
            ]

            productive_time = sum(act.get('duration', 0) for act in productive_activities)
            unproductive_time = sum(act.get('duration', 0) for act in unproductive_activities)
            total_time = productive_time + unproductive_time

            if total_time > 0:
                productivity_ratio = (productive_time / total_time) * 100

                if productivity_ratio < 40 and len(unproductive_activities) > 2:
                    quote = self.llm_client.generate_motivational_quote(
                        self.current_activity or {}
                    )
                    self.show_notification(
                        "📊 Productivity Check",
                        f"Productivity: {productivity_ratio:.0f}%\n\n{quote}"
                    )
                    self.last_notification_time = current_time

    def show_notification(self, title: str, message: str):
        """Show notification to user"""
        try:
            if HAS_NOTIFICATIONS:
                show_notification(title, message)
                self.logger.debug(f"Notification shown - {title}")
            else:
                # Fallback notification
                print(f"🔔 {title}: {message}")
        except Exception as e:
            self.logger.error(f"Notification failed: {e}")
            print(f"🔔 {title}: {message}")

    def get_current_status(self):
        """Get current status for GUI"""
        status = {
            'tracking_active': self.tracker and hasattr(self.tracker, 'is_tracking') and self.tracker.is_tracking,
            'llm_available': self.llm_client.is_available,
            'current_activity': self.current_activity,
            'activities_tracked': len(self.activity_history),
            'productivity_score': self.calculate_current_productivity(),
            'database_available': self.db is not None,
            'learning_system_available': self.llm_learning_system is not None,
            'learning_cycles_completed': self.learning_cycle_count,
            'last_learning_time': self.last_learning_time,
            'llm_interaction_count': self.llm_interaction_count,
            'last_llm_analysis': self.last_llm_analysis,
            'llm_insights': self.llm_insights[-3:] if self.llm_insights else [],
            'current_model': self.llm_client.model_name,
            'llm_stats': {
                'success_count': self.llm_success_count,
                'failure_count': self.llm_failure_count,
                'success_rate': (self.llm_success_count / (self.llm_success_count + self.llm_failure_count) * 100)
                if (self.llm_success_count + self.llm_failure_count) > 0 else 0
            },
            'debug_info': {
                'activity_changes': self.activity_change_count,
                'llm_calls': self.llm_call_count,
                'activity_history_size': len(self.activity_history)
            }
        }
        return status

    def get_learning_insights(self):
        """Get insights from the learning system"""
        if not self.llm_learning_system or not self.db:
            return {"error": "Learning system not available"}

        try:
            patterns = self.db.get_user_productivity_patterns(days=7)
            insights = {
                'weekly_patterns': patterns,
                'learning_cycles': self.learning_cycle_count,
                'last_learning': self.last_learning_time.isoformat() if self.last_learning_time else None
            }
            return insights
        except Exception as e:
            self.logger.error(f"Error getting learning insights: {e}")
            return {"error": str(e)}

    def calculate_current_productivity(self):
        """Calculate current productivity score"""
        if not self.activity_history:
            return 50

        productive_time = sum(
            act.get('duration', 0) for act in self.activity_history
            if act.get('productivity_score', 0) >= 60
        )
        total_time = sum(act.get('duration', 0) for act in self.activity_history)

        if total_time > 0:
            return min(100, (productive_time / total_time) * 100)
        return 50

    def provide_user_feedback(self, llm_interaction_id: int, feedback: int, corrected_response: str = None):
        """Allow user to provide feedback on LLM responses"""
        if not self.db:
            return False

        try:
            self.db.update_llm_feedback(llm_interaction_id, feedback, corrected_response)
            self.logger.info(f"User feedback recorded: {feedback}")
            return True
        except Exception as e:
            self.logger.error(f"Error recording user feedback: {e}")
            return False

    def get_personalized_recommendations(self):
        """Get personalized recommendations based on learned patterns"""
        if not self.llm_learning_system or not self.db:
            return ["Enable learning system to get personalized recommendations"]

        try:
            patterns = self.db.get_user_productivity_patterns(days=30)

            # Generate recommendations based on patterns
            productive_hours = []
            time_patterns = patterns.get('time_of_day_patterns', [])
            for pattern in time_patterns:
                if pattern.get('avg_score', 0) >= 70:
                    hour = int(pattern.get('hour', 0))
                    productive_hours.append(f"{hour:02d}:00")

            recommendations = []
            if productive_hours:
                recommendations.append(f"Your most productive hours are: {', '.join(productive_hours[:3])}")

            category_trends = patterns.get('category_trends', [])
            if category_trends:
                top_category = category_trends[0].get('category', 'unknown')
                recommendations.append(f"Focus on {top_category} work during productive hours")

            if not recommendations:
                recommendations = [
                    "Continue tracking to build personalized insights",
                    "The system is learning your productivity patterns",
                    "Check back later for customized recommendations"
                ]

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating personalized recommendations: {e}")
            return ["Error generating recommendations"]

    def get_llm_status(self):
        """Get detailed LLM status"""
        llm_status = self.llm_client.get_status() if hasattr(self.llm_client, 'get_status') else {}

        return {
            'available': self.llm_client.is_available,
            'interaction_count': self.llm_interaction_count,
            'last_analysis': self.last_llm_analysis,
            'model_used': self.llm_client.model_name,
            'insights_count': len(self.llm_insights),
            'available_models': self.llm_client.get_available_models() if hasattr(self.llm_client,
                                                                                  'get_available_models') else [],
            'success_rate': self.llm_success_count / (self.llm_success_count + self.llm_failure_count) * 100
            if (self.llm_success_count + self.llm_failure_count) > 0 else 0,
            'raw_status': llm_status,
            'debug_info': {
                'activity_changes': self.activity_change_count,
                'llm_calls': self.llm_call_count,
                'llm_success': self.llm_success_count,
                'llm_failure': self.llm_failure_count
            }
        }

    def test_llm_connection(self):
        """Test LLM connection and capabilities"""
        try:
            if hasattr(self.llm_client, 'test_connection_detailed'):
                result = self.llm_client.test_connection_detailed()
                return result
            else:
                # Fallback test for basic LLM client
                if not self.llm_client.is_available:
                    return {"status": "offline", "message": "LLM not available"}

                # Test motivational quote generation
                test_activity = {"app_name": "Test App", "category": "testing", "productivity_score": 75}
                quote = self.llm_client.generate_motivational_quote(test_activity)

                # Test recommendations
                recommendations = self.llm_client.generate_study_recommendations([test_activity])

                # Test analysis
                analysis = self.llm_client.analyze_productivity_trend([test_activity])

                return {
                    "status": "online",
                    "model": self.llm_client.model_name,
                    "test_quote": quote,
                    "test_recommendations": recommendations,
                    "test_analysis": analysis.get('insight', 'No analysis'),
                    "message": "LLM is working correctly!"
                }

        except Exception as e:
            return {"status": "error", "message": f"LLM test failed: {e}"}

    def change_llm_model(self, model_name: str) -> bool:
        """Change the LLM model"""
        try:
            if hasattr(self.llm_client, 'set_model'):
                success = self.llm_client.set_model(model_name)
                if success:
                    self.logger.info(f"✅ LLM model changed to: {model_name}")
                    # Update insights with new model info
                    for insight in self.llm_insights:
                        insight['model_used'] = model_name
                else:
                    self.logger.error(f"❌ Failed to change LLM model to: {model_name}")
                return success
            else:
                self.logger.warning("LLM client doesn't support model changes")
                return False
        except Exception as e:
            self.logger.error(f"Error changing LLM model: {e}")
            return False

    def generate_motivational_quote(self):
        """Generate a motivational quote on demand"""
        if not self.llm_client.is_available or not self.current_activity:
            return "LLM not available or no current activity"

        try:
            return self.llm_client.generate_motivational_quote(self.current_activity)
        except Exception as e:
            self.logger.error(f"Error generating motivational quote: {e}")
            return "Stay focused and keep making progress! 💪"

    def check_goals_progress(self):
        """Check and update goal progress"""
        if not self.goal_tracker or not self.db:
            return

        try:
            active_goals = self.goal_tracker.get_active_goals()
            if not active_goals:
                return

            # Get recent activities for goal evaluation
            activities = self.db.get_recent_activities(limit=100)
            if not activities:
                return

            for goal in active_goals:
                # Filter activities based on goal type
                goal_activities = activities
                if goal.get('goal_type') == 'daily':
                    today = datetime.now().date()
                    goal_activities = [a for a in activities 
                                     if hasattr(a.get('start_time'), 'date') and 
                                     a.get('start_time').date() == today]
                elif goal.get('goal_type') == 'weekly':
                    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
                    goal_activities = [a for a in activities 
                                     if hasattr(a.get('start_time'), 'date') and 
                                     a.get('start_time').date() >= week_start.date()]

                if goal_activities:
                    progress = self.goal_tracker.update_goal_progress(goal['id'], goal_activities)
                    
                    # Send notification if goal achieved
                    if progress.get('achieved') and not goal.get('achieved'):
                        self.show_notification(
                            "🎉 Goal Achieved!",
                            f"Congratulations! You achieved: {goal.get('description', 'your goal')}"
                        )
                        self.logger.info(f"🎯 Goal achieved: {goal.get('description')}")

        except Exception as e:
            self.logger.error(f"Error checking goals progress: {e}")

    def diagnose_llm_issues(self):
        """Run LLM diagnosis"""
        try:
            diagnose_llm_issues()
            return True
        except Exception as e:
            self.logger.error(f"Error running LLM diagnosis: {e}")
            return False

    def stop(self):
        """Stop the agent"""
        self.logger.info("🛑 Stopping Productivity Agent...")
        self.logger.info(
            f"📊 Final stats - Activity changes: {self.activity_change_count}, LLM calls: {self.llm_call_count}")
        self.logger.info(f"🤖 LLM Stats - Success: {self.llm_success_count}, Failure: {self.llm_failure_count}")
        self.running = False

        # Only stop tracking if we have our own tracker
        if self.tracker and hasattr(self.tracker, 'stop_tracking'):
            try:
                self.tracker.stop_tracking()
                self.logger.info("✅ Activity tracking stopped")
            except Exception as e:
                self.logger.error(f"Error stopping tracker: {e}")

        # Save final learning state
        if self.llm_learning_system:
            self.logger.info(f"🧠 Completed {self.learning_cycle_count} learning cycles")


def run_modern_gui():
    """Run the modern GUI"""
    try:
        _dbg_log("H1", "main_app.py:run_modern_gui", "enter_run_modern_gui",
                 {"cwd": os.getcwd(), "sys_path_sample": sys.path[:5]})
        print("🎨 Launching Modern GUI...")

        # Import the GUI
        from main_modern_gui import ModernProductivityTracker
        _dbg_log("H1", "main_app.py:run_modern_gui", "import_main_modern_gui_success", {})

        print("✅ Modern GUI imported successfully")

        # Create the GUI application
        app = ModernProductivityTracker()
        _dbg_log("H1", "main_app.py:run_modern_gui", "create_gui_success", {})
        print("✅ Modern GUI created successfully")

        # Run the GUI - this will block until the GUI is closed
        print("🚀 Starting GUI main loop...")
        app.run()

        return True

    except ImportError as e:
        _dbg_log("H1", "main_app.py:run_modern_gui", "import_error_modern_gui", {"error": str(e)})
        print(f"❌ Failed to import Modern GUI: {e}")
        print("💡 Make sure main_modern_gui.py is in the same directory")
        return False
    except Exception as e:
        _dbg_log("H2", "main_app.py:run_modern_gui", "generic_gui_error", {"error": str(e)})
        print(f"❌ GUI error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("🚀 AI Productivity Tracker - Enhanced Edition")
    print("=" * 60)

    # Run LLM diagnosis first
    print("🔍 Running LLM diagnostics...")
    diagnose_llm_issues()
    print("")

    # Create the agent BUT tell it NOT to create its own tracker
    # The GUI will handle the tracking
    agent = ProductivityAgent(use_gui_tracker=True)

    # Don't start tracking here - the GUI will handle it
    print("✅ Agent initialized (GUI will handle tracking)")

    # Start smart monitoring (but it won't do much since no tracker)
    monitor_thread = agent.start_smart_monitoring()
    print("✅ Background services: ACTIVE")

    # Start learning system if available
    if agent.llm_learning_system:
        learning_thread = agent.start_learning_cycle()
        print("✅ LLM Learning System: ACTIVE")
    else:
        print("⚠️ LLM Learning System: UNAVAILABLE")

    # Check LLM status
    if agent.llm_client.is_available:
        print("✅ Local LLM: CONNECTED")
        print(f"🤖 Using model: {agent.llm_client.model_name}")

        # Show available models
        if hasattr(agent.llm_client, 'get_available_models'):
            available_models = agent.llm_client.get_available_models()
            print(f"📚 Available models: {', '.join(available_models)}")
    else:
        print("⚠️ Local LLM: UNAVAILABLE (using fallbacks)")

    # Check database status
    if agent.db:
        print("✅ Database: CONNECTED")
    else:
        print("⚠️ Database: UNAVAILABLE (limited functionality)")

    print("🛑 Close the GUI window to stop the application")
    print("=" * 60)

    try:
        # Launch the modern GUI - this will handle everything
        print("🔄 Launching GUI...")
        gui_started = run_modern_gui()

        if not gui_started:
            print("💡 GUI failed to start")
            # If GUI fails, we could start our own tracking here
            # But for now, just exit

    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        agent.stop()
        print("✅ Application closed successfully")


if __name__ == "__main__":
    main()