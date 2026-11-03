# TechWatch Android client

Native Flutter client for the existing FastAPI service. It includes onboarding, Feed · Your Stack · Trending · AI, full-screen vertical briefing paging, list view, topic filters, search, bookmarks, source health, and data deletion.

## Build

Install Flutter stable, Android SDK 36 and a supported JDK. Keep the upload keystore outside this repository. The Android Gradle project reads `TECHWATCH_SIGNING_PROPERTIES` or `~/.local/share/techwatch-signing/key.properties` with `storeFile`, `storePassword`, `keyAlias`, and `keyPassword`.

```sh
cd mobile
flutter pub get
flutter analyze
flutter test
flutter build apk --release --flavor preview --dart-define=API_BASE_URL=http://65.1.226.15
flutter build appbundle --release --flavor preview --dart-define=API_BASE_URL=http://65.1.226.15
```

The preview package ID is `com.zivantaai.techwatch.preview`. This variant alone permits cleartext traffic to the temporary IP. The APK is for direct installation and the AAB is for Play internal testing once a Play Console account exists.

After DNS and HTTPS are active, build the production package ID `com.zivantaai.techwatch`:

```sh
flutter build appbundle --release --flavor production --dart-define=API_BASE_URL=https://techwatch.zivantaai.com
```

Back up the upload keystore and its passwords. Losing the upload key complicates future updates; never commit it or send it in chat. The package ID can be changed before the first Play publication, then becomes permanent for that listing.

## Play submission remaining

Verify the permanent HTTPS hostname and public privacy policy. Confirm the support email in `web/privacy.html`. Complete the Play Console app content, News & Magazines declaration if applicable, Data safety answers, screenshots, store listing, and required testing. The production app requests only Internet permission and targets Android API 36. A signed bundle alone does not guarantee approval.
