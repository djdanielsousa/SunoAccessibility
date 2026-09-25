# Suno Accessibility

Suno Accessibility is an NVDA add-on by Daniel SonarCode that improves the accessibility of the Suno AI music-generation website.

The add-on provides conservative labels for icon-only or unclear controls, offers manual and automatic accessibility diagnostics, and announces explicit song-generation progress and completion messages exposed by Suno.

## Supported browsers

- Google Chrome
- Microsoft Edge
- Mozilla Firefox
- Brave
- Vivaldi

## Main features

- Labels recognised Suno controls without accessible names.
- Improves generic play-count and like-count announcements.
- Announces song generation progress and completion.
- Adds a Suno AI submenu to the NVDA Tools menu.
- Creates detailed accessibility diagnostic reports.
- Optionally captures an image of the focused control and its surroundings.
- Provides settings under NVDA Preferences, Settings, Suno AI.
- Includes documentation and localisation resources.

## Privacy

The add-on does not collect telemetry, transmit diagnostic reports, access credentials, read browser cookies, or communicate with external analytics services. Diagnostic files and optional screenshots remain on the user's computer unless the user chooses to share them.

## Compatibility

The Store manifest uses NVDA API version `0.0.0` for compatibility with NVDA 2018.4.1 and earlier. The add-on contains compatibility fallbacks intended for older NVDA releases and is designed to support NVDA 2014.1 and later.

Development version 1.0.1 is declared as tested through the experimental NVDA 2027.1 API and must be submitted to the `dev` channel.

## Building

The `.nvda-addon` package is a ZIP archive containing the files at the repository root. Exclude repository-only files such as `README.md`, `CHANGELOG.md`, `LICENSE.txt` and `.gitignore` when building a release package.

## Author

Daniel SonarCode

## Licence

GNU General Public License version 2.0 only. See `LICENSE.txt`.
