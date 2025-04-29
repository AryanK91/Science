import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class UserData:
    def __init__(self):
        self.users_dir = "user_data"
        os.makedirs(self.users_dir, exist_ok=True)

    def _get_user_file_path(self, username: str) -> str:
        """Get the file path for a user's data file"""
        return os.path.join(self.users_dir, f"{username}.json")

    def _load_user(self, username: str) -> Dict:
        """Load a single user's data"""
        file_path = self._get_user_file_path(username)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                if "progress" in data:
                    data["progress"]["topics_covered"] = set(data["progress"]["topics_covered"])
                return data
        return None

    def _save_user(self, username: str, data: Dict):
        """Save a single user's data"""
        file_path = self._get_user_file_path(username)
        save_data = data.copy()
        
        if "progress" in save_data:
            save_data["progress"] = save_data["progress"].copy()
            save_data["progress"]["topics_covered"] = list(save_data["progress"]["topics_covered"])
        
        with open(file_path, 'w') as f:
            json.dump(save_data, f, indent=4)

    def create_user(self, username: str) -> Dict:
        """Create or get a user"""
        # Try to load existing user
        existing_data = self._load_user(username)
        if existing_data:
            return existing_data

        # Create new user
        new_user = {
            "username": username,
            "chat_history": [],
            "progress": {
                "total_questions": 0,
                "correct_answers": 0,
                "last_session": datetime.now().isoformat(),
                "topics_covered": set()
            }
        }
        self._save_user(username, new_user)
        return new_user

    def update_chat_history(self, username: str, message: str, is_user: bool):
        """Update a user's chat history"""
        user_data = self._load_user(username) or self.create_user(username)
        
        user_data["chat_history"].append({
            "role": "user" if is_user else "ai",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 50 messages
        if len(user_data["chat_history"]) > 50:
            user_data["chat_history"] = user_data["chat_history"][-50:]

        self._save_user(username, user_data)

    def get_chat_history(self, username: str) -> List[Dict]:
        """Get a user's chat history"""
        user_data = self._load_user(username)
        return user_data["chat_history"] if user_data else []

    def update_progress(self, username: str, topic: str, is_correct: bool):
        """Update a user's progress"""
        user_data = self._load_user(username) or self.create_user(username)
        
        progress = user_data["progress"]
        progress["total_questions"] += 1
        if is_correct:
            progress["correct_answers"] += 1
        progress["topics_covered"].add(topic)
        progress["last_session"] = datetime.now().isoformat()
        
        self._save_user(username, user_data)

    def get_progress(self, username: str) -> Dict:
        """Get a user's progress"""
        user_data = self._load_user(username)
        if not user_data:
            return None
        
        progress = user_data["progress"]
        return {
            "username": username,
            "total_questions": progress["total_questions"],
            "correct_answers": progress["correct_answers"],
            "accuracy": (progress["correct_answers"] / progress["total_questions"] * 100) if progress["total_questions"] > 0 else 0,
            "topics_covered": list(progress["topics_covered"]),
            "last_session": progress["last_session"]
        }

# Create a global instance
user_data = UserData() 