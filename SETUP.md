# ClassMateAI - Setup & Usage Guide

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## Session Persistence

The app now automatically saves your session data, so you won't lose your progress when you refresh the page!

### What Gets Saved?
- ✅ Your API key
- ✅ All chat history (last 10 threads)
- ✅ Your selected learning level
- ✅ Current active chat thread

### Important Note About PDFs
**After refreshing the page, you'll need to re-upload and process your PDF.**

This is because the RAG system (which processes your textbook) cannot be saved to disk. However:
- Your chat history is preserved
- Your API key is saved
- You just need to upload the same PDF again and process it
- Then you can continue chatting with all your previous conversations intact

### How It Works

#### Option 1: Automatic Session Saving (Easiest)
The app automatically saves your session to `session_state.json` after every interaction:
- When you enter your API key
- When you send a message
- When you create/switch/delete chat threads

Just refresh the page and you'll continue right where you left off!

#### Option 2: Permanent API Key Storage (Recommended)
Never enter your API key again by storing it permanently:

1. Open `.streamlit/secrets.toml` in your project directory
2. Uncomment this line:
   ```toml
   OPENAI_API_KEY = "sk-your-api-key-here"
   ```
3. Replace `"sk-your-api-key-here"` with your actual OpenAI API key
4. Save the file and restart the app

**Your API key will be automatically loaded on every startup!**

> **Security Note:** The `secrets.toml` file is gitignored, so your API key won't be committed to version control.

### Managing Your Session

#### Save Session Manually
Go to **Settings** (⚙️ button in the sidebar) and click **💾 Save Session**

#### Clear All Data
If you want to start fresh:
1. Go to **Settings** (⚙️ button in the sidebar)
2. Click **🗑️ Clear All Data**
3. This will delete your saved session and reset the app

## Features

### Chat History
- View your last 10 conversation threads in the left sidebar
- Create new chats with the **➕ New Chat** button
- Switch between conversations by clicking on them
- Delete unwanted threads with the 🗑️ icon
- Active conversation is marked with 🟢

### Learning Levels
Choose from three difficulty levels:
- **Beginner**: Simple explanations with examples
- **Intermediate**: More detailed technical content
- **Expert**: Advanced, in-depth responses

### UI Features
- Modern gradient design with smooth animations
- Dark-themed sidebar with light chat area
- Auto-generated chat titles from first message
- Smart timestamps (shows time/date/year based on age)
- Responsive layout that works on all screen sizes

## Troubleshooting

### "API key not found" error
- Make sure you've entered a valid OpenAI API key
- Check that `.streamlit/secrets.toml` is formatted correctly if using Option 2
- Verify your API key at https://platform.openai.com/account/api-keys

### Session not loading on refresh
- Check that `session_state.json` exists in your project directory
- Look for any error messages in the terminal where Streamlit is running
- Try manually saving your session from the Settings page

### Lost chat history
- Chat threads are automatically saved after each interaction
- If you cleared your browser cache, the RAG system will need to be reinitialized
- You may need to re-upload your textbook PDF

## File Structure

```
ClassMait/
├── app.py                      # Main application
├── rag_system.py              # RAG implementation
├── quiz_generator.py          # Quiz generation
├── requirements.txt           # Python dependencies
├── session_state.json         # Auto-saved session data (created automatically)
├── .streamlit/
│   └── secrets.toml          # API key storage (add your key here)
├── textbooks/                # Your uploaded PDFs
└── chroma_db/                # Vector database (auto-generated)
```

## Getting Your OpenAI API Key

1. Visit https://platform.openai.com/account/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Add it to `.streamlit/secrets.toml` or enter it in the app

## Support

For issues or questions, please open an issue on GitHub.

---

**Enjoy your AI-powered learning experience! 🧠✨**
