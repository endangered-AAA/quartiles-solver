# ============================================================
# Quartiles Solver v3.1 — Full Version (Clean, Safe)
# ============================================================

import os, re, datetime, shutil, glob
from openai import OpenAI

# --- Secure API Key handling ---
# Your key is read from environment variable (export OPENAI_API_KEY="sk-...")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=OPENAI_API_KEY if OPENAI_API_KEY else None)

BLOCKLIST_FILE = "blocklist.txt"


# ============================================================
# Backup / Maintenance
# ============================================================

def backup_blocklist():
    if not os.path.exists(BLOCKLIST_FILE):
        return
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = f"blocklist_backup_{ts}.txt"
    try:
        shutil.copy(BLOCKLIST_FILE, name)
        print(f"💾 Backup created: {name}")
    except Exception as e:
        print("⚠️ Could not create backup:", e)


def clean_blocklist_file():
    if not os.path.exists(BLOCKLIST_FILE):
        open(BLOCKLIST_FILE, "w").close()
        return

    cleaned = set()
    with open(BLOCKLIST_FILE) as f:
        for line in f:
            w = line.strip().lower()
            if not w:
                continue
            if w.startswith("#") or w.startswith("-"):
                continue
            if all(c.isalpha() or c == "-" for c in w):
                cleaned.add(w)

    with open(BLOCKLIST_FILE, "w") as f:
        for w in sorted(cleaned):
            f.write(w + "\n")

    print(f"🧹 Cleaned {BLOCKLIST_FILE} ({len(cleaned)} valid entries).")


def restore_latest_backup():
    backups = sorted(
        glob.glob("blocklist_backup_*.txt"),
        key=os.path.getmtime,
        reverse=True
    )
    if not backups:
        print("⚠️  No backups found to restore.")
        return
    latest = backups[0]
    try:
        shutil.copy(latest, BLOCKLIST_FILE)
        print(f"🔄 Restored {BLOCKLIST_FILE} from {latest}.")
    except Exception as e:
        print("⚠️  Could not restore backup:", e)


# ============================================================
# Blocklist helpers
# ============================================================

def load_blocklist():
    if not os.path.exists(BLOCKLIST_FILE):
        open(BLOCKLIST_FILE, "w").close()
    valid = set()
    with open(BLOCKLIST_FILE) as f:
        for line in f:
            w = line.strip().lower()
            if not w:
                continue
            if w.startswith("#") or w.startswith("-"):
                continue
            if all(c.isalpha() or c == "-" for c in w):
                valid.add(w)
    return valid


def save_blocklist(words):
    with open(BLOCKLIST_FILE, "w") as f:
        for w in sorted(words):
            f.write(w + "\n")


def add_invalid(word):
    words = load_blocklist()
    w = word.strip().lower()
    if not w:
        print("Please provide a non-empty word.")
        return
    if not all(c.isalpha() or c == "-" for c in w):
        print("Only letters and hyphens are allowed.")
        return
    if w in words:
        print(f"'{w}' is already in the blocklist.")
    else:
        words.add(w)
        save_blocklist(words)
        print(f"✅ Added '{w}' to the blocklist!")


def show_blocklist():
    words = load_blocklist()
    if not words:
        print("(No blocked words yet.)")
    else:
        print("Blocked words:")
        for w in sorted(words):
            print("-", w)


def debug_blocklist_path():
    full_path = os.path.abspath(BLOCKLIST_FILE)
    print(f"\n🔍 Blocklist file path:\n{full_path}\n")
    if not os.path.exists(BLOCKLIST_FILE):
        print("⚠️  The file does NOT exist yet!")
        return
    print("📄 Current file contents:\n")
    with open(BLOCKLIST_FILE) as f:
        data = f.read().strip()
        if data:
            print(data)
        else:
            print("(File exists but is empty.)")


# ============================================================
# GPT interaction
# ============================================================

def detect_potential_invalids(text, existing_blocklist):
    lines = re.findall(r'(?im)^\s*INVALID\s*:\s*(.+)$', text)
    if not lines:
        return []
    joined = " ".join(lines)
    tokens = re.split(r'[,\s]+', joined)
    stop = {
        'word','words','tile','tiles','invalid','blocked',
        'example','sample','placeholder','unusable','none'
    }
    out = []
    for tok in tokens:
        w = re.sub(r'[^a-zA-Z-]', '', tok).lower()
        if not w or w in stop:
            continue
        if not (2 <= len(w) <= 20):
            continue
        if w in existing_blocklist:
            continue
        out.append(w)
    return sorted(set(out))


def solve_puzzle(tiles):
    words = load_blocklist()
    blocklist_text = "\n".join(sorted(words)) or "(none)"
    print("\n🧩 Sending puzzle to GPT...")
    print("(This may take a few seconds...)\n")

    if not OPENAI_API_KEY:
        print("⚠️ OPENAI_API_KEY is not set. Run:")
        print('   export OPENAI_API_KEY="sk-..."')
        return

    prompt = f"""
You are Quartiles Solver v3.1.
Solve this Quartiles puzzle using these tiles:
{tiles}

Avoid any of the following blocked words:
{blocklist_text}

Return your Quartiles Solver Output in Markdown format.

At the very end, if you believe any words should be blocked in the future,
output EXACTLY ONE LINE in this format (or omit the line if none):
INVALID: word1, word2, word3
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a careful puzzle solver."},
                {"role": "user", "content": prompt}
            ]
        )
        gpt_output = resp.choices[0].message.content
        print("✅ GPT Response:\n")
        print(gpt_output)

        new_invalids = detect_potential_invalids(gpt_output, words)
        if new_invalids:
            print("\n⚠️  GPT flagged possible invalid words:", ", ".join(new_invalids))
            confirm = input("Add these to blocklist? (y/n): ").strip().lower()
            if confirm == "y":
                merged = load_blocklist().union(new_invalids)
                save_blocklist(merged)
                print("✅ Updated blocklist with new invalid words.")
        else:
            print("\nNo new invalid words detected.")
    except Exception as e:
        print("⚠️ Error contacting GPT:", e)


# ============================================================
# Main
# ============================================================

def main():
    backup_blocklist()
    clean_blocklist_file()

    if not load_blocklist():
        print("⚠️  Warning: blocklist.txt is currently empty — add words before solving.\n")

    while True:
        print("\nChoose an action:")
        print("1) Add a blocked word")
        print("2) Show blocked words")
        print("3) Debug: show blocklist path and contents")
        print("4) Solve a puzzle")
        print("5) Restore most recent backup")
        print("6) Quit")

        choice = input("Enter 1-6: ").strip()

        if choice == "1":
            w = input("Enter the word to block: ").strip()
            add_invalid(w)
        elif choice == "2":
            show_blocklist()
        elif choice == "3":
            debug_blocklist_path()
        elif choice == "4":
            t = input("Enter your puzzle tiles (separated by spaces): ")
            solve_puzzle(t)
        elif choice == "5":
            restore_latest_backup()
        elif choice == "6":
            print("Goodbye!")
            break
        else:
            print("Please choose a number between 1 and 6.")


if __name__ == "__main__":
    main()
