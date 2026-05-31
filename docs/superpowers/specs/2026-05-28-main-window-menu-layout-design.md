# Veduta Main Window and Menu Layout Design

## Goal

Make Veduta feel like a standard mature macOS menu-bar app by adopting the reference app's window structure and menu arrangement: a native window with a left sidebar, right-side grouped settings pages, and a concise menu-bar dropdown. The design borrows layout hierarchy only; colors and control styling stay native/system-provided.

## Reference Boundary

The reference project is `hoomanaskari/mac-dictate-anywhere`, which uses a main macOS window with a sidebar and native SwiftUI controls. Its MIT license permits reference, but Veduta should not copy code or branding. We will adapt the arrangement: sidebar navigation, page titles, grouped rows, and a menu-bar entry point.

## Window Structure

Veduta should present a standard main window rather than a small custom settings panel.

- Use a SwiftUI `NavigationSplitView` hosted from AppKit so the existing menu-bar app architecture can stay intact.
- Default window title: `Veduta`.
- Use a stable sidebar on the left and detail content on the right.
- Let macOS handle window background, dark mode, sidebar selection color, row styling, and native control colors.
- Avoid custom gradient icons, custom color palettes, oversized cards, or showcase-style headers.

## Sidebar Pages

Initial pages should stay focused on current product capabilities:

1. `Wallpaper` — current wallpaper status, next-wallpaper action, rotation interval.
2. `Settings` — menu-bar and Dock visibility preferences.
3. `Collections` — downloaded collection enable/disable toggles.
4. `Library` — local library path and open-folder action.
5. `About` — short product description and app-level actions.

Do not add unimplemented future pages such as favorites, gallery history, sync, or launch-at-login in this pass.

## Detail Layout

Each detail page should follow the screenshot's standard rhythm:

- A plain page title at the top.
- Native grouped sections with section headers.
- Rows with label on the left and value/control/action on the right.
- Secondary explanatory text only where needed, using native secondary text styling.
- Buttons stay plain/native unless the system gives them emphasis.

Page content:

### Wallpaper

- `Current Wallpaper` section:
  - Artwork title, falling back to `No wallpaper selected yet`.
  - Creator when available.
  - Status message, shown when not `Ready` or when useful for troubleshooting.
- `Rotation` section:
  - Native picker for rotation interval.
- `Actions` section:
  - `Next Wallpaper` button.

### Settings

- `App Visibility` section:
  - `Show menu bar icon` toggle.
  - `Show Dock icon on next launch` toggle, preserving the existing next-launch behavior.
- `Recovery` section:
  - Native explanatory text about reopening from Finder or Spotlight if both icons are hidden.

### Collections

- `Downloaded Collections` section:
  - One native toggle row per collection.
  - Disable the last enabled collection toggle and show a short secondary explanation: `At least one collection must stay enabled.`
  - Empty state: `No downloaded collections found yet.`

### Library

- `Local Library` section:
  - Show the local library path.
  - Show downloaded collection count.
  - `Open Library Folder` button.

### About

- `Veduta` section:
  - Short description: `A local-first open-source wallpaper rotator for macOS.`
- `Actions` section:
  - `Open Library Folder`.
  - `Quit Veduta`.

## Menu-Bar Dropdown

Rearrange the status-menu dropdown to feel like a standard companion menu for the main window:

1. `Open Veduta` — opens/focuses the main window.
2. Separator.
3. `Next Wallpaper`.
4. `Current Wallpapers` submenu when there is at least one current selection.
5. `Collections` submenu when downloaded collections exist.
6. `Rotation Interval` submenu.
7. Separator.
8. `Quit Veduta`.

The collections submenu should use checkmarks and preserve the existing rule that at least one collection remains enabled. The current wallpaper submenu should keep reveal/open-source actions.

## Behavior

- Launch should show the main window, matching the current app behavior of showing settings on start.
- Reopening the app from Finder/Spotlight should show/focus the same main window.
- Menu-bar `Open Veduta` should show/focus the same main window.
- `Next Wallpaper`, rotation changes, and collection toggles should update both the menu and the window snapshot.
- Existing preferences and local-library behavior should remain unchanged.

## Testing and Verification

- Run Swift tests to ensure core preferences and library behavior are unchanged.
- Run a Swift build to catch app-target compile errors.
- Run the app and manually verify:
  - The main window appears with sidebar and native controls.
  - Sidebar pages switch correctly.
  - Menu-bar dropdown ordering matches this spec.
  - Rotation picker updates the menu and preferences.
  - Collection toggles preserve the at-least-one-enabled rule.
  - Dark mode uses native colors without copied reference colors.

## Out of Scope

- Copying the reference app's colors, custom green selection style, or branding.
- Adding launch-at-login.
- Adding new product features such as favorites, gallery browsing, sync, or release packaging.
- Converting the entire executable to SwiftUI `@main` unless required by implementation constraints.
