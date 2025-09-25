import os
import datetime
import random
import platform
import webbrowser
import requests
from flask import Flask, render_template, request, jsonify
import re

# Optional imports
try:
    import psutil
except ImportError:
    psutil = None

try:
    import wikipedia
except ImportError:
    wikipedia = None

# Screenshot (Windows/macOS)
try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

app = Flask(__name__, static_folder="static", template_folder="templates")

WOLFRAM_APPID = "3H5JG6QH52"

def norm(s: str) -> str:
    return (s or "").strip().lower()

# Improved intent system with more precise matching
INTENTS = {
    "self_introduction": {
        "patterns": [
            r"\bwho are you\b",
            r"\btell me about yourself\b",
            r"\bwhat are you\b",
            r"\bintroduce yourself\b",
            r"\babout you\b",
            r"\bwho is arlo\b"
        ],
        "responses": [
            "I am A.R.L.O. - Artificial Reasoning and Learning Operator. I'm an AI assistant designed to help you with various tasks including answering questions, opening applications, providing system information, and more. I use Wolfram Alpha for computational queries and Wikipedia for general knowledge.",
            "Hello! I'm ARLO, your AI assistant. I can help with calculations, opening applications, system monitoring, web searches, and general questions. I integrate with Wolfram Alpha for math and Wikipedia for information.",
            "I'm A.R.L.O., an intelligent assistant created to help you. I can perform calculations, open programs, check system status, answer questions using Wolfram Alpha and Wikipedia, and even open websites for you."
        ]
    },
    "greeting": {
        "patterns": [
            r"^(hello|hi|hey|hiya)\s*(arlo)?$",
            r"^(what's up|sup)\s*(arlo)?$",
            r"^(hey|hi)\s+arlo$"
        ],
        "responses": [
            "Hello Sir — ARLO online and ready to assist.",
            "Hi there! ARLO at your service. How may I help you today?",
            "Greetings Sir — systems are operational and ready."
        ]
    },
    "capabilities": {
        "patterns": [
            r"\bwhat can you do\b",
            r"\byour capabilities\b",
            r"\bwhat are your features\b",
            r"\bhelp me\b",
            r"\bwhat functions\b"
        ],
        "responses": [
            "I can help you with: ✓ Mathematical calculations ✓ Opening applications (YouTube, Google, Gmail, Notepad, Calculator) ✓ System information and battery status ✓ Taking screenshots ✓ Answering general knowledge questions ✓ Telling jokes ✓ Time and date queries ✓ Opening any .com website. Just ask me anything!",
        ]
    },
    "time": {
        "patterns": [
            r"\bwhat time\b",
            r"\btime is it\b",
            r"\btell me the time\b",
            r"\bcurrent time\b",
            r"\btime now\b"
        ],
        "reply_func": lambda q: f"The current time is {datetime.datetime.now().strftime('%I:%M:%S %p')}"
    },
    "date": {
        "patterns": [
            r"\bwhat date\b",
            r"\btoday's date\b",
            r"\bdate is it\b",
            r"\bwhat is the date\b",
            r"\btoday is\b"
        ],
        "reply_func": lambda q: f"Today's date is {datetime.date.today().strftime('%B %d, %Y')}"
    },
    "battery": {
        "patterns": [
            r"\bbattery\b",
            r"\bbattery status\b",
            r"\bbattery level\b",
            r"\bhow much battery\b",
            r"\bbattery percent\b"
        ],
        "reply_func": lambda q: f"Battery is at {psutil.sensors_battery().percent}%" if psutil and psutil.sensors_battery() else "Battery information not available on this system."
    },
    "system_info": {
        "patterns": [
            r"\bsystem info\b",
            r"\bsystem information\b",
            r"\bos info\b",
            r"\bcpu usage\b",
            r"\bram usage\b",
            r"\bsystem status\b",
            r"\bpc info\b",
            r"\bcomputer info\b"
        ],
        "reply_func": lambda q: f"System: {platform.system()} {platform.release()}. CPU usage: {psutil.cpu_percent(interval=0.5) if psutil else 'N/A'}%. RAM usage: {psutil.virtual_memory().percent if psutil else 'N/A'}%. Disk usage: {psutil.disk_usage('/').percent if psutil else 'N/A'}%."
    },
    "open_youtube": {
        "patterns": [
            r"\bopen youtube\b",
            r"\byoutube please\b",
            r"\byoutube\.com\b",
            r"\bgo to youtube\b",
            r"\blaunch youtube\b"
        ],
        "reply_func": lambda q: (webbrowser.open("https://youtube.com"), "Opening YouTube for you, Sir.")[1]
    },
    "open_google": {
        "patterns": [
            r"\bopen google\b",
            r"\bgoogle please\b",
            r"\bgo to google\b",
            r"\bopen www\.google\.com\b",
            r"\blaunch google\b"
        ],
        "reply_func": lambda q: (webbrowser.open("https://google.com"), "Opening Google Search.")[1]
    },
    "open_gmail": {
        "patterns": [
            r"\bopen gmail\b",
            r"\bopen mail\b",
            r"\bgmail please\b",
            r"\bopen google mail\b",
            r"\blaunch gmail\b"
        ],
        "reply_func": lambda q: (webbrowser.open("https://mail.google.com"), "Opening Gmail for you.")[1]
    },
    "open_website": {
        "patterns": [
            r"\bopen\s+(\w+)\.com\b",
            r"\bgo to\s+(\w+)\.com\b",
            r"\bvisit\s+(\w+)\.com\b",
            r"\blaunch\s+(\w+)\.com\b",
            r"\b(\w+)\.com\s+please\b"
        ],
        "reply_func": lambda q: open_website_by_name(q)
    },
    "screenshot": {
        "patterns": [
            r"\btake screenshot\b",
            r"\bscreenshot\b",
            r"\bgrab screen\b",
            r"\bcapture screen\b",
            r"\btake a screenshot\b"
        ],
        "reply_func": lambda q: (
            "Screenshot functionality not available (PIL ImageGrab not installed)." if not ImageGrab else (
                lambda: (
                    os.makedirs("screenshots", exist_ok=True),
                    ImageGrab.grab().save(os.path.join("screenshots", f"screenshot_{random.randint(1000,9999)}.png")),
                    "Screenshot captured and saved successfully."
                )[-1]
            )()
        )
    },
    "notepad": {
        "patterns": [
            r"\bopen notepad\b",
            r"\bstart notepad\b",
            r"\blaunch notepad\b"
        ],
        "reply_func": lambda q: (os.system("start notepad" if platform.system() == "Windows" else "open -a TextEdit"), "Opening text editor.")[1]
    },
    "calculator": {
        "patterns": [
            r"\bopen calculator\b",
            r"\bstart calculator\b",
            r"\blaunch calculator\b",
            r"\bopen calc\b"
        ],
        "reply_func": lambda q: (os.system("calc" if platform.system() == "Windows" else "open -a Calculator"), "Opening calculator application.")[1]
    },
    "joke": {
        "patterns": [
            r"\bjoke\b",
            r"\btell me a joke\b",
            r"\bmake me laugh\b",
            r"\bsay something funny\b",
            r"\bgive me a joke\b"
        ],
        "responses": [
            "Why don't scientists trust atoms? Because they make up everything!",
            "I told my computer I needed a break — it went to sleep mode.",
            "Why did the AI go to therapy? It had deep learning issues!",
            "What do you call a robot that takes the long way around? R2-Detour!",
            "Why was the computer cold? It left its Windows open!"
        ]
    }
}

def open_website_by_name(query: str):
    """Extract website name and open it"""
    import re
    
    # Extract website name from various patterns
    patterns = [
        r"\bopen\s+(\w+)\.com\b",
        r"\bgo to\s+(\w+)\.com\b", 
        r"\bvisit\s+(\w+)\.com\b",
        r"\blaunch\s+(\w+)\.com\b",
        r"\b(\w+)\.com\s+please\b"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            site_name = match.group(1)
            url = f"https://{site_name}.com"
            try:
                webbrowser.open(url)
                return f"Opening {site_name}.com for you."
            except Exception as e:
                return f"Sorry, I couldn't open {site_name}.com. Please check if it's a valid website."
    
    return "I couldn't identify which website you want to open. Try saying 'open [sitename].com'"

def wolfram_query(query_text: str):
    """Query Wolfram Alpha API with error handling"""
    if not WOLFRAM_APPID:
        return None
    try:
        response = requests.get(
            "https://api.wolframalpha.com/v1/result",
            params={"appid": WOLFRAM_APPID, "i": query_text},
            timeout=8
        )
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Wolfram API error: {e}")
        return None

def wikipedia_query(query_text: str):
    """Query Wikipedia with better error handling"""
    if not wikipedia:
        return None
    try:
        # Clean the query for better Wikipedia search
        clean_query = re.sub(r'\b(tell me about|information about|about)\b', '', query_text, flags=re.IGNORECASE).strip()
        if not clean_query:
            return None
            
        summary = wikipedia.summary(clean_query, sentences=3)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            # Try with the first suggestion
            summary = wikipedia.summary(e.options[0], sentences=2)
            return f"{summary}\n\n(Showing results for '{e.options[0]}'. Multiple topics found with this name.)"
        except:
            return f"Multiple topics found for '{clean_query}'. Could you be more specific? Options include: {', '.join(e.options[:5])}"
    except wikipedia.exceptions.PageError:
        return None
    except Exception as e:
        print(f"Wikipedia error: {e}")
        return None

def match_intent(query: str):
    """Improved intent matching using regex patterns"""
    query_lower = query.lower().strip()
    
    for intent_name, intent_data in INTENTS.items():
        patterns = intent_data.get("patterns", [])
        for pattern in patterns:
            if re.search(pattern, query_lower):
                return intent_name, intent_data
    
    return None, None

def process_query(raw_text: str) -> str:
    """Process user query with improved intent matching and fallbacks"""
    q = norm(raw_text)
    if not q:
        return "I didn't catch that. Could you please repeat?"
    
    # Try intent matching first
    intent_name, intent_data = match_intent(raw_text)
    
    if intent_data:
        # Handle responses
        if "responses" in intent_data:
            return random.choice(intent_data["responses"])
        elif "reply_func" in intent_data:
            try:
                return intent_data["reply_func"](raw_text)
            except Exception as e:
                print(f"Error processing {intent_name}: {e}")
                return f"Sorry, I encountered an error processing that request."
    
    # If no intent matches, try computational/factual queries
    
    # Check if it looks like a math problem
    math_indicators = ['calculate', 'compute', '+', '-', '*', '/', '^', 'square', 'root', 'sin', 'cos', 'tan', 'log']
    if any(indicator in q for indicator in math_indicators) or any(char.isdigit() for char in q):
        wolfram_result = wolfram_query(raw_text)
        if wolfram_result:
            return wolfram_result
    
    # Try Wolfram Alpha for general queries
    wolfram_result = wolfram_query(raw_text)
    if wolfram_result and len(wolfram_result.strip()) > 3:
        return wolfram_result
    
    # Try Wikipedia for informational queries
    wiki_result = wikipedia_query(raw_text)
    if wiki_result:
        return wiki_result
    
    # Ultimate fallback
    return "I don't have specific information about that right now. You can try rephrasing your question, or I can help you with calculations, opening applications, system info, or general knowledge questions. What would you like to know?"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process_route():
    data = request.get_json() or {}
    message = data.get("message", "")
    reply = process_query(message)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    print("🤖 ARLO AI Assistant Starting...")
    print("🌐 Access your assistant at: http://localhost:5000")
    print("✨ Features: Voice commands, calculations, system info, web browsing")
    app.run(debug=True, port=5000)