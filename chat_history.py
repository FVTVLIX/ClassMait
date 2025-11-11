# chat_history.py

import json
import os
from datetime import datetime

class ChatHistoryManager:
    def __init__(self, history_file="chat_history.json"):
        self.history_file = history_file
        self.sessions = {}
        self.load_history()
        print("📦 ChatHistoryManager initialized. Sessions loaded:", list(self.sessions.keys()))

    def load_history(self):
        """Load chat history from file."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.sessions = json.load(f)
                    print("📂 load_history: Successfully loaded sessions from file.")
            else:
                self.sessions = {"default": []}
                print("📂 load_history: No file found, created default session.")
        except Exception as e:
            print(f"❌ ERROR in load_history: {e}")
            self.sessions = {"default": []}

    def save_history(self):
        """Save chat history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
                print(f"💾 save_history: Successfully saved {len(self.sessions)} sessions.")
        except Exception as e:
            print(f"❌ ERROR in save_history: {e}")

    def create_session(self, title="Untitled Chat"):
        """Create a new chat session."""
        try:
            session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.sessions[session_id] = {
                "title": title,
                "created_at": datetime.now().isoformat(),
                "messages": []
            }
            print(f"✅ create_session: Created session '{session_id}' with title '{title}'")
            self.save_history()
            return session_id
        except Exception as e:
            print(f"❌ ERROR in create_session: {e}")
            return None

    def delete_session(self, session_id):
        """Delete a chat session."""
        try:
            if session_id in self.sessions:
                del self.sessions[session_id]
                print(f"🗑️ delete_session: Deleted session '{session_id}'")
                self.save_history()
        except Exception as e:
            print(f"❌ ERROR in delete_session: {e}")

    def get_session_messages(self, session_id):
        """Get messages from a specific session."""
        try:
            messages = self.sessions.get(session_id, {}).get("messages", [])
            print(f"📝 get_session_messages: Found {len(messages)} messages for session '{session_id}'")
            return messages
        except Exception as e:
            print(f"❌ ERROR in get_session_messages: {e}")
            return []

    def get_session_title(self, session_id):
        """Get the title of a session."""
        try:
            title = self.sessions.get(session_id, {}).get("title", "Untitled")
            print(f"📝 get_session_title: Found title '{title}' for session '{session_id}'")
            return title
        except Exception as e:
            print(f"❌ ERROR in get_session_title: {e}")
            return "Untitled"

    def get_recent_sessions(self, limit=10):
        """Get recent chat sessions. THIS IS THE CRITICAL FUNCTION."""
        try:
            if not self.sessions:
                print("📂 get_recent_sessions: No sessions exist.")
                return {}

            # Create a list of (session_id, session_data) tuples for sorting
            session_list = []
            print(f"🔍 get_recent_sessions: Building session list from {len(self.sessions)} sessions...")
            for session_id, session_data in self.sessions.items():
                session_list.append((session_id, session_data))
                print(f"  - Added tuple: ({session_id}, {session_data.get('title', 'No Title')})")

            # THE FIX: Sort using the session_data tuple
            sorted_sessions = sorted(
                session_list,
                key=lambda session_tuple: session_tuple[1]["created_at"], # <<< CORRECT INDEX
                reverse=True
            )
            
            print(f"✅ get_recent_sessions: Sorted sessions. Count: {len(sorted_sessions)}")
            
            # Convert back to dictionary
            result_dict = {}
            for session_id, session_data in sorted_sessions[:limit]:
                result_dict[session_id] = session_data
                print(f"  - Added to result: ({session_id}, {session_data.get('title', 'No Title')})")
            
            print(f"🎉 get_recent_sessions: Returning final dict with {len(result_dict)} sessions.")
            return result_dict

        except Exception as e:
            print(f"❌ CRITICAL ERROR in get_recent_sessions: {e}")
            print(f"   Type of session_list: {type(session_list)}")
            print(f"   Contents of session_list: {session_list[:2]}")
            return {}