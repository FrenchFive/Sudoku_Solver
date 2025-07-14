# 🧩 Sudoku Solver

Welcome to **Sudoku Solver**, a Python-based tool designed to solve Sudoku puzzles with a brute-force algorithm. 🖥️✨

---

## ✨ Features

- 🚀 **Brute-Force Algorithm**: Systematically solves Sudoku puzzles by exploring all valid possibilities.
- 📋 **Flexible Input**: Easily input puzzles in a standard 9x9 grid format.
- ⚡ **Efficient Execution**: Optimized for quick solutions to standard Sudoku grids.
- 🎹 **Simulation Mode**: Automatically types the solved grid into any active window using the Python `keyboard` module.

---

## 🛠️ Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/FrenchFive/Sudoku_Solver.git
   ```
2. **Navigate to the Directory**:
   ```bash
   cd Sudoku_Solver
   ```
3. **Install Python**: Ensure Python 3.x is installed. Download it from the [official Python website](https://www.python.org/downloads/).

## 🔧 Usage

1. Run the solver:
   ```bash
   python main.py
   ```
   Open the printed address in your browser, enter your puzzle and press **Solve**.
   The puzzle is saved to `sudoku_save.txt`, solved locally, and the solution is shown on the page. The solved grid is written back to `sudoku_save.txt`.
   Use the **Clear** button on the page to reset the grid and overwrite `sudoku_save.txt` with zeros.
   After a solution appears, click **SIMULATE** to have the solver type the grid for you. Make sure the desired window is active during the 5-second countdown.

4. **Paste from Clipboard**:
   You can grab a screenshot of a Sudoku board and paste it directly into the solver:
   - Copy the board image to your clipboard.
   - Click **Clipboard** on the web page.
   - The solver attempts to read the grid from the image and fills the cells automatically.
   This feature requires the Python packages `pillow` and `pytesseract` as well as a working Tesseract OCR installation.

---

## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 🌟 Acknowledgments

- 🙏 Special thanks to the open-source community for inspiration and tools.
- 🧠 Inspired by the beauty and logic of Sudoku puzzles.

---