# Python Fighting Game 🥊

A 2D local multiplayer fighting game built with Python and Pygame. This project supports both local desktop play and web-based play via WebAssembly (Pygbag).

> **Note:**This is a Ultimate **vibe coding**  project.

## 🎮 Features
* **Local Multiplayer:** Two-player combat on a single keyboard.
* **Combat System:** Light/Heavy attacks, blocking, crouching, and aerial juggles.
* **Mechanics:** Health bars, stamina system for dashing, hitstun, and chip damage.
* **Round System:** Best of 3 rounds with a 60-second timer.

## 🕹️ Controls

| Action | Player 1 | Player 2 |
| :--- | :--- | :--- |
| **Move** | A / D | Left / Right Arrows |
| **Jump** | W | Up Arrow |
| **Crouch** | S | Down Arrow |
| **Attack (Light)** | F | K |
| **Attack (Heavy)** | G | L |
| **Block** | H | ; (Semicolon) |
| **Dash** | Left Shift | Right Shift |

## 📂 Project Structure
```bash
├── build/                      # Generated build directory (created by pygbag)
│   └── web/                    # Contains the deployable web version        
│   │   └── favilon.png         # Game icon
│   └── web-cahe/               # Internal cache for the web builder (pygbag)
│       └──489f...29eca.tmpl    # Go template file
│       └──38ee...28ed.png      #
│
├──fight_game/                  # Main source code directory
├── main.py                     # Core game loop and logic
├── script.js                   # Frontend JavaScript for web integration
├── styles.css                  # Styling for the web container
├── requirements.txt            # Python dependencies (pygame, pygbag)
├── version.json                # Versioning and build metadata
├── fight_game.apk              # Local package archive
├── favicon.png                 # Game icon
└── index.html                  # Template for web build
```
## 🛠️ Installation & Setup

### Prerequisites
* Python 3.10+
* pip

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```
### 2. Run Locally (Desktop Version)
To play the game directly on your computer:
```bash
python main.py
```
### 3. Run on Web (Browser Version)
To run the game in a browser using pygbag:
```bash
# This command converts the game to WebAssembly and serves it locally
pygbag .
```
Then open http://localhost:8000 in your browser.


