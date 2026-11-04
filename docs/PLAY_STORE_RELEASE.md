# TechWatch Android release handoff

## Current artifacts

The native Flutter Android client is in `mobile/`. The `preview` flavor has package ID `com.zivantaai.techwatch.preview` and is for installation and internal testing only. Both preview and production use `https://techwatch.zivantaai.com` and disallow cleartext traffic. The `production` flavor uses package ID `com.zivantaai.techwatch`. Both target API 36. The app asks for no runtime permissions; the merged manifest contains Internet and an AndroidX receiver compatibility permission.

The upload signing key was generated outside the repository at `~/.local/share/techwatch-signing/upload-keystore.p12`, with local Gradle properties in the same directory. Back up both securely. The key passwords are not in Git.

## Before Play Console submission

1. Keep `techwatch.zivantaai.com` pointed to the server, confirm HTTPS, and test the production API and `/privacy` URL. Do not upload the preview flavor as the public app.
2. Confirm that `admin@zivantaai.com` is a monitored support and privacy email, or replace it in `web/privacy.html` and the Play listing. Review the privacy policy for accuracy against the final logging and hosting setup.
3. Build `production` with `flutter build appbundle --release --flavor production --dart-define=API_BASE_URL=https://techwatch.zivantaai.com`. Keep package ID and signing key stable after first publication; increase the `+buildNumber` in `mobile/pubspec.yaml` for every update.
4. Create the Play Console app and complete the store listing, real screenshots, app access declaration, ads declaration, content rating, target audience, and Data safety form. The form must accurately cover the random installation ID, preferences, bookmarks, server logs, service hosting and 30-day backups. Production traffic must use HTTPS before marking data as encrypted in transit.
5. Treat TechWatch as a news or news-related app if the Play declaration asks for it. Identify each briefing's original source, keep content current, provide a reachable contact, and complete the News & Magazines self declaration where applicable. The app already displays source labels and links, and marks fictional development examples.
6. Test on real Android phones, including a small screen and Android 16, and fix any visible clipped card or onboarding options. Verify onboarding, the four feeds, vertical paging, source links, search, bookmarks, data deletion and offline error states against the live backend.
7. Upload to internal testing first. For a new personal Play developer account, Google may require a closed test with at least 12 opted-in testers for 14 continuous days before production access.

Google's current guidance: [target API levels](https://support.google.com/googleplay/android-developer/answer/11926878), [app bundle and signing](https://docs.flutter.dev/deployment/android), [News & Magazines policy](https://support.google.com/googleplay/android-developer/answer/9935326), [privacy policy and review preparation](https://support.google.com/googleplay/android-developer/answer/9859455), [Data safety](https://support.google.com/googleplay/android-developer/answer/10787469), [new personal account testing](https://support.google.com/googleplay/android-developer/answer/14151465).

Approval depends on Google's review of the final app, listing, declarations and account. No code change can guarantee it.
