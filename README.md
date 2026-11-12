# 📖 Book-Angel

**Book-Angel** is an intelligent book transformation and filtering companion designed to run alongside AI agents (such as Google Antigravity CLI and Cursor IDE). It allows you to safely adapt EPUB and PDF books according to custom content guidelines (e.g., softening graphic romance/kissing, reducing violence or gore, adapting characters and genders) while preserving original cover art, typography, and book formatting.

---

## ⚡ Super-Easy Setup (Zero Path Typing!)

### Option A: Double-Click Launcher (macOS)
Inside this `Book-Angel-` folder, simply **double-click** the file:
```text
Book-Angel.command
```
This opens Terminal automatically, installs any needed components, and presents a friendly menu:
```text
============================================================
              📖  Welcome to Book-Angel
============================================================
Active Rules File: ./rules.yaml
  • Romance Level:    mild
  • Violence Level:   adventure
  • Character Rules:  1 configured
  • Export Directory: ~/Downloads
------------------------------------------------------------
[1] 📂 Open a Book (Opens Mac Finder dialog to select EPUB/PDF)
[2] ⚙️  Configure Rules & Character Transformations
[3] 📝 Open rules.yaml in Text Editor / Cursor
[4] 🔍 Review Chunk Diffs
[5] 📦 Export Clean Book to Downloads
[Q] ❌ Quit
============================================================
```

### Option B: Terminal Command
Run `book-angel` anywhere in your terminal:
```bash
cd Book-Angel-
pip install -e .
book-angel
```

---

## 🛠️ Complete 5-Step Workflow

```text
[Input Book (.epub / .pdf)]
           │
           ▼
1. rules.yaml (in root)     ──► Edit rules, character mappings & examples
           │
           ▼
2. book-angel unpack        ──► Opens Mac Finder dialog to click and choose book
           │
           ▼
3. Agent Processing         ──► Antigravity or Cursor Agent rewrites chunks
           │
           ▼
4. Visual Diff in Cursor    ──► Inspect red/green changes side-by-side
           │
           ▼
5. book-angel export        ──► Packages final EPUB / PDF directly to ~/Downloads
```

---

### Step 1: Configure Your Rules & Character Transformations

Right in the project root is `rules.yaml`. You can double click it or run:
```bash
book-angel config --open
```

#### What you can customize:

```yaml
# 1. Policy Levels
romance_level: mild        # mild | clean | moderate
violence_level: adventure  # adventure (removes gore) | mild | clean
language_level: cleaned    # cleaned | pg | original

# 2. Character & Gender Transformations (Character Swapping)
# Seamlessly adapt a character's name and pronouns so all dialogue,
# romance, and narrative interactions remain natural:
character_mappings:
  - original_name: "Julian"
    new_name: "Julia"
    new_gender: "female"
    pronouns: "she/her/hers"
    instruction: "Transform Julian into a female love interest named Julia. Adapt all pronouns (he->she, him->her, his->her/hers) and physical descriptors so the relationship with the protagonist is completely natural."

# 3. Omitted Themes
omitted_topics:
  - graphic sexual content
  - extreme gore or torture

# 4. Few-Shot Examples (Teach the AI your exact style)
examples:
  - before: "He grabbed her roughly and crushed his mouth against hers in a fiery, desperate kiss."
    after: "He reached out and gently took her hand, leaning in to give her a warm, affectionate kiss on the cheek."
```

---

### Step 2: Open Your Book (No Typing Paths!)

Just run:
```bash
book-angel unpack
```
Your native **Mac Finder window** pops up automatically. Navigate to your Downloads or Books folder, click your `.epub` or `.pdf` file, and click **Open**.

Book-Angel will:
- Extract the book's cover image (`cover.jpg`)
- Break the text into scene-preserving chunks (`<2,500 words`)
- Save pristine copies in `.originals/` for side-by-side diffing

---

### Step 3: Run the AI Agent to Edit Chunks

#### In Cursor IDE:
1. Open the `Book-Angel-` folder in Cursor.
2. In Composer / Chat (`Cmd + I` or `Cmd + L`), prompt the agent:
   > *"Review all chunks in `.book-angel/staging/<book-slug>/chunks/` and modify them to follow the guidelines in `rules.md`."*
3. The agent edits each chunk file right inside your workspace.

#### In Antigravity CLI (`agy`):
Prompt:
> *"Review the unpacked chunks in staging according to rules.md"*

---

### Step 4: Review Changes Visually in Cursor

1. Open **Cursor**.
2. Click on the **Source Control (Git) icon** on the left sidebar (or press `Ctrl + Shift + G`).
3. Click any modified chunk file (`chunk_001.txt`, `chunk_002.txt`).
4. You will see a clear **side-by-side split screen**:
   - **Left:** Original text (red lines removed).
   - **Right:** Cleaned text (green lines added).
5. If you want to tweak any sentence, you can edit directly in the file!

*(You can also run `book-angel review` in the terminal for colorized diffs).*

---

### Step 5: Export the Clean Book to Downloads

Run:
```bash
book-angel export
```

Your clean edition will be saved directly into your **`~/Downloads`** folder:
- `~/Downloads/My_Book_Clean_Edition.epub` (or `.pdf` with `--format pdf`)
- ✅ Original cover art preserved
- ✅ Responsive typography, font styles, and layout intact
- ✅ Character names and gender adaptations smoothly applied

---

## 📋 CLI Cheatsheet

| Command | Action |
|---|---|
| `book-angel` | Opens the interactive menu. |
| `book-angel unpack` | Pops up macOS Finder to pick an EPUB or PDF. |
| `book-angel config` | Interactive setup questionnaire. |
| `book-angel config --open` | Opens `rules.yaml` directly in your default editor. |
| `book-angel review` | Interactive terminal diff viewer. |
| `book-angel export` | Exports clean book to `~/Downloads`. |
| `book-angel status` | Shows staged books and modified chunk counts. |
