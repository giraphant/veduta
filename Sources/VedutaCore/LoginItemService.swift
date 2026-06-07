import Foundation
import ServiceManagement

/// Wraps the system "Open at Login" registration for the main app bundle.
///
/// Backed by `SMAppService.mainApp` (macOS 13+). The system — not
/// `UserDefaults` — is the source of truth, so `isEnabled` reads the live
/// registration status each time rather than mirroring a stored flag the user
/// could change out from under us in System Settings.
public final class LoginItemService {
    public init() {}

    /// Whether the app is currently registered to launch at login.
    public var isEnabled: Bool {
        SMAppService.mainApp.status == .enabled
    }

    /// Whether login-item registration is usable in this build. `SMAppService`
    /// only works from a real `.app` bundle with a bundle identifier; a bare
    /// SwiftPM executable (e.g. `swift run`) has none, so the control is hidden
    /// there instead of throwing on every toggle.
    public var isSupported: Bool {
        Bundle.main.bundleIdentifier != nil
            && Bundle.main.bundleURL.pathExtension == "app"
    }

    /// Register or unregister the app as a login item. Throws if the system
    /// rejects the change — most commonly when the user previously disabled the
    /// item in System Settings, which then requires their re-approval there.
    public func setEnabled(_ enabled: Bool) throws {
        let service = SMAppService.mainApp
        if enabled {
            guard service.status != .enabled else { return }
            try service.register()
        } else {
            guard service.status == .enabled else { return }
            try service.unregister()
        }
    }
}
