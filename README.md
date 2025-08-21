# Ecotrack Carbon Footprint Tracker

## 🌍 Overview
**Ecotrack** is a Python-based web application designed to help users monitor and manage their carbon footprint. It allows users to log daily activities, calculate their emissions, and track their environmental impact over time.

## ✨ Features
- 📝 **Activity Logging** – Record activities that contribute to carbon emissions
- 📊 **Carbon Footprint Calculation** – Estimate emissions based on user input
- 💾 **Database Storage** – Uses SQLite for persistent data storage
- ✅ **Comprehensive Testing** – Includes `test_comprehensive.py` with results in `test_results.txt`
- 🎨 **Template-Based UI** – Simple and clean frontend using HTML templates

## 🛠️ Tech Stack
- **Python (Flask framework)** – Backend
- **SQLite** – Database
- **HTML/CSS** – Frontend templates
- **Pytest/Unittest** – Testing

## 🚀 Getting Started

### Prerequisites
- Python 3.7+
- Virtual environment tool (`venv` recommended)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Samarth-170904/EcotrackCarbonFootprintTracker.git
cd EcotrackCarbonFootprintTracker
```

2. **Create and activate a virtual environment**

On Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

On macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python app.py
```
Then open `http://localhost:5000` in your browser.

### Running Tests
```bash
pytest test_comprehensive.py
# or
python test_comprehensive.py
```
Check `test_results.txt` for results.

## 📂 Project Structure
```text
EcotrackCarbonFootprintTracker/
├── app.py
├── ecotrack.db
├── requirements.txt
├── test_comprehensive.py
├── test_results.txt
├── templates/
├── venv/
├── __pycache__/
├── .vscode/
└── README.md
```

## 🔮 Future Enhancements
- User authentication & profiles
- Data visualization dashboard
- Export reports (CSV/JSON)
- Cloud deployment (Heroku, Render, etc.)

## 🤝 Contributing
Contributions are welcome!

1. Fork the repo
2. Create a feature branch
```bash
git checkout -b feature/YourFeature
```
3. Commit your changes
```bash
git commit -m "Add feature"
```
4. Push the branch
```bash
git push origin feature/YourFeature
```
5. Open a Pull Request

## 📜 License
This project is licensed under the MIT License.

## 📧 Contact
For any questions or suggestions, feel free to reach out via GitHub issues.
