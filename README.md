# Connor's Deck 🚀

**One place to launch and update Connor's apps.**

School Hub · Writing App (coming soon) · Watch Hub · Mystery Hollow — plus empty berths for whatever comes next.

Same family as the other hubs: lives on the Mac via Desktop shortcuts, updates from GitHub when Dad ships changes. Cool **Command Glass** UI, not a plain list.

---

## For Connor's Mac (after Xcode / git is ready)

### First time only

Open **Terminal** and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/Gaz444-lab/connor-deck/main/scripts/setup-for-connor.sh | bash
```

That clones into `~/Documents/connor-deck` and puts on the **Desktop**:

| Shortcut | When to use |
|----------|-------------|
| **Connor's Deck.command** | Every day — open the launcher |
| **Update Deck.command** | After Dad says he pushed a Deck update |

macOS may ask to allow Terminal the first time → **Open**.

### Every day

1. Double-click **Connor's Deck.command**
2. Browser opens → `http://127.0.0.1:8764/`
3. Hit **Launch** / **Play** on an app card, or **Update** when Dad has shipped changes

### When Dad ships an app update

Open the Deck → **Update** on that card (or **Update all**).

> Your homework, watchlist, reviews and game saves stay on this Mac — only app code updates.

You can still use the old School Hub / Watch Hub Desktop shortcuts if you want. The Deck just makes one home for everything.

---

## What's on the deck

| Tile | What it does |
|------|----------------|
| **School Hub** | Launch / stop / update the Grade 10 planner (port 8765) |
| **Writing App** | Coming soon — reserved until Dad pulls it from the other account |
| **Watch Hub** | Launch / stop / update Neon Deck tracker (port 8766) |
| **Mystery Hollow** | Launch the Godot detective game (and git-update if installed as a repo) |
| **Empty berths** | Space for the next builds |

### Keyboard

| Key | Action |
|-----|--------|
| `1`–`4` | Launch first launchable apps |
| `U` | Update all |
| `R` | Refresh status |
| `?` | Shortcuts help |

---

## For Dad (your Mac)

Repo: `https://github.com/Gaz444-lab/connor-deck`  
Local: `~/connor-deck`

```bash
cd ~/connor-deck
# edit files…
git add -A
git commit -m "Describe the change"
git push
```

Tell Connor to run **Update Deck.command** (or open Deck and it will use the new UI after update).

### Local run (dev)

```bash
cd ~/connor-deck
./launch.sh
# → http://127.0.0.1:8764/
```

### App registry

Tiles are data, not hard-coded UI:

```
data/apps.json
```

When Writing lands on this machine:

1. Clone it to `~/Documents/connor-writing-app` (or `~/connor-writing-app`)
2. Set `"state": "active"` and fill `repoUrl` if needed
3. Push Deck — Connor updates Deck and the card flips to Launch/Update

### Ports

| Port | Service |
|------|---------|
| **8764** | Connor's Deck |
| 8765 | School Hub |
| 8766 | Watch Hub |
| 8767 | Writing App (reserved) |

### Security notes

- Control plane binds **127.0.0.1 only**
- Only app ids listed in `apps.json` can be launched/updated
- Launch scripts and install paths are whitelisted (home + Documents)

---

## Tech

Static HTML/CSS/JS · Python control plane (`server.py`) · no Node · git pull for updates · registry in `data/apps.json`.

Made for Connor 🌊
