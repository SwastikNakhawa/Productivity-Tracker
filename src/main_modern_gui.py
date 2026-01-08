# main_modern_gui.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import sys
import os
from datetime import datetime
import logging
import json
import time
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# FIXED: Add src directory to path for proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# #region agent log helper (debug mode)
def _dbg_log(hypothesis_id: str, location: str, message: str, data: dict = None, run_id: str = "pre-fix"):
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

print(f"🔧 Working directory: {current_dir}")
print(f"📦 Python path: {[p for p in sys.path if 'Productivity' in p]}")

# Try to import your existing modules
try:
    from analysis.llm_integration import LocalLLMClient

    HAS_LLM = True
    print("✅ LLM integration imported successfully")
    _dbg_log("H1", "main_modern_gui.py:imports", "llm_import_success", {})
except ImportError as e:
    HAS_LLM = False
    print(f"❌ LLM integration import failed: {e}")
    _dbg_log("H1", "main_modern_gui.py:imports", "llm_import_failed", {"error": str(e)})

try:
    from database.db import DatabaseManager

    HAS_DB = True
    print("✅ Database imported successfully")
    _dbg_log("H1", "main_modern_gui.py:imports", "db_import_success", {})
except ImportError as e:
    HAS_DB = False
    print(f"❌ Database import failed: {e}")
    _dbg_log("H1", "main_modern_gui.py:imports", "db_import_failed", {"error": str(e)})

try:
    from trackers.window_tracker import RealWindowsTracker

    HAS_TRACKER = True
    print("✅ Tracker imported successfully")
    _dbg_log("H1", "main_modern_gui.py:imports", "tracker_import_success", {})
except ImportError as e:
    HAS_TRACKER = False
    print(f"❌ Tracker import failed: {e}")
    _dbg_log("H1", "main_modern_gui.py:imports", "tracker_import_failed", {"error": str(e)})

try:
    from notifications import show_notification

    HAS_NOTIFICATIONS = True
    print("✅ Notifications imported successfully")
    _dbg_log("H1", "main_modern_gui.py:imports", "notifications_import_success", {})
except ImportError as e:
    HAS_NOTIFICATIONS = False
    print(f"❌ Notifications import failed: {e}")
    _dbg_log("H1", "main_modern_gui.py:imports", "notifications_import_failed", {"error": str(e)})

# Import the main app to get ProductivityAgent
try:
    from main_app import ProductivityAgent

    HAS_AGENT = True
    print("✅ ProductivityAgent imported successfully")
    _dbg_log("H1", "main_modern_gui.py:imports", "agent_import_success", {})
except ImportError as e:
    HAS_AGENT = False
    print(f"❌ ProductivityAgent import failed: {e}")
    _dbg_log("H1", "main_modern_gui.py:imports", "agent_import_failed", {"error": str(e)})

try:
    from ui.charts import create_charts

    HAS_CHARTS = True
    print("✅ Charts helper imported successfully")
    _dbg_log("H2", "main_modern_gui.py:imports", "charts_import_success", {})
except ImportError as e:
    HAS_CHARTS = False
    print(f"❌ Charts helper import failed: {e}")
    _dbg_log("H2", "main_modern_gui.py:imports", "charts_import_failed", {"error": str(e)})

try:
    from utils.goal_tracker import GoalTracker

    HAS_GOAL_TRACKER = True
    print("✅ Goal Tracker imported successfully")
    _dbg_log("H3", "main_modern_gui.py:imports", "goal_tracker_import_success", {})
except ImportError as e:
    HAS_GOAL_TRACKER = False
    print(f"❌ Goal Tracker import failed: {e}")
    _dbg_log("H3", "main_modern_gui.py:imports", "goal_tracker_import_failed", {"error": str(e)})

try:
    from utils.goal_tracker import GoalTracker

    HAS_GOAL_TRACKER = True
    print("✅ Goal Tracker imported successfully")
except ImportError as e:
    HAS_GOAL_TRACKER = False
    print(f"❌ Goal Tracker import failed: {e}")


class ModernProductivityTracker:
    def __init__(self):
        # Configure appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Create main window
        self.root = ctk.CTk()
        self.root.title("🚀 AI Productivity Tracker")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Set protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Initialize components
        self.agent = None
        self.setup_components()
        self.setup_gui()

        # UI state
        self.is_tracking = False
        self.current_activity = None
        self.activity_history = []
        self._last_logged_activity = None

        # Start background updates
        self.update_ui_loop()

    def setup_components(self):
        """Initialize all components with better LLM integration"""
        self.logger = self.setup_logging()

        # Initialize LLM Client FIRST (most important)
        self.llm_client = None
        if HAS_LLM:
            try:
                self.llm_client = LocalLLMClient()
                if self.llm_client.is_available:
                    self.logger.info("✅ LLM Client connected and ready!")
                else:
                    self.logger.warning("❌ LLM Client not available - Ollama may not be running")
            except Exception as e:
                self.logger.error(f"LLM Client failed: {e}")
                self.llm_client = None

        # Database
        self.db = None
        if HAS_DB:
            try:
                self.db = DatabaseManager()
                self.logger.info("✅ Database initialized")
            except Exception as e:
                self.logger.error(f"Database failed: {e}")
                self.db = None

        # Only now create agent (depends on LLM and DB)
        self.agent = None
        if HAS_AGENT and self.llm_client and self.db:
            try:
                self.agent = ProductivityAgent(use_gui_tracker=True)
                # Ensure agent uses our LLM client and database
                self.agent.llm_client = self.llm_client
                self.agent.db = self.db
                self.logger.info("✅ Productivity Agent initialized")
            except Exception as e:
                self.logger.error(f"Agent initialization failed: {e}")
                self.agent = None

        # Tracker
        self.tracker = None
        if HAS_TRACKER and self.db:
            try:
                self.tracker = RealWindowsTracker(self.db)
                self.logger.info("✅ Window tracker initialized")
            except Exception as e:
                self.logger.error(f"Tracker initialization failed: {e}")
                self.tracker = None

        # Goal Tracker
        self.goal_tracker = None
        if HAS_GOAL_TRACKER and self.db:
            try:
                self.goal_tracker = GoalTracker(self.db.db_path if hasattr(self.db, 'db_path') else "productivity_tracker.db")
                self.logger.info("✅ Goal Tracker initialized")
            except Exception as e:
                self.logger.error(f"Goal Tracker initialization failed: {e}")
                self.goal_tracker = None

        # Log final status
        status_msg = f"""
🎯 COMPONENT STATUS:
• LLM: {'✅ Available' if self.llm_client and self.llm_client.is_available else '❌ Unavailable'}
• Database: {'✅ Ready' if self.db else '❌ Failed'}
• Agent: {'✅ Active' if self.agent else '❌ Inactive'}
• Tracker: {'✅ Ready' if self.tracker else '❌ Failed'}
"""
        self.logger.info(status_msg)
        print(status_msg)

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('gui_productivity_tracker.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def setup_gui(self):
        """Setup the modern GUI with tabs"""
        # Create main grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create tab view
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Create tabs
        self.tabview.add("🏠 Dashboard")
        self.tabview.add("📊 Real-time Tracking")
        self.tabview.add("🤖 AI Analysis")
        self.tabview.add("📚 Study Recommendations")
        self.tabview.add("📈 Analytics")
        self.tabview.add("🎯 Goals")
        self.tabview.add("⚙️ Settings")

        # Setup each tab
        self.setup_dashboard_tab()
        self.setup_tracking_tab()
        self.setup_analysis_tab()
        self.setup_study_tab()
        self.setup_analytics_tab()
        self.setup_goals_tab()
        self.setup_settings_tab()

        # Status bar
        self.setup_status_bar()

    def setup_dashboard_tab(self):
        """Setup dashboard with overview"""
        tab = self.tabview.tab("🏠 Dashboard")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        # Title
        title = ctk.CTkLabel(tab, text="AI Productivity Dashboard",
                             font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, pady=(0, 20), sticky="w")

        # Stats cards
        stats_frame = ctk.CTkFrame(tab)
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Productivity Score
        score_card = ctk.CTkFrame(stats_frame, fg_color="#2b5b84")
        score_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(score_card, text="🏆 Productivity Score",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5))
        self.score_label = ctk.CTkLabel(score_card, text="--/100",
                                        font=ctk.CTkFont(size=24, weight="bold"))
        self.score_label.grid(row=1, column=0, padx=15, pady=(0, 15))

        # Current Activity
        activity_card = ctk.CTkFrame(stats_frame, fg_color="#2b5b84")
        activity_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(activity_card, text="🖥️ Current Activity",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5))
        self.activity_label = ctk.CTkLabel(activity_card, text="None",
                                           font=ctk.CTkFont(size=16))
        self.activity_label.grid(row=1, column=0, padx=15, pady=(0, 15))

        # Tracked Time
        time_card = ctk.CTkFrame(stats_frame, fg_color="#2b5b84")
        time_card.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(time_card, text="⏱️ Tracked Time",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5))
        self.time_label = ctk.CTkLabel(time_card, text="0h 0m",
                                       font=ctk.CTkFont(size=24, weight="bold"))
        self.time_label.grid(row=1, column=0, padx=15, pady=(0, 15))

        # LLM Status
        llm_card = ctk.CTkFrame(stats_frame, fg_color="#2b5b84")
        llm_card.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(llm_card, text="🤖 AI Status",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5))
        self.llm_status_label = ctk.CTkLabel(llm_card, text="Ready",
                                             font=ctk.CTkFont(size=16))
        self.llm_status_label.grid(row=1, column=0, padx=15, pady=(0, 15))

        # Controls
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        controls_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.tracking_button = ctk.CTkButton(
            controls_frame,
            text="🎯 Start Tracking",
            command=self.toggle_tracking,
            width=150,
            height=40
        )
        self.tracking_button.grid(row=0, column=0, padx=10, pady=10)

        ctk.CTkButton(
            controls_frame,
            text="📊 Generate Report",
            command=self.generate_report,
            width=150,
            height=40
        ).grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkButton(
            controls_frame,
            text="🔔 Test Notification",
            command=self.test_notification,
            width=150,
            height=40
        ).grid(row=0, column=2, padx=10, pady=10)

        ctk.CTkButton(
            controls_frame,
            text="🧠 Test LLM",
            command=self.test_llm_connection,
            width=150,
            height=40
        ).grid(row=0, column=3, padx=10, pady=10)

        # Activity log
        log_frame = ctk.CTkFrame(tab)
        log_frame.grid(row=3, column=0, sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="📋 Recent Activities",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=15)

        self.activity_log = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(size=12))
        self.activity_log.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="nsew")
        self.activity_log.configure(state="disabled")

    def setup_tracking_tab(self):
        """Setup real-time tracking tab"""
        tab = self.tabview.tab("📊 Real-time Tracking")
        tab.grid_columnconfigure(0, weight=1)

        # Current activity details
        current_frame = ctk.CTkFrame(tab)
        current_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        current_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(current_frame, text="🎯 Current Activity Details",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=20,
                                                                    pady=15)

        # Activity details grid
        details = [
            ("Application:", "app_detail"),
            ("Window Title:", "title_detail"),
            ("Category:", "category_detail"),
            ("Productivity Score:", "score_detail"),
            ("Duration:", "duration_detail")
        ]

        self.detail_labels = {}
        for i, (label, key) in enumerate(details):
            ctk.CTkLabel(current_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=i + 1, column=0,
                                                                                          sticky="w", padx=20, pady=5)
            value_label = ctk.CTkLabel(current_frame, text="--", font=ctk.CTkFont(size=12))
            value_label.grid(row=i + 1, column=1, sticky="w", padx=20, pady=5)
            self.detail_labels[key] = value_label

        # Productivity meter
        meter_frame = ctk.CTkFrame(tab)
        meter_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))

        ctk.CTkLabel(meter_frame, text="📈 Productivity Level",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=15)

        self.productivity_meter = ctk.CTkProgressBar(meter_frame, width=400, height=20)
        self.productivity_meter.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.productivity_meter.set(0)

        self.meter_label = ctk.CTkLabel(meter_frame, text="--/100", font=ctk.CTkFont(weight="bold"))
        self.meter_label.grid(row=1, column=1, padx=10, sticky="w")

    def setup_analysis_tab(self):
        """Setup AI analysis tab"""
        tab = self.tabview.tab("🤖 AI Analysis")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # LLM Status
        status_frame = ctk.CTkFrame(tab)
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        status_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(status_frame, text="LLM Status",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.llm_debug_status = ctk.CTkLabel(status_frame, text="Testing...")
        self.llm_debug_status.grid(row=0, column=1, padx=10, pady=5)

        # Controls
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        controls_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(controls_frame, text="AI-Powered Analysis",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=20,
                                                                    pady=15)

        ctk.CTkButton(controls_frame, text="🚀 Run Analysis",
                      command=self.run_ai_analysis, width=150).grid(row=1, column=0, padx=20, pady=10)

        ctk.CTkButton(controls_frame, text="💬 Get Motivation",
                      command=self.get_motivation, width=150).grid(row=1, column=1, padx=20, pady=10)

        ctk.CTkButton(controls_frame, text="🧪 Test LLM",
                      command=self.test_llm_connection, width=150).grid(row=1, column=2, padx=20, pady=10)

        # Results
        results_frame = ctk.CTkFrame(tab)
        results_frame.grid(row=2, column=0, sticky="nsew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        self.analysis_text = ctk.CTkTextbox(results_frame, font=ctk.CTkFont(size=12))
        self.analysis_text.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.analysis_text.insert("1.0", "Run AI analysis to see insights about your productivity patterns...")
        self.analysis_text.configure(state="disabled")

    def setup_study_tab(self):
        """Setup study recommendations tab"""
        tab = self.tabview.tab("📚 Study Recommendations")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(tab, text="Personalized Learning Recommendations",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=15)

        ctk.CTkButton(tab, text="🔄 Update Recommendations",
                      command=self.update_recommendations, width=200).grid(row=0, column=1, padx=20, pady=15)

        self.recommendations_text = ctk.CTkTextbox(tab, font=ctk.CTkFont(size=12))
        self.recommendations_text.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
        self.recommendations_text.insert("1.0",
                                         "Click 'Update Recommendations' to get personalized study tips based on your activity patterns.")
        self.recommendations_text.configure(state="disabled")

    def setup_analytics_tab(self):
        """Setup analytics tab with visual charts"""
        tab = self.tabview.tab("📈 Analytics")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(tab)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header_frame, text="📊 Visual Analytics Dashboard",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=15)

        ctk.CTkButton(header_frame, text="🔄 Refresh Charts",
                      command=self.refresh_analytics, width=150).grid(row=0, column=1, padx=20, pady=15, sticky="e")

        # Charts container (scrollable)
        charts_frame = ctk.CTkScrollableFrame(tab)
        charts_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        charts_frame.grid_columnconfigure(0, weight=1)

        self.charts_container = charts_frame
        self.chart_labels = []

        # Initial chart load
        self.refresh_analytics()

    def refresh_analytics(self):
        """Refresh analytics charts"""
        if not HAS_CHARTS:
            if hasattr(self, 'charts_container'):
                for widget in self.charts_container.winfo_children():
                    widget.destroy()
            ctk.CTkLabel(self.charts_container, text="❌ Charts module not available. Install matplotlib and pandas.",
                        font=ctk.CTkFont(size=14)).grid(row=0, column=0, pady=20)
            return

        try:
            # Clear existing charts
            for widget in self.charts_container.winfo_children():
                widget.destroy()
            self.chart_labels = []

            # Get activities from database
            activities = []
            if self.db:
                activities = self.db.get_recent_activities(limit=500)

            if not activities:
                ctk.CTkLabel(self.charts_container, text="📊 No data available yet. Start tracking to see analytics!",
                            font=ctk.CTkFont(size=14)).grid(row=0, column=0, pady=50)
                return

            # Generate charts
            try:
                import matplotlib
                matplotlib.use("Agg")
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                from ui.charts import create_charts

                figures = create_charts(activities)

                for i, fig in enumerate(figures):
                    # Create canvas for each chart
                    canvas = FigureCanvasTkAgg(fig, self.charts_container)
                    canvas.draw()
                    canvas.get_tk_widget().grid(row=i, column=0, pady=10, padx=10, sticky="ew")
                    self.chart_labels.append(canvas)

            except ImportError as e:
                self.logger.error(f"Error importing chart libraries: {e}")
                ctk.CTkLabel(self.charts_container, 
                            text=f"❌ Chart libraries not available: {e}\nInstall: pip install matplotlib pandas",
                            font=ctk.CTkFont(size=12)).grid(row=0, column=0, pady=20)
            except Exception as e:
                self.logger.error(f"Error generating charts: {e}")
                ctk.CTkLabel(self.charts_container, 
                            text=f"❌ Error generating charts: {e}",
                            font=ctk.CTkFont(size=12)).grid(row=0, column=0, pady=20)

        except Exception as e:
            self.logger.error(f"Error refreshing analytics: {e}")
            import traceback
            traceback.print_exc()

    def setup_goals_tab(self):
        """Setup goals management tab"""
        tab = self.tabview.tab("🎯 Goals")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Header with create button
        header_frame = ctk.CTkFrame(tab)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header_frame, text="🎯 Productivity Goals",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=15)

        ctk.CTkButton(header_frame, text="➕ Create Goal",
                      command=self.create_goal_dialog, width=150).grid(row=0, column=1, padx=20, pady=15, sticky="e")

        # Goals list (scrollable)
        goals_frame = ctk.CTkScrollableFrame(tab)
        goals_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        goals_frame.grid_columnconfigure(0, weight=1)

        self.goals_container = goals_frame

        # Refresh button
        refresh_frame = ctk.CTkFrame(tab)
        refresh_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(refresh_frame, text="🔄 Refresh Goals",
                      command=self.refresh_goals, width=200).grid(row=0, column=0, padx=20, pady=10)

        # Initial load
        self.refresh_goals()

    def create_goal_dialog(self):
        """Open dialog to create a new goal"""
        if not self.goal_tracker:
            messagebox.showerror("Error", "Goal Tracker not available!")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create New Goal")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Goal type
        ctk.CTkLabel(dialog, text="Goal Type:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        goal_type_var = ctk.StringVar(value="daily")
        goal_type_menu = ctk.CTkOptionMenu(dialog, values=["daily", "weekly", "monthly"], variable=goal_type_var)
        goal_type_menu.grid(row=0, column=1, padx=20, pady=10, sticky="ew")

        # Target score
        ctk.CTkLabel(dialog, text="Target Score (0-100):", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        target_score_var = ctk.StringVar(value="70")
        target_score_entry = ctk.CTkEntry(dialog, textvariable=target_score_var, width=200)
        target_score_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # Target hours (optional)
        ctk.CTkLabel(dialog, text="Target Hours (optional):", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        target_hours_var = ctk.StringVar(value="")
        target_hours_entry = ctk.CTkEntry(dialog, textvariable=target_hours_var, width=200)
        target_hours_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        # Category (optional)
        ctk.CTkLabel(dialog, text="Category (optional):", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=20, pady=10, sticky="w")
        category_var = ctk.StringVar(value="")
        category_entry = ctk.CTkEntry(dialog, textvariable=category_var, width=200)
        category_entry.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        # Description
        ctk.CTkLabel(dialog, text="Description:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=20, pady=10, sticky="nw")
        description_text = ctk.CTkTextbox(dialog, width=300, height=100)
        description_text.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

        dialog.grid_columnconfigure(1, weight=1)

        def save_goal():
            try:
                goal_data = {
                    'goal_type': goal_type_var.get(),
                    'target_score': int(target_score_var.get()) if target_score_var.get() else None,
                    'target_hours': float(target_hours_var.get()) if target_hours_var.get() else None,
                    'target_category': category_var.get() if category_var.get() else None,
                    'description': description_text.get("1.0", "end-1c").strip()
                }

                goal_id = self.goal_tracker.create_goal(goal_data)
                if goal_id:
                    messagebox.showinfo("Success", "Goal created successfully!")
                    dialog.destroy()
                    self.refresh_goals()
                else:
                    messagebox.showerror("Error", "Failed to create goal")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create goal: {e}")

        ctk.CTkButton(dialog, text="Create Goal", command=save_goal, width=150).grid(row=5, column=0, columnspan=2, pady=20)

    def refresh_goals(self):
        """Refresh goals display"""
        if not self.goal_tracker:
            if hasattr(self, 'goals_container'):
                for widget in self.goals_container.winfo_children():
                    widget.destroy()
            ctk.CTkLabel(self.goals_container, text="❌ Goal Tracker not available",
                        font=ctk.CTkFont(size=14)).grid(row=0, column=0, pady=20)
            return

        try:
            # Clear existing goals
            for widget in self.goals_container.winfo_children():
                widget.destroy()

            # Get active goals
            active_goals = self.goal_tracker.get_active_goals()

            if not active_goals:
                ctk.CTkLabel(self.goals_container, text="📝 No active goals. Create one to get started!",
                            font=ctk.CTkFont(size=14)).grid(row=0, column=0, pady=50)
                return

            # Display each goal
            for i, goal in enumerate(active_goals):
                goal_frame = ctk.CTkFrame(self.goals_container)
                goal_frame.grid(row=i, column=0, sticky="ew", pady=5, padx=10)
                goal_frame.grid_columnconfigure(1, weight=1)

                # Goal info
                goal_type_emoji = {"daily": "📅", "weekly": "📆", "monthly": "🗓️"}.get(goal['goal_type'], "🎯")
                goal_title = f"{goal_type_emoji} {goal.get('description', 'No description')}"
                
                ctk.CTkLabel(goal_frame, text=goal_title,
                            font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)

                # Progress bar
                progress = goal.get('current_progress', 0)
                progress_bar = ctk.CTkProgressBar(goal_frame, width=400)
                progress_bar.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
                progress_bar.set(progress / 100.0)

                # Progress text
                target_text = ""
                if goal.get('target_score'):
                    target_text = f"Target: {goal['target_score']}%"
                elif goal.get('target_hours'):
                    target_text = f"Target: {goal['target_hours']} hours"
                
                progress_text = f"{progress:.1f}% - {target_text}"
                ctk.CTkLabel(goal_frame, text=progress_text,
                            font=ctk.CTkFont(size=12)).grid(row=2, column=0, sticky="w", padx=10, pady=5)

                # Delete button
                def delete_goal(goal_id=goal['id']):
                    if messagebox.askyesno("Delete Goal", "Are you sure you want to delete this goal?"):
                        if self.goal_tracker.delete_goal(goal_id):
                            self.refresh_goals()

                ctk.CTkButton(goal_frame, text="🗑️ Delete", command=delete_goal, width=80, fg_color="#dc3545",
                             hover_color="#c82333").grid(row=2, column=1, padx=10, pady=5, sticky="e")

        except Exception as e:
            self.logger.error(f"Error refreshing goals: {e}")
            import traceback
            traceback.print_exc()

    def setup_settings_tab(self):
        """Setup settings tab with enhanced LLM model management"""
        tab = self.tabview.tab("⚙️ Settings")
        tab.grid_columnconfigure(0, weight=1)

        # Tracking settings
        tracking_frame = ctk.CTkFrame(tab)
        tracking_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        ctk.CTkLabel(tracking_frame, text="Tracking Settings",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=15)

        self.auto_start_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tracking_frame, text="Start tracking automatically",
                        variable=self.auto_start_var).grid(row=1, column=0, sticky="w", padx=20, pady=5)

        self.notifications_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tracking_frame, text="Enable notifications",
                        variable=self.notifications_var).grid(row=2, column=0, sticky="w", padx=20, pady=5)

        # LLM settings
        llm_frame = ctk.CTkFrame(tab)
        llm_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        llm_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(llm_frame, text="AI Settings",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=20,
                                                                    pady=15)

        ctk.CTkLabel(llm_frame, text="LLM Model:").grid(row=1, column=0, sticky="w", padx=20, pady=5)

        # Get available models from LLM client
        available_models = ["llama3.2:latest", "mistral:latest", "llama2:7b", "codellama:7b"]
        if self.llm_client and hasattr(self.llm_client, 'get_available_models'):
            try:
                available_models = self.llm_client.get_available_models()
            except Exception as e:
                self.logger.error(f"Error getting available models: {e}")

        # Get current model
        current_model = self.llm_client.model_name if self.llm_client else "llama3.2:latest"

        self.model_var = ctk.StringVar(value=current_model)
        self.model_menu = ctk.CTkOptionMenu(llm_frame, values=available_models,
                                            variable=self.model_var, width=200,
                                            command=self.on_model_change)
        self.model_menu.grid(row=1, column=1, padx=20, pady=5)

        # Refresh models button
        ctk.CTkButton(llm_frame, text="🔄 Refresh Models",
                      command=self.refresh_models, width=120).grid(row=1, column=2, padx=10, pady=5)

        # Model status
        self.model_status_label = ctk.CTkLabel(llm_frame, text="", font=ctk.CTkFont(size=12))
        self.model_status_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=20, pady=5)

        # Update model status
        self.update_model_status()

    def setup_status_bar(self):
        """Setup status bar at bottom"""
        status_frame = ctk.CTkFrame(self.root)
        status_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        # Left status
        left_status = ctk.CTkFrame(status_frame, fg_color="transparent")
        left_status.grid(row=0, column=0, sticky="w")

        self.status_label = ctk.CTkLabel(left_status, text="Ready to start tracking")
        self.status_label.grid(row=0, column=0, padx=10, pady=5)

        # Right status
        right_status = ctk.CTkFrame(status_frame, fg_color="transparent")
        right_status.grid(row=0, column=1, sticky="e")

        self.tracking_status = ctk.CTkLabel(right_status, text="Tracking: 🔴 Offline")
        self.tracking_status.grid(row=0, column=0, padx=10, pady=5)

        self.llm_status = ctk.CTkLabel(right_status, text="AI: 🔴 Offline")
        self.llm_status.grid(row=0, column=1, padx=10, pady=5)

    def on_model_change(self, new_model):
        """Handle model change"""
        if not self.llm_client:
            return

        def change_model():
            try:
                success = self.llm_client.set_model(new_model)
                self.root.after(0, lambda: self.handle_model_change_result(success, new_model))
            except Exception as e:
                self.root.after(0, lambda: self.handle_model_change_result(False, new_model, str(e)))

        self.model_status_label.configure(text="🔄 Changing model...", text_color="#ffc107")
        threading.Thread(target=change_model, daemon=True).start()

    def handle_model_change_result(self, success: bool, model_name: str, error: str = None):
        """Handle the result of model change"""
        if success:
            self.model_status_label.configure(text=f"✅ Using {model_name}", text_color="#28a745")
            self.logger.info(f"Model changed to {model_name}")
            # Update the model variable to reflect the change
            self.model_var.set(model_name)
        else:
            error_msg = error if error else "Model not available"
            self.model_status_label.configure(text=f"❌ Failed: {error_msg}", text_color="#dc3545")
            self.logger.error(f"Failed to change model to {model_name}: {error_msg}")

    def refresh_models(self):
        """Refresh available models list"""
        if not self.llm_client:
            return

        def refresh():
            try:
                available_models = self.llm_client.get_available_models()
                self.root.after(0, lambda: self.update_model_menu(available_models))
            except Exception as e:
                self.root.after(0, lambda: self.model_status_label.configure(
                    text=f"❌ Refresh failed: {e}", text_color="#dc3545"))

        self.model_status_label.configure(text="🔄 Refreshing models...", text_color="#ffc107")
        threading.Thread(target=refresh, daemon=True).start()

    def update_model_menu(self, available_models):
        """Update the model dropdown menu"""
        if available_models:
            current_value = self.model_var.get()
            self.model_menu.configure(values=available_models)

            # If current value is not in available models, set to first available
            if current_value not in available_models:
                self.model_var.set(available_models[0])

            self.model_status_label.configure(text=f"✅ {len(available_models)} models available", text_color="#28a745")
        else:
            self.model_status_label.configure(text="❌ No models available", text_color="#dc3545")

    def update_model_status(self):
        """Update model status display"""
        if self.llm_client:
            current_model = self.llm_client.model_name
            status = "🟢 Connected" if self.llm_client.is_available else "🔴 Offline"
            self.model_status_label.configure(text=f"{status} - {current_model}",
                                              text_color="#28a745" if self.llm_client.is_available else "#dc3545")

    def toggle_tracking(self):
        """Toggle activity tracking on/off with error handling"""
        if not self.tracker:
            messagebox.showerror("Error", "Activity tracker not available!")
            return

        if not self.is_tracking:
            # Start tracking
            try:
                if self.tracker.start_tracking():
                    self.is_tracking = True
                    self.tracking_button.configure(text="⏹️ Stop Tracking", fg_color="#dc3545")
                    self.status_label.configure(text="Tracking active - AI analysis enabled")
                    self.tracking_status.configure(text="Tracking: 🟢 Active")
                    self.logger.info("Tracking started")
                else:
                    messagebox.showerror("Error", "Failed to start tracking")
            except Exception as e:
                self.logger.error(f"Failed to start tracking: {e}")
                messagebox.showerror("Error", f"Failed to start tracking: {e}")
        else:
            # Stop tracking
            try:
                self.tracker.stop_tracking()
                self.is_tracking = False
                self.tracking_button.configure(text="🎯 Start Tracking", fg_color="#2b5b84")
                self.status_label.configure(text="Tracking stopped")
                self.tracking_status.configure(text="Tracking: 🔴 Offline")
                self.logger.info("Tracking stopped")
            except Exception as e:
                self.logger.error(f"Failed to stop tracking: {e}")
                messagebox.showerror("Error", f"Failed to stop tracking: {e}")

    def generate_report(self):
        """Generate productivity report with real data"""
        try:
            # Get activities from database
            activities = []
            if self.db:
                activities = self.db.get_recent_activities(limit=100)

            if not activities:
                messagebox.showinfo("Report", "No activity data available yet. Start tracking to generate reports!")
                return

            # Calculate real metrics
            productive_activities = [a for a in activities if a.get('productivity_score', 0) > 60]
            unproductive_activities = [a for a in activities if a.get('productivity_score', 0) < 40]

            productive_time = sum(a.get('duration', 0) for a in productive_activities)
            total_time = sum(a.get('duration', 0) for a in activities)
            productivity_ratio = (productive_time / total_time * 100) if total_time > 0 else 0

            # Get categories and apps
            categories = {}
            apps = {}
            for activity in activities:
                category = activity.get('category', 'unknown')
                app_name = activity.get('app_name', 'unknown')
                categories[category] = categories.get(category, 0) + 1
                apps[app_name] = apps.get(app_name, 0) + 1

            top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else 'unknown'
            top_app = max(apps.items(), key=lambda x: x[1])[0] if apps else 'unknown'

            # Generate report with LLM insights if available
            report_text = f"""📊 PRODUCTIVITY REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

📈 BASIC METRICS:
• Total Activities: {len(activities)}
• Productive Activities: {len(productive_activities)} ({len(productive_activities) / len(activities) * 100:.1f}%)
• Unproductive Activities: {len(unproductive_activities)} ({len(unproductive_activities) / len(activities) * 100:.1f}%)
• Productivity Ratio: {productivity_ratio:.1f}%
• Most Used Category: {top_category}
• Most Used App: {top_app}

⏱️ TIME ANALYSIS:
• Total Tracked Time: {total_time // 3600}h {(total_time % 3600) // 60}m
• Productive Time: {productive_time // 3600}h {(productive_time % 3600) // 60}m
"""

            # Add LLM insights if available
            if self.llm_client and self.llm_client.is_available:
                try:
                    analysis = self.llm_client.analyze_productivity_trend_enhanced(activities)
                    report_text += f"\n🤖 AI INSIGHTS:\n{analysis['insight']}\n"
                except Exception as e:
                    report_text += f"\n🤖 AI Insights: Temporarily unavailable\n"

            # Add recent activities
            report_text += f"\n📋 RECENT ACTIVITIES (Last 5):\n"
            for i, activity in enumerate(activities[:5]):
                app = activity.get('app_name', 'Unknown')
                category = activity.get('category', 'unknown')
                score = activity.get('productivity_score', 50)
                duration = activity.get('duration', 0)
                report_text += f"{i + 1}. {app} ({category}) - Score: {score}, Duration: {duration}s\n"

            messagebox.showinfo("Productivity Report", report_text)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")

    def test_notification(self):
        """Test notification system"""
        try:
            if HAS_NOTIFICATIONS:
                show_notification(
                    "Test Notification",
                    "This is a test from the Productivity Tracker! 🚀"
                )
                self.logger.info("Test notification sent")
            else:
                messagebox.showinfo("Test Notification", "This is a test notification! 🚀")
        except Exception as e:
            messagebox.showerror("Error", f"Notification test failed: {e}")

    def test_llm_connection(self):
        """Test LLM connection and display results"""
        if not self.llm_client:
            messagebox.showerror("Error", "LLM client not available")
            return

        def test_llm():
            try:
                result = self.llm_client.test_connection()
                self.root.after(0, lambda: self.display_llm_test_result(result))
            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Test failed: {str(e)}",
                    "model": getattr(self.llm_client, 'model_name', 'Unknown')
                }
                self.root.after(0, lambda: self.display_llm_test_result(error_result))

        # Show loading message
        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        current_model = getattr(self.llm_client, 'model_name', 'Unknown')
        self.analysis_text.insert("1.0",
                                  f"🧪 Testing LLM connection...\n\nModel: {current_model}\nStatus: Testing...\n\nPlease wait...")
        self.analysis_text.configure(state="disabled")

        # Run test in background thread
        threading.Thread(target=test_llm, daemon=True).start()

    def display_llm_test_result(self, result):
        """Display LLM test results"""
        try:
            self.analysis_text.configure(state="normal")
            self.analysis_text.delete("1.0", "end")

            status = result.get('status', 'unknown')
            message = result.get('message', 'No message provided')

            # Status emojis and colors
            if status == "online":
                status_emoji = "✅"
                status_color = "#28a745"
            elif status == "error":
                status_emoji = "❌"
                status_color = "#dc3545"
            else:
                status_emoji = "⚠️"
                status_color = "#ffc107"

            output = f"{status_emoji} LLM Test Results\n\n"
            output += f"Status: {status}\n"
            output += f"Message: {message}\n\n"

            # Add model information
            if 'model' in result:
                output += f"🤖 Model: {result['model']}\n"

            if 'available_models' in result:
                output += f"📚 Available Models: {', '.join(result['available_models'])}\n"

            # Add test results if available
            if 'test_quote' in result:
                output += f"\n🎯 Test Quote:\n{result['test_quote']}\n"

            if 'test_recommendations' in result and result['test_recommendations']:
                output += f"\n📚 Test Recommendations:\n"
                for i, rec in enumerate(result['test_recommendations'], 1):
                    output += f"  {i}. {rec}\n"

            if 'test_analysis' in result:
                output += f"\n📊 Test Analysis:\n{result['test_analysis']}\n"

            # If no specific test results, show basic status
            if len(output.strip().split('\n')) <= 5:
                output += "\n💡 Tip: Make sure Ollama is running with 'ollama serve' and you have models pulled."

            self.analysis_text.insert("1.0", output)
            self.analysis_text.configure(state="disabled")

            # Update status label
            self.llm_debug_status.configure(text=f"{status_emoji} {status.upper()}", text_color=status_color)

            # Also show in message box for immediate feedback
            if status == "online":
                messagebox.showinfo("LLM Test", f"✅ LLM is working!\nModel: {result.get('model', 'Unknown')}")
            else:
                messagebox.showerror("LLM Test", f"❌ LLM test failed:\n{message}")

        except Exception as e:
            error_msg = f"Error displaying results: {str(e)}"
            self.analysis_text.configure(state="normal")
            self.analysis_text.delete("1.0", "end")
            self.analysis_text.insert("1.0", f"❌ Error: {error_msg}")
            self.analysis_text.configure(state="disabled")
            messagebox.showerror("Display Error", error_msg)

    def run_ai_analysis(self):
        """Run AI analysis on current activities"""
        if not self.llm_client or not self.llm_client.is_available:
            messagebox.showerror("Error", "LLM not available. Make sure Ollama is running!")
            return

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", "🤖 Analyzing your productivity patterns...\n\n")
        self.analysis_text.configure(state="disabled")

        def analyze():
            try:
                # Get activities from database
                activities = []
                if self.db:
                    activities = self.db.get_recent_activities(limit=50)

                if not activities:
                    self.root.after(0, lambda: self.display_analysis_results(
                        "No activity data available for analysis. Start tracking to generate insights!"))
                    return

                # Use LLM to analyze activities
                analysis_result = self.llm_client.analyze_productivity_trend_enhanced(activities)

                analysis_text = f"""📊 AI PRODUCTIVITY ANALYSIS

Activities Analyzed: {analysis_result['activities_analyzed']}
Productivity Score: {analysis_result['productivity_score']}/100
Productivity Ratio: {analysis_result['productive_ratio']}
Model Used: {analysis_result['model_used']}
Status: {analysis_result['status']}

🤖 AI INSIGHTS:
{analysis_result['insight']}

💡 RECOMMENDATIONS:
• Track more activities for better insights
• Focus on your most productive categories
• Use the Pomodoro technique for better focus
• Take regular breaks to maintain productivity
"""

                self.root.after(0, lambda: self.display_analysis_results(analysis_text))
            except Exception as e:
                self.logger.error(f"Analysis failed: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Analysis failed: {e}"))

        threading.Thread(target=analyze, daemon=True).start()

    def display_analysis_results(self, analysis_text):
        """Display analysis results"""
        try:
            self.analysis_text.configure(state="normal")
            self.analysis_text.delete("1.0", "end")
            self.analysis_text.insert("1.0", analysis_text)
            self.analysis_text.configure(state="disabled")
        except Exception as e:
            self.logger.error(f"Error displaying analysis: {e}")

    def get_motivation(self):
        """Get motivational quote using LLM with current activity"""
        try:
            if not self.llm_client or not self.llm_client.is_available:
                messagebox.showerror("LLM Not Available",
                                     "Local LLM is not available. Make sure Ollama is running with 'ollama serve'")
                return

            # Use current activity or create a sample
            if self.current_activity:
                activity_data = self.current_activity
            else:
                # Fallback activity data
                activity_data = {
                    "app_name": "Your Computer",
                    "category": "general",
                    "productivity_score": 75
                }

            # Generate quote using LLM
            quote = self.llm_client.generate_motivational_quote(activity_data)
            messagebox.showinfo("💫 Motivation", quote)

        except Exception as e:
            self.logger.error(f"Motivation generation failed: {e}")
            messagebox.showerror("Error", f"Failed to generate motivation: {e}")

    def update_recommendations(self):
        """Update study recommendations with real LLM output"""
        try:
            if not self.llm_client or not self.llm_client.is_available:
                self.show_fallback_recommendations()
                return

            # Get real activities for analysis
            activities = []
            if self.db:
                activities = self.db.get_recent_activities(limit=50)

            if not activities:
                self.show_fallback_recommendations()
                return

            # Generate REAL recommendations using LLM
            recommendations = self.llm_client.generate_study_recommendations(activities)

            self.recommendations_text.configure(state="normal")
            self.recommendations_text.delete("1.0", "end")

            recommendations_text = f"""📚 PERSONALIZED STUDY RECOMMENDATIONS

Current Model: {self.llm_client.model_name}
Activities Analyzed: {len(activities)}

🤖 AI-GENERATED RECOMMENDATIONS:

"""
            for i, rec in enumerate(recommendations, 1):
                recommendations_text += f"{i}. {rec}\n"

            # Add activity insights
            productive_activities = [a for a in activities if a.get('productivity_score', 0) > 60]
            if productive_activities:
                top_categories = {}
                for activity in productive_activities:
                    category = activity.get('category', 'general')
                    top_categories[category] = top_categories.get(category, 0) + 1

                if top_categories:
                    top_category = max(top_categories.items(), key=lambda x: x[1])[0]
                    recommendations_text += f"\n🎯 Your productive work focuses on: {top_category}\n"

            recommendations_text += """
💡 PRO TIPS:
• Track more activities for better personalization
• Use 'Run Analysis' for detailed insights  
• Keep Ollama running for AI features
"""

            self.recommendations_text.insert("1.0", recommendations_text)
            self.recommendations_text.configure(state="disabled")

        except Exception as e:
            self.logger.error(f"Recommendations update failed: {e}")
            self.show_fallback_recommendations()

    def show_fallback_recommendations(self):
        """Show fallback when LLM is unavailable"""
        self.recommendations_text.configure(state="normal")
        self.recommendations_text.delete("1.0", "end")

        fallback_text = """📚 STUDY RECOMMENDATIONS

🤖 AI Features Currently Unavailable

To enable AI-powered recommendations:

1. Ensure Ollama is running:
   • Open terminal and run: ollama serve

2. Check available models:
   • Run: ollama list

3. Pull a model if needed:
   • Run: ollama pull llama3.2:latest

4. Restart the Productivity Tracker

💡 MANUAL TIPS:
• Practice coding daily (30+ minutes)
• Work on personal projects
• Read documentation and tutorials
• Join programming communities
• Review your code regularly
"""

        self.recommendations_text.insert("1.0", fallback_text)
        self.recommendations_text.configure(state="disabled")

    def update_ui_loop(self):
        """Main UI update loop with real data"""
        try:
            # Update current activity with real data
            if self.is_tracking and self.tracker and hasattr(self.tracker, 'get_current_activity'):
                try:
                    current_activity = self.tracker.get_current_activity()
                    if current_activity:
                        self.current_activity = current_activity

                        # Update activity display with REAL data
                        app_name = current_activity.get('app_name', 'Unknown')
                        if hasattr(self, 'activity_label'):
                            self.activity_label.configure(text=app_name)

                        # Update detailed view with REAL data
                        if hasattr(self, 'detail_labels'):
                            self.detail_labels['app_detail'].configure(text=app_name)
                            self.detail_labels['title_detail'].configure(
                                text=str(current_activity.get('window_title', 'Unknown'))[:50]
                            )
                            self.detail_labels['category_detail'].configure(
                                text=str(current_activity.get('category', 'unknown'))
                            )

                            # REAL productivity score
                            score = current_activity.get('productivity_score', 50)
                            self.detail_labels['score_detail'].configure(text=str(score))

                            duration = current_activity.get('duration', 0)
                            if duration:
                                mins = duration // 60
                                secs = duration % 60
                                self.detail_labels['duration_detail'].configure(text=f"{mins}m {secs}s")

                        # Update productivity meter with REAL score
                        if hasattr(self, 'productivity_meter'):
                            score = current_activity.get('productivity_score', 50)
                            self.productivity_meter.set(score / 100.0)  # Convert to 0-1 scale

                        if hasattr(self, 'meter_label'):
                            self.meter_label.configure(text=f"{score}/100")

                        # Update activity log
                        self.update_activity_log(current_activity)

                except Exception as e:
                    self.logger.error(f"Error updating current activity: {e}")

            # Update LLM status with real status
            if self.llm_client:
                status_text = "🟢 Connected" if self.llm_client.is_available else "🔴 Offline"
                model_name = getattr(self.llm_client, 'model_name', 'Unknown')
                if hasattr(self, 'llm_status_label'):
                    self.llm_status_label.configure(text=status_text)
                if hasattr(self, 'llm_status'):
                    self.llm_status.configure(text=f"AI: {status_text}")

            # Update productivity score with real data
            if hasattr(self, 'score_label'):
                # Calculate average productivity from recent activities
                activities = []
                if self.db:
                    activities = self.db.get_recent_activities(limit=20)

                if activities:
                    avg_score = sum(a.get('productivity_score', 50) for a in activities) / len(activities)
                    self.score_label.configure(text=f"{int(avg_score)}/100")
                else:
                    self.score_label.configure(text="--/100")

            # Update total time with real data
            if hasattr(self, 'time_label'):
                activities_count = 0
                if self.db:
                    activities = self.db.get_recent_activities(limit=1000)  # Get all activities
                    activities_count = len(activities)
                self.time_label.configure(text=f"{activities_count} acts")

        except Exception as e:
            self.logger.error(f"UI update error: {e}")

        # Schedule next update
        self.root.after(2000, self.update_ui_loop)

    def update_activity_log(self, activity):
        """Update activity log display"""
        try:
            if activity and activity != self._last_logged_activity:
                self._last_logged_activity = activity

                self.activity_log.configure(state="normal")

                timestamp = datetime.now().strftime("%H:%M:%S")
                app_name = activity.get('app_name', 'Unknown')
                category = activity.get('category', 'unknown')
                score = activity.get('productivity_score', 50)

                emoji = "🚀" if score >= 80 else "💪" if score >= 60 else "⚡" if score >= 40 else "💬"

                log_entry = f"[{timestamp}] {emoji} {app_name} - {category} (score: {score})\n"

                # Keep only last 20 entries
                current_text = self.activity_log.get("1.0", "end-1c")
                lines = current_text.split('\n')
                if len(lines) > 20:
                    self.activity_log.delete("1.0", "end")
                    self.activity_log.insert("1.0", '\n'.join(lines[-20:]) + '\n')

                self.activity_log.insert("end", log_entry)
                self.activity_log.see("end")
                self.activity_log.configure(state="disabled")
        except Exception as e:
            self.logger.error(f"Error updating activity log: {e}")

    def on_closing(self):
        """Handle window closing"""
        try:
            # Stop tracking if active
            if self.is_tracking and self.tracker and hasattr(self.tracker, 'stop_tracking'):
                self.tracker.stop_tracking()
                self.logger.info("Tracker stopped on window close")

            # Stop the agent
            if self.agent:
                self.agent.stop()

            # Destroy the window
            self.root.destroy()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self.root.destroy()

    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"GUI error: {e}")
            messagebox.showerror("Fatal Error", f"The application encountered an error: {e}")
        finally:
            # Ensure cleanup happens
            if self.is_tracking and self.tracker and hasattr(self.tracker, 'stop_tracking'):
                try:
                    self.tracker.stop_tracking()
                    self.logger.info("Tracker stopped in final cleanup")
                except Exception as e:
                    self.logger.error(f"Error stopping tracker in cleanup: {e}")


def main():
    """Main function to run the GUI"""
    print("🚀 Starting Modern Productivity Tracker GUI...")
    try:
        app = ModernProductivityTracker()
        app.run()
    except Exception as e:
        print(f"❌ Failed to start GUI: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()