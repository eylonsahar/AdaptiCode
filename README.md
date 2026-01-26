# AdaptiCode

**AdaptiCode** is an Intelligent Tutoring System (ITS) designed to help students learn recursion through adaptive, personalized practice. The system uses Item Response Theory (IRT) to model student ability, selects appropriate questions dynamically, and provides AI-powered feedback and explanations.

## Features

- **Adaptive Question Selection**: Uses IRT-based modeling to select questions that match the student's current ability level
- **AI-Powered Feedback**: Generates personalized explanations and hints using Large Language Models (LLMs)
- **Code Execution & Testing**: Safely executes student code against predefined test cases
- **Progress Tracking**: Monitors student performance and concept mastery over time
- **Interactive Web Interface**: Clean, modern UI for practicing recursion problems

## Project Structure

```
AdaptiCode/
├── backend/
│   ├── api/                    # Flask API routes and application setup
│   ├── business_logic/         # Core system logic (IRT, selection, feedback, LLM)
│   ├── data/                   # Data models and management
│   └── config.py               # Configuration settings
├── data/
│   ├── questions/              # Question bank organized by topic
│   ├── user_data.json          # Persisted user profiles (gitignored)
│   └── interaction_log.json    # User interaction history (gitignored)
├── frontend/                   # Frontend JavaScript and CSS
├── static/                     # Static assets (CSS, JS)
├── templates/                  # HTML templates
├── prompts/                    # LLM prompt templates
├── requirements.txt            # Python dependencies
└── run.py                      # Main entry point to start the server
```

## Prerequisites

- **Python**: 3.8 or higher
- **pip**: Python package manager
- **Groq API Key**: You'll need an API key for Groq (free tier available)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/eylonsahar/AdaptiCode.git
cd AdaptiCode
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Groq API Key

The system uses Groq for generating AI-powered feedback and explanations.



Edit the `.env` file in the project root and replace `your_groq_api_key_here` with your actual API key:

```bash
# Edit the .env file and add your Groq API key
GROQ_API_KEY=your_actual_api_key_here
```

**Getting API Key:**
- **Groq** (Free): https://console.groq.com/keys


## Running the Application

### Start the Server

```bash
python3 run.py
```

You should see output like:

```
============================================================
AdaptiCode - Adaptive Learning System for Recursion
============================================================

Starting server on http://0.0.0.0:5001

To use the system (single server):
1. Keep this server running
2. Open http://localhost:5001/ in your browser
   - Cover page is at '/' (home)
   - Practice page with editor is at '/question'

Press Ctrl+C to stop the server
============================================================
```

### Access the Application

Open your web browser and navigate to:

```
http://localhost:5001 or http://127.0.0.1:5001
```


## License

This project is available for educational purposes. Please contact the author for other uses.

## Acknowledgments

- Built with Flask, NumPy, and modern web technologies
- Uses IRT theory for adaptive learning
- Powered by state-of-the-art LLMs for personalized feedback
- Model selection based on: Barla, M., Bieliková, M., Ezzeddinne, A. B., Kramár, T., Šimko, M., & Vozár, O. (2010). On the impact of adaptive test question selection for learning efficiency. Computers & Education, 55(2), 846-857

## Contact

For questions or feedback about this project, please open an issue on GitHub.

---

**Happy Learning! 🚀**
