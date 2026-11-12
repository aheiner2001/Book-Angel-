# 📖 Book-Angel

**Book-Angel** is an intelligent book transformation and filtering companion designed to run alongside AI agents (such as Google Antigravity / Gemini and Cursor IDE). It allows you to safely adapt EPUB and PDF books according to custom content guidelines while preserving original cover art, typography, and book formatting.

---

## ⚡ Double-Click & Go (No Terminal Commands!)

In your `Book-Angel-` folder, you have two simple files:

1. 📝 **`Edit-Rules.command`**:
   - Double-click anytime to open your rules in Mac TextEdit.
   - Paste or change your plain-English rules, press `Cmd + S` to save, and close.

2. 📖 **`Book-Angel.command`**:
   - Double-click to start!
   - If starting fresh: Mac Finder opens immediately $\rightarrow$ click your EPUB or PDF book $\rightarrow$ click **Open**.
   - If you already unpacked a book: Simply press **Enter** (Option `[1]`) to copy the AI prompt to your clipboard anytime!
   - Open Gemini (or Cursor) and press **`Cmd + V`** (Enter).
   - **Automatic Export**: Gemini reads your rules, edits the book chunks, and automatically exports the clean copy straight to your `~/Downloads` folder!

---

## 🛠️ How It Works

```text
1. Edit-Rules.command        ──► Paste plain-English rules in TextEdit
              │
              ▼
2. Book-Angel.command        ──► Unpacks book or copies prompt (Option [1])
              │
              ▼
3. Auto-Copied to Clipboard  ──► Press Cmd + V in Gemini / Cursor
              │
              ▼
4. AI Auto-Exports Book      ──► Clean EPUB/PDF ready in ~/Downloads!
```

---

## 📝 Rules & Guidelines (`rules.txt`)

Your active rules are in [rules.txt](file:///Users/aaronheiner/Book-Angel-/rules.txt):
- **Surgical Scalpel**: Leaves 95%+ of the book untouched.
- **Jane Austen Kissing**: Keeps sweet, soft, romantic affection; tones down heavy lust.
- **Clean Bedroom Transitions**: Preserves conversations and love declarations; cleanly cuts before explicit acts.
- **Same-Sex Adaptations**: Adapts characters and pronouns naturally.
- **Action Preserved**: Keeps exciting battles and sword fights; only softens extreme gore.

---

## 🧪 Testing

```bash
pytest -v
```
All 64 tests pass in under 0.3 seconds.
