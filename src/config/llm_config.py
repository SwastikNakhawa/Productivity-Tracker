# config/llm_config.py
LLM_CONFIG = {
    "default_model": "mistral",
    "fallback_model": "llama2",
    "base_url": "http://localhost:11434",
    "timeout": 30,
    "max_retries": 3,

    "prompt_templates": {
        "motivational": {
            "system": "You are a motivational coach. Provide short, inspiring quotes.",
            "user": "Current activity: {app_name} (score: {score}). Generate motivational quote:"
        },
        "recommendations": {
            "system": "You are a learning advisor. Provide specific study recommendations.",
            "user": "User's productive categories: {categories}. Provide 3-4 study recommendations:"
        }
    },

    "fallback_responses": {
        "motivational": [
            "Stay focused and keep making progress! 💪",
            "Every minute counts toward your goals! 🚀",
            "Consistency is the key to mastery! 🔑"
        ],
        "recommendations": [
            "Practice consistently with daily learning sessions",
            "Build projects to apply your knowledge",
            "Join online communities for support and learning"
        ]
    }
}