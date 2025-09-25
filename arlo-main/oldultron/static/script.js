// UI wiring for Flask backend
const consoleOutput = document.getElementById("consoleOutput");
const voiceBtn = document.getElementById("voiceBtn");
const voiceHint = document.getElementById("voiceHint");
const modeToggle = document.getElementById("modeToggle");
const modeLabel = document.getElementById("modeLabel");
const voiceSection = document.getElementById("voiceSection");
const textSection = document.getElementById("textSection");
const textForm = document.getElementById("textForm");
const textField = document.getElementById("textField");
const suggestions = document.querySelectorAll(".suggestion");

const synth = window.speechSynthesis;
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.continuous = false;
}

let listening = false;
let voiceMode = true;
let busy = false; // disables inputs while processing

// escape HTML
function escapeHtml(str) {
  return (str || "").toString().replace(/[&<>"'`=\/]/g, function (s) {
    return {
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
      "'": '&#39;', '/': '&#x2F;', '`': '&#x60;', '=': '&#x3D;'
    }[s];
  });
}

// append line to console
function appendConsoleLine(sender, text) {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const node = document.createElement("div");
  node.className = "console-line";
  node.innerHTML = `<strong>${sender} [${time}]:</strong> ${escapeHtml(text)}`;
  consoleOutput.appendChild(node);
  consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

// typewriter for reply
function typeReply(sender, text) {
  return new Promise((resolve) => {
    const container = document.createElement("div");
    container.className = "console-line";
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    container.innerHTML = `<strong>${sender} [${time}]:</strong> `;
    const span = document.createElement("span");
    container.appendChild(span);
    consoleOutput.appendChild(container);
    consoleOutput.scrollTop = consoleOutput.scrollHeight;

    let i = 0;
    function step() {
      if (i < text.length) {
        span.innerHTML += escapeHtml(text.charAt(i));
        i++;
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
        setTimeout(step, 10 + Math.random() * 15);
      } else {
        resolve();
      }
    }
    step();
  });
}

// speak (cancel previous)
function speak(text) {
  if (!('speechSynthesis' in window)) return;
  // stop any ongoing speech immediately
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1;
  u.pitch = 1;
  // ensure we don't start speaking if tab not visible? still speak
  synth.speak(u);
}

// set busy state (disable UI)
function setBusy(state) {
  busy = state;
  // voice + text disabled
  if (state) {
    voiceBtn.setAttribute("disabled", "true");
    voiceBtn.classList.add("disabled");
    if (textField) textField.setAttribute("disabled", "true");
    const sendBtn = document.querySelector(".send-btn");
    if (sendBtn) sendBtn.setAttribute("disabled", "true");
  } else {
    voiceBtn.removeAttribute("disabled");
    voiceBtn.classList.remove("disabled");
    if (textField) textField.removeAttribute("disabled");
    const sendBtn = document.querySelector(".send-btn");
    if (sendBtn) sendBtn.removeAttribute("disabled");
  }
}

// send message to Flask
async function sendMessageToServer(message) {
  if (busy) return;
  setBusy(true);
  appendConsoleLine("You", message);
  try {
    const res = await fetch("/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const json = await res.json();
    const reply = json.reply || "No reply from server.";
    // type reply
    await typeReply("ARLO", reply);
    // speak after typing starts (but ensure speech restarts from beginning)
    speak(reply);
  } catch (err) {
    appendConsoleLine("ARLO", "⚠️ Error contacting server.");
    console.error(err);
  } finally {
    setBusy(false);
  }
}

// mode toggle
modeToggle.addEventListener("click", () => {
  voiceMode = !voiceMode;
  if (voiceMode) {
    voiceSection.classList.remove("hidden");
    textSection.classList.add("hidden");
    modeLabel.textContent = "Text Mode";
    modeToggle.querySelector("#modeIcon").textContent = "💬";
  } else {
    voiceSection.classList.add("hidden");
    textSection.classList.remove("hidden");
    modeLabel.textContent = "Voice Mode";
    modeToggle.querySelector("#modeIcon").textContent = "🎙️";
  }
});

// voice handlers
if (recognition) {
  voiceBtn.addEventListener("click", () => {
    if (busy) return;
    if (!listening) {
      try {
        recognition.start();
      } catch (e) { /* ignored */ }
    } else {
      recognition.stop();
    }
  });

  recognition.onstart = () => {
    listening = true;
    voiceBtn.classList.add("listening");
    voiceHint.textContent = "Listening... Speak now";
    voiceBtn.setAttribute("aria-pressed", "true");
  };
  recognition.onend = () => {
    listening = false;
    voiceBtn.classList.remove("listening");
    voiceHint.textContent = "Click to start voice input";
    voiceBtn.setAttribute("aria-pressed", "false");
  };
  recognition.onerror = (e) => {
    listening = false;
    voiceBtn.classList.remove("listening");
    voiceHint.textContent = "Click to start voice input";
    appendConsoleLine("ARLO", "Voice recognition error: " + (e.error || "unknown"));
  };
  recognition.onresult = (ev) => {
    const txt = ev.results[0][0].transcript;
    // stop recognition to avoid duplicate events
    try { recognition.stop(); } catch (e) { /* ignore */ }
    sendMessageToServer(txt);
  };
} else {
  // hide voice UI if not supported
  voiceBtn.style.display = "none";
  voiceHint.textContent = "Voice not supported in this browser.";
}

// text form submit
if (textForm) {
  textForm.addEventListener("submit", (e) => {
    e.preventDefault();
    if (busy) return;
    const v = textField.value.trim();
    if (!v) return;
    textField.value = "";
    sendMessageToServer(v);
  });
}

// suggestion buttons
suggestions.forEach(btn => {
  btn.addEventListener("click", () => {
    const txt = btn.textContent.trim();
    if (!txt) return;
    if (voiceSection.classList.contains("hidden")) {
      textField.value = txt;
      textField.focus();
    } else {
      sendMessageToServer(txt);
    }
  });
});

// show initial demo messages quickly then clear
(async function intro() {
  const demo = [
    "> Initializing ARLO neural networks...",
    "> Loading language models...",
    "> Connecting to voice recognition system...",
    "> Web browsing capabilities enabled...",
    "> Ready for voice interaction.",
    "> ARLO online - How may I assist you?"
  ];
  for (let i = 0; i < demo.length; i++) {
    await typeReply("System", demo[i]);
    await new Promise(r => setTimeout(r, 200));
  }
})();