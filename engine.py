import sqlite3
import pandas as pd
import xml.etree.ElementTree as ET
import os
import sys
import csv

DB_NAME = "scrubber_local.db"

def get_base_dir():
    """Returns the absolute directory where engine.py is located."""
    try:
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.path.abspath(".")

def init_local_db():
    db_path = os.path.join(get_base_dir(), DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Rules Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS validation_rules (
            rule_id TEXT PRIMARY KEY,
            rule_name TEXT NOT NULL,
            code_1 TEXT NOT NULL,
            code_2 TEXT NOT NULL,
            description TEXT NOT NULL
        )
    ''')
    
    # Reference Handbook Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reference_handbook (
            code TEXT PRIMARY KEY,
            code_type TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL
        )
    ''')
    conn.commit()
    
    # Seed Rules from validation_rules.csv if empty
    cursor.execute("SELECT COUNT(*) FROM validation_rules")
    if cursor.fetchone()[0] == 0:
        rules_path = os.path.join(get_base_dir(), "validation_rules.csv")
        if os.path.exists(rules_path):
            try:
                with open(rules_path, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        r_id = r.get('rule_id', '').strip()
                        if r_id:
                            cursor.execute("INSERT OR REPLACE INTO validation_rules VALUES (?, ?, ?, ?, ?)", (
                                r_id,
                                r.get('rule_name', '').strip(),
                                r.get('code_1', '').strip().upper(),
                                r.get('code_2', '').strip().upper(),
                                r.get('description', '').strip()
                            ))
                conn.commit()
            except Exception as e:
                print(f"Error seeding rules: {e}")

    # Seed Reference Codes from reference_codes.csv if empty
    cursor.execute("SELECT COUNT(*) FROM reference_handbook")
    if cursor.fetchone()[0] == 0:
        refs_path = os.path.join(get_base_dir(), "reference_codes.csv")
        if os.path.exists(refs_path):
            try:
                with open(refs_path, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        code = r.get('code', '').strip().upper()
                        if code:
                            cursor.execute("INSERT OR REPLACE INTO reference_handbook VALUES (?, ?, ?, ?)", (
                                code,
                                r.get('code_type', 'ICD').strip().upper(),
                                r.get('description', '').strip(),
                                r.get('category', 'General').strip()
                            ))
                conn.commit()
            except Exception as e:
                print(f"Error seeding references: {e}")

    conn.close()

def parse_xml_file(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    records = []
    for child in root:
        record = {}
        for elem in child.iter():
            if elem.text and elem.text.strip():
                record[elem.tag] = elem.text.strip()
        if record:
            records.append(record)
    return pd.DataFrame(records)

def load_claims_file(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith('.csv'):
        df = pd.read_csv(uploaded_file, dtype=str, encoding='utf-8-sig', engine='python', on_bad_lines='skip')
    elif filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(uploaded_file, dtype=str)
    elif filename.endswith('.xml'):
        df = parse_xml_file(uploaded_file)
    else:
        raise ValueError("Unsupported file format. Please upload CSV, Excel, or XML.")
    return df.fillna("").astype(str)

def get_code_info(code):
    db_path = os.path.join(get_base_dir(), DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT description, category FROM reference_handbook WHERE code = ?", (code.upper(),))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"description": res[0], "category": res[1]}
    return {"description": "Description not found in handbook", "category": "General"}

def get_active_rules():
    db_path = os.path.join(get_base_dir(), DB_NAME)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM validation_rules")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_rule_to_db(rule_id, name, code_1, code_2, desc):
    db_path = os.path.join(get_base_dir(), DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO validation_rules VALUES (?, ?, ?, ?, ?)", (
        rule_id, name, code_1.strip().upper(), code_2.strip().upper(), desc
    ))
    conn.commit()
    conn.close()

def delete_rule_from_db(rule_id):
    db_path = os.path.join(get_base_dir(), DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM validation_rules WHERE rule_id = ?", (rule_id,))
    conn.commit()
    conn.close()

def group_and_validate_claims(df, col_mapping, rules):
    claim_col = col_mapping['claim_id']
    code_col = col_mapping['code']
    
    grouped = {}
    for _, row in df.iterrows():
        cid = str(row.get(claim_col, '')).strip()
        code = str(row.get(code_col, '')).strip().upper()
        if not cid or not code:
            continue
            
        if cid not in grouped:
            grouped[cid] = set()
        grouped[cid].add(code)
        
    flagged = []
    for cid, codes in grouped.items():
        for rule in rules:
            c1 = rule['code_1']
            c2 = rule['code_2']
            if c1 in codes and c2 in codes:
                info1 = get_code_info(c1)
                info2 = get_code_info(c2)
                flagged.append({
                    'Claim ID': cid,
                    'Rule ID': rule['rule_id'],
                    'Rule Name': rule['rule_name'],
                    'Conflicting Codes': f"{c1} & {c2}",
                    'Code 1 Details': f"{c1}: {info1['description']}",
                    'Code 2 Details': f"{c2}: {info2['description']}",
                    'Description': rule['description']
                })
                
    return pd.DataFrame(flagged), grouped

def cleanup_local_files():
    """Deletes the local SQLite database file upon exit."""
    db_path = os.path.join(get_base_dir(), DB_NAME)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
