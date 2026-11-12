# 📖 Book-Angel

**Book-Angel** is an intelligent book transformation and filtering companion designed to run alongside AI agents (such as Google Antigravity / Gemini and Cursor IDE). It allows you to safely adapt EPUB and PDF books according to custom content guidelines while preserving original cover art, typography, and book formatting.

---

## ⚡ The Dead-Simple 3-Step Workflow

```text
1. Paste rules into rules.txt  ──► (Plain English, as long as you want!)
              │
              ▼
2. Double-click Book-Angel     ──► Picks book & copies prompt to clipboard
              │
              ▼
3. Press Cmd + V in Gemini     ──► AI edits all chunks in staging
              │
              ▼
4. Export clean book           ──► Clean EPUB/PDF ready in ~/Downloads!
```

---

### Step 1: Paste Your Rules into `rules.txt`

Open [rules.txt](file:///Users/aaronheiner/Book-Angel-/rules.txt) in the folder.
Type or paste your rules in plain English. No special syntax or formatting required!

**Example `rules.txt`:**
```text
- Only change passionate kissing scenes into mild, sweet affection. Leave ordinary friendly kisses, hugs, and casual handholding completely alone.
- If you see extreme gore or dismemberment, soften it. Keep regular sword fights and battles completely intact.
- Whenever Julian is in a romantic scene, change Julian to a woman named Julia with she/her pronouns so the relationship remains natural.
- Leave 99% of the author's words completely untouched.
```

---

### Step 2: Open Your Book

Double-click [Book-Angel.command](file:///Users/aaronheiner/Book-Angel-/Book-Angel.command) (or run `book-angel` in Terminal).

- Choose **`[1] Open a Book`**
- Your **Mac Finder window** pops open automatically.
- Click your `.epub` or `.pdf` file and click **Open**.

Book-Angel will unpack the book into chunks, apply your `rules.txt`, and **automatically copy this prompt to your Mac clipboard**:

```text
=================================================================
🎉 BOOK UNPACKED AND READY!
📋 PROMPT AUTOMATICALLY COPIED TO CLIPBOARD!
   👉 Just open Gemini (or Cursor) and press Cmd + V!
=================================================================
```

---

### Step 3: Paste into Gemini (or Cursor)

1. Open your Gemini / Antigravity chat or Cursor.
2. Press **`Cmd + V`** (Paste) and hit **Enter**.
3. Gemini will read the folder, read your rules, and automatically process the chunks!

---

### Step 4: Export Your Clean Book

When Gemini finishes, go back to Book-Angel and choose:
- **`[5] Export Clean Book to Downloads`** (or run `book-angel export`)

Your clean book is saved directly into your **Mac Downloads folder** (`~/Downloads/My_Book_[Clean_Edition].epub`)!
