# Claims Scrubber for UAE 🏥

An automated, 100% offline desktop application built for the UAE healthcare sector to ingest insurance claims, group line items, and validate medical codes against custom pairwise error rules (ICD/CPT).

## 🚀 Key Features

* **100% Offline & Secure:** Runs locally with a temporary SQLite database that securely auto-wipes on exit.
* **Dynamic Rule Engine:** Instantly add, view, or remove custom coding conflict checks.
* **Built-in Reference Handbook:** Fast search across local ICD and CPT code definitions and categories.
* **Audit & Export:** Flags incorrect claim combinations line-by-line and exports formatted Excel audit reports ready for submission.

## 🛠️ Tech Stack

* **UI:** Streamlit
* **Database & Core:** Python, SQLite
* **Data Processing:** Pandas, OpenPyXL

## ⚙️ Quick Start

1. Clone or download the repository.
2. Install the required dependencies:
```bash
pip install streamlit pandas openpyxl

```


3. Run the application:
```bash
streamlit run app.py

```
