# AgentVizion2Go Release Portal

Separate one-click builds for **iOS (TestFlight)** and **Android (signed AAB)**.

## Platform flows

| | iOS | Android |
|---|-----|---------|
| Increment build number | ✓ | ✗ |
| `dotnet publish` | `net9.0-ios` + archive | `net9.0-android` + signed AAB |
| Upload | TestFlight via `xcrun altool` | — (AAB saved locally) |

Each platform has its own button in the portal — they run independently.

## Quick start

```bash
cd testflight-portal
chmod +x start.sh
./start.sh
```

Edit `.env` with credentials, then open **http://127.0.0.1:8787**.

## Configuration (`.env`)

| Variable | Used by |
|----------|---------|
| `APPLE_ID`, `APPLE_APP_PASSWORD` | iOS only |
| `ANDROID_KEYSTORE_PATH`, `ANDROID_KEYSTORE_PASS`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASS` | Android only |
| `GROQ_API_KEY` | Optional AI log analysis |

## Manual commands

**iOS** (increments build, publishes, uploads):
```bash
# 1. Increment ApplicationVersion in csproj
cd /Users/jayendra/Desktop/AgentVizion2Go
dotnet publish AgentVizion2Go.MAUI/AgentVizion2Go.MAUI.csproj \
  -f net9.0-ios -c Release \
  -p:RuntimeIdentifier=ios-arm64 -p:ArchiveOnBuild=true
cd AgentVizion2Go.MAUI/bin/Release/net9.0-ios/ios-arm64/publish
xcrun altool --upload-app -f AgentVizion2Go.MAUI.ipa -t ios \
  -u "ios.jayendra@gmail.com" \
  -p "hlhh-bhjk-mpze-dowu"
```

**Android** (no version bump, signed AAB only):
```bash
cd /Users/jayendra/Desktop/AgentVizion2Go
dotnet publish AgentVizion2Go.MAUI/AgentVizion2Go.MAUI.csproj \
  -f net9.0-android -c Release \
  -p:AndroidPackageFormat=aab \
  -p:AndroidKeyStore=true \
  -p:AndroidSigningKeyStore="/Users/jayendra/Documents/Magnifact/Certs/AgentVizion2Go/AgentVizion2Go.keystore" \
  -p:AndroidSigningStorePass="agentvizion@magnifact#7" \
  -p:AndroidSigningKeyAlias="AgentVizion2Go" \
  -p:AndroidSigningKeyPass="agentvizion@magnifact#7"
```

Output: `AgentVizion2Go.MAUI/bin/Release/net9.0-android/publish/*-Signed.aab`
