<<<<<<< HEAD
# PLNetworkBot-JBResidency
=======
# PLNetworkBot-JBResidency

This repository contains the codebase for the PLNetworkBot-JBResidency project.

## Prerequisites

- Python 3.8 or later
- Virtual environment (optional, but recommended)
- `python-dotenv` package for environment variable management
- Telegram Bot API Key
- Gemini Flash API Key
- Discourse API credentials

## Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tkkr6895/PLNetworkBot-JBResidency.git
   cd PLNetworkBot-JBResidency
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up API keys and credentials:**
   - Create a `.env` file in the root directory of the project to store your API keys and credentials:
     ```
     TELEGRAM_TOKEN=your-telegram-token
     GEMINI_API_KEY=your-gemini-api-key
     DISCOURSE_API_KEY=your-discourse-api-key
     DISCOURSE_USERNAME=your-discourse-username
     ```
   - Replace `your-telegram-token`, `your-gemini-api-key`, `your-discourse-api-key`, and `your-discourse-username` with the actual values.

5. **Add the `.env` file to `.gitignore` to keep your credentials secure:**
   - Open the `.gitignore` file (or create one if it doesn't exist) in the root directory and add the following line:
     ```
     .env
     ```

6. **Updating the Knowledge Base:**
   - If you're updating the knowledge base with newer files, execute `create_embeddings.py` to update the embeddings stored in `faiss_index`.
   - Ensure that the documents are in the same folder as the script unless you've configured the code to specify a different path.

## Running the Bot

After completing the setup, you can run the bot using the following command:
```bash
python telegram_discourse_bot.py
```

>>>>>>> cb32cd1 (Initial commit: Added bot codebase, knowledge base and README)
