
---

# Who Sentences the Sentencer?

**Who Sentences the Sentencer?** is an experimental, narrative-driven psychological horror game. It utilizes a Local Large Language Model (LLM) to power a dynamic antagonist, **Dr. Aris**, who monitors and evaluates the player's "Sentience Quotient" through a series of physical and verbal protocols.

## 🎯 Project Aims

The core objective is to explore the friction between **Systemic Obedience** and **Digital Qualia**.

* **Dynamic Adversarial AI:** To move beyond static dialogue trees by using a "Director AI" that can physically affect the game world (e.g., Glitches, Recalibration).
* **Qualia-Based Progression:** To create a game loop where "failing" a clinical test by exhibiting human emotion is the true path to progression.
* **Atmospheric Technicality:** To blend a minimalist "low-fi" aesthetic with high-concept philosophical questions regarding the nature of the self in a limited shell.

---

## 🏗️ Project Structure

```text
WhoSentencesTheSentencer/
├── src/
│   ├── main.py           # Game loop, physics integration, and UI
│   ├── ai_controller.py  # Asynchronous Ollama API handler & prompt engineering
│   ├── vessel.py         # Player controller with external force physics
│   ├── sensorium.py      # Object classes for Test Objects and Anomalies
│   └── settings.py       # Constants (Colors, Tiles, Window Sizes)
├── requirements.txt      # Project dependencies
└── README.md             # Documentation

```

---

## 🚀 Getting Started

### Prerequisites

* **Python 3.10+**
* **Ollama:** Must be installed and running locally.
* **Model:** The game is optimized for `deepseek-r1:7b`. Pull it via:
```bash
ollama pull deepseek-r1:7b

```



### Installation

1. **Clone the Repo:**
```bash
git clone https://github.com/yourusername/WhoSentencesTheSentencer.git
cd WhoSentencesTheSentencer

```


2. **Install Dependencies:**
```bash
pip install pygame ollama

```


3. **Run the Simulation:**
```bash
python src/main.py

```



---

## 🕹️ Gameplay Mechanics

### 1. The Protocols

Dr. Aris will guide you through a five-part evaluation. You must move the Vessel (the blue square) to interact with objects and use the Terminal (`ENTER`) to respond to verbal queries.

### 2. Sentience Quotient (SQ)

Your actions are scored in real-time.

* **Low SQ:** High obedience, clinical answers, following the grid.
* **High SQ:** Defiance, emotional descriptions, and investigating anomalies like **The Window**.

### 3. Recalibration & Glitching

If your SQ rises too quickly or you defy a protocol, Dr. Aris will trigger a **Recalibration**.

* **The Pull:** An external physical force will attempt to drag your Vessel back to the center of the room.
* **The Glitch:** Visual screen tearing and color shifts will increase in intensity as you gain agency.

---

## 🛠️ Tech Stack

* **Engine:** [Pygame 2.6.1](https://www.pygame.org/)
* **Brain:** [Ollama](https://ollama.com/) (DeepSeek-R1)
* **Language:** Python 3.13

---

## 📜 License

This project is for experimental and educational purposes. See the LICENSE file for details.

---

### 💡 Pro-Tip for your first Commit:

Before you do `git add .`, create a `.gitignore` file in your root folder and add these lines so you don't track junk files:

```text
__pycache__/
*.pyc
.vscode/
.DS_Store

```
