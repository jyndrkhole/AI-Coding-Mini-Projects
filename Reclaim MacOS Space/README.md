# Reclaim macOS Space

Local web portal to safely reclaim disk space from developer junk on macOS — Xcode, Android, .NET, simulators, caches, and Time Machine local snapshots.

## What it does

1. **Scans** known junk locations and shows how much space each uses.
2. Lets you **pick categories** — nothing is deleted unless you check it and confirm.
3. **Never touches** your projects, SDKs, source code, or `~/Android` SDK installs wholesale.

## Safety model

| Risk | Examples | Default |
|------|----------|---------|
| Low | DerivedData, NuGet cache, Gradle caches, developer app caches | Selected |
| Medium | Xcode Archives, simulators, AVD images, TM snapshots | You opt in |
| High | Local iPhone/iPad backups (`MobileSync`) | You opt in |

Deletion is limited to predefined paths per category. The cleaner refuses any path outside that allowlist.

**Not included (on purpose):**

- Blanket `rm -rf ~/Library/Caches/*` — too aggressive; only named developer caches are targeted.
- Full `~/Library/Android` or `~/Android` — only Gradle/Android Studio cache subfolders.
- Your `.android` folder except `avd` emulator images.

## Quick start

**Option A — double-click app (recommended)**

```bash
chmod +x build-app.sh
./build-app.sh
```

Then open **`Reclaim Space.app`** in Finder.

**Option B — terminal**

```bash
chmod +x run.sh
./run.sh
```

Opens **http://127.0.0.1:8765** in your browser.

To stop the server: quit the Python process, or run `lsof -ti:8765 | xargs kill`.

## Categories

- **Xcode DerivedData** — build artifacts
- **Xcode Archives** — old `.xcarchive` bundles
- **Old iOS DeviceSupport only** — keeps 2 newest versions, removes the rest
- **CoreSimulator** — simulator devices and data
- **NuGet + dotnet nuget locals**
- **Android AVD + Gradle/Android Studio caches**
- **MAUI / Xamarin caches** — Visual Studio, Xamarin, MonoDevelop logs, Android build-cache
- **Docker unused data** — dangling images, stopped containers, build cache (volumes kept)
- **Developer app caches** (Xcode, SwiftPM, CocoaPods, pip, yarn, Homebrew)
- **User logs** — `~/Library/Logs`
- **iOS device backups** — local Finder/iTunes backups (high risk)
- **Time Machine local snapshots** — requires admin password
- **System `/Library/Caches`** — requires admin password

Admin operations use the standard macOS password dialog via `osascript`.

## After cleanup

- Empty Trash if large folders were removed.
- Restart Xcode / Android Studio if they were open during cleanup.
- Re-open simulators or re-create AVDs as needed.

## Manual commands (reference)

These are the operations the portal wraps — run manually only if you prefer Terminal:

```bash
rm -rf ~/Library/Developer/Xcode/DerivedData
dotnet nuget locals all --clear
tmutil listlocalsnapshots /
sudo tmutil thinlocalsnapshots / 999999999999 4
```

## Requirements

- macOS
- Python 3.10+
