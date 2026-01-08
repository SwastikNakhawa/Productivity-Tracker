# analysis/llm_learning_system.py
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class LLMLearningSystem:
    def __init__(self, db_manager, llm_client):
        self.db = db_manager
        self.llm_client = llm_client
        self.setup_logging()

    def setup_logging(self):
        self.logger = logging.getLogger(__name__)

    def analyze_and_learn(self):
        """Main learning loop - analyze patterns and improve LLM responses"""
        try:
            self.logger.info("🧠 Starting LLM learning cycle...")

            # Get recent patterns
            patterns = self.db.get_user_productivity_patterns(days=30)

            # Learn from patterns
            self._learn_from_patterns(patterns)

            # Learn from user feedback
            self._learn_from_feedback()

            # Update personalization model
            self._update_personalization_rules()

            self.logger.info("✅ LLM learning cycle completed")

        except Exception as e:
            self.logger.error(f"❌ Learning cycle failed: {e}")

    def _learn_from_patterns(self, patterns: Dict):
        """Learn from productivity patterns"""
        try:
            # Analyze time-of-day patterns
            time_patterns = patterns.get('time_of_day_patterns', [])
            productive_hours = [
                pattern['hour'] for pattern in time_patterns
                if pattern.get('avg_score', 0) >= 70
            ]

            # Analyze app preferences
            app_patterns = patterns.get('app_usage_patterns', [])
            preferred_apps = [
                app for app in app_patterns
                if app.get('avg_score', 0) >= 70 and app.get('total_duration', 0) > 1800
            ]

            # Save discovered patterns
            if productive_hours:
                self.db.save_productivity_pattern(
                    'productive_hours',
                    {'hours': productive_hours},
                    confidence=0.8
                )

            if preferred_apps:
                self.db.save_productivity_pattern(
                    'preferred_apps',
                    {'apps': [app['app_name'] for app in preferred_apps]},
                    confidence=0.7
                )

            self.logger.info(
                f"📊 Learned from patterns: {len(productive_hours)} productive hours, {len(preferred_apps)} preferred apps")

        except Exception as e:
            self.logger.error(f"Error learning from patterns: {e}")

    def _learn_from_feedback(self):
        """Learn from user feedback on LLM responses"""
        try:
            patterns = self.db.get_user_productivity_patterns(days=30)
            feedback_data = patterns.get('learning_preferences', {})

            llm_feedback = feedback_data.get('llm_feedback', [])
            activity_feedback = feedback_data.get('activity_feedback', [])

            positive_feedback = [f for f in llm_feedback if f.get('user_feedback', 0) > 0]
            negative_feedback = [f for f in llm_feedback if f.get('user_feedback', 0) < 0]

            # Analyze what works well
            successful_patterns = self._analyze_successful_responses(positive_feedback)

            # Analyze what needs improvement
            improvement_areas = self._analyze_unsuccessful_responses(negative_feedback)

            # Update LLM prompt templates based on learning
            self._update_prompts_based_on_feedback(successful_patterns, improvement_areas)

            self.logger.info(
                f"📝 Learned from feedback: {len(positive_feedback)} positive, {len(negative_feedback)} negative")

        except Exception as e:
            self.logger.error(f"Error learning from feedback: {e}")

    def _analyze_successful_responses(self, positive_feedback: List[Dict]) -> Dict:
        """Analyze what makes LLM responses successful"""
        patterns = {
            'response_length': [],
            'content_type': [],
            'tone_analysis': [],
            'specificity_level': []
        }

        for feedback in positive_feedback:
            response = feedback.get('llm_response', '')

            # Analyze response characteristics
            patterns['response_length'].append(len(response))
            patterns['content_type'].append(self._classify_content_type(response))
            patterns['tone_analysis'].append(self._analyze_tone(response))
            patterns['specificity_level'].append(self._analyze_specificity(response))

        return patterns

    def _analyze_unsuccessful_responses(self, negative_feedback: List[Dict]) -> Dict:
        """Analyze why some LLM responses get negative feedback"""
        issues = {
            'too_generic': 0,
            'wrong_tone': 0,
            'irrelevant': 0,
            'too_long': 0,
            'too_short': 0
        }

        for feedback in negative_feedback:
            response = feedback.get('llm_response', '')
            corrected = feedback.get('corrected_response', '')

            # Compare with corrected response to identify issues
            if corrected:
                if len(response) > 200 and len(corrected) < 100:
                    issues['too_long'] += 1
                elif len(response) < 50:
                    issues['too_short'] += 1

                if self._is_generic(response) and not self._is_generic(corrected):
                    issues['too_generic'] += 1

        return issues

    def _update_personalization_rules(self):
        """Update personalization rules based on learned patterns"""
        try:
            # Get current patterns
            patterns = self.db.get_user_productivity_patterns()

            # Create personalized rules
            personalized_rules = self._generate_personalized_rules(patterns)

            # Save rules for use in LLM prompts
            self._save_personalization_rules(personalized_rules)

        except Exception as e:
            self.logger.error(f"Error updating personalization rules: {e}")

    def _generate_personalized_rules(self, patterns: Dict) -> Dict:
        """Generate personalized rules based on user patterns"""
        rules = {
            'productive_times': self._extract_productive_times(patterns),
            'preferred_categories': self._extract_preferred_categories(patterns),
            'learning_style': self._infer_learning_style(patterns),
            'motivation_triggers': self._identify_motivation_triggers(patterns)
        }

        return rules

    def _extract_productive_times(self, patterns: Dict) -> List[str]:
        """Extract user's most productive times"""
        time_patterns = patterns.get('time_of_day_patterns', [])
        productive_hours = [
            f"{int(pattern['hour']):02d}:00" for pattern in time_patterns
            if pattern.get('avg_score', 0) >= 70
        ]
        return productive_hours[:3]

    def _extract_preferred_categories(self, patterns: Dict) -> List[str]:
        """Extract user's preferred productive categories"""
        category_trends = patterns.get('category_trends', [])
        preferred_categories = [
            cat['category'] for cat in category_trends
            if cat.get('avg_score', 0) >= 70 and cat.get('total_duration', 0) > 3600
        ]
        return preferred_categories

    def _infer_learning_style(self, patterns: Dict) -> str:
        """Infer user's learning style from activity patterns"""
        app_patterns = patterns.get('app_usage_patterns', [])

        coding_apps = ['VS Code', 'PyCharm', 'IntelliJ', 'Sublime Text']
        reading_apps = ['Adobe', 'Books', 'Kindle', 'PDF']
        video_apps = ['YouTube', 'VLC', 'Video']

        coding_time = sum(app['total_duration'] for app in app_patterns if
                          any(code_app in app['app_name'] for code_app in coding_apps))
        reading_time = sum(app['total_duration'] for app in app_patterns if
                           any(read_app in app['app_name'] for read_app in reading_apps))
        video_time = sum(
            app['total_duration'] for app in app_patterns if any(vid_app in app['app_name'] for vid_app in video_apps))

        if coding_time > reading_time and coding_time > video_time:
            return "hands_on"
        elif reading_time > coding_time and reading_time > video_time:
            return "reading"
        elif video_time > coding_time and video_time > reading_time:
            return "visual"
        else:
            return "balanced"

    def _identify_motivation_triggers(self, patterns: Dict) -> List[str]:
        """Identify what motivates the user based on patterns"""
        triggers = []

        time_patterns = patterns.get('time_of_day_patterns', [])
        high_productivity_hours = [p for p in time_patterns if p.get('avg_score', 0) >= 80]

        if high_productivity_hours:
            triggers.append("Morning hours" if int(high_productivity_hours[0]['hour']) < 12 else "Afternoon hours")

        category_trends = patterns.get('category_trends', [])
        successful_categories = [c for c in category_trends if c.get('avg_score', 0) >= 80]

        if successful_categories:
            triggers.append(f"Working on {successful_categories[0]['category']} projects")

        return triggers

    def _classify_content_type(self, text: str) -> str:
        """Classify the type of content in LLM response"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['step', 'guide', 'tutorial', 'how to']):
            return "instructional"
        elif any(word in text_lower for word in ['motivat', 'inspire', 'keep going']):
            return "motivational"
        elif any(word in text_lower for word in ['resource', 'website', 'book', 'course']):
            return "resource_recommendation"
        else:
            return "general"

    def _analyze_tone(self, text: str) -> str:
        """Analyze the tone of LLM response"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['great', 'excellent', 'awesome', 'amazing']):
            return "enthusiastic"
        elif any(word in text_lower for word in ['consider', 'suggest', 'recommend']):
            return "suggestive"
        elif any(word in text_lower for word in ['focus', 'concentrate', 'avoid']):
            return "directive"
        else:
            return "neutral"

    def _analyze_specificity(self, text: str) -> str:
        """Analyze specificity level of response"""
        word_count = len(text.split())
        unique_entities = len(set(text.split()))

        if word_count < 30:
            return "brief"
        elif unique_entities / word_count > 0.3:
            return "specific"
        else:
            return "generic"

    def _is_generic(self, text: str) -> bool:
        """Check if text is generic"""
        generic_phrases = [
            "keep up the good work",
            "stay focused",
            "you can do it",
            "great job",
            "well done"
        ]
        return any(phrase in text.lower() for phrase in generic_phrases)

    def _update_prompts_based_on_feedback(self, successful_patterns: Dict, improvement_areas: Dict):
        """Update LLM prompts based on feedback analysis"""
        self.logger.info(f"Successful patterns: {successful_patterns}")
        self.logger.info(f"Improvement areas: {improvement_areas}")

    def _save_personalization_rules(self, rules: Dict):
        """Save personalization rules for future use"""
        try:
            rules_json = json.dumps(rules, indent=2)

            with open('personalization_rules.json', 'w') as f:
                f.write(rules_json)

            self.logger.info("💾 Saved personalization rules")

        except Exception as e:
            self.logger.error(f"Error saving personalization rules: {e}")