import Foundation

public final class AppPreferences {
    public enum Keys {
        public static let enabledCollectionIDs = "enabledCollectionIDs"
        public static let rotationIntervalSeconds = "rotationIntervalSeconds"
        public static let showMenuBarIcon = "showMenuBarIcon"
        public static let showDockIcon = "showDockIcon"
    }

    public static let defaultRotationIntervalSeconds: TimeInterval = 30 * 60

    private let defaults: UserDefaults

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    public var enabledCollectionIDs: Set<String> {
        get { Set(defaults.stringArray(forKey: Keys.enabledCollectionIDs) ?? []) }
        set { defaults.set(Array(newValue).sorted(), forKey: Keys.enabledCollectionIDs) }
    }

    public var rotationIntervalSeconds: TimeInterval? {
        get {
            guard defaults.object(forKey: Keys.rotationIntervalSeconds) != nil else {
                return Self.defaultRotationIntervalSeconds
            }
            let seconds = defaults.double(forKey: Keys.rotationIntervalSeconds)
            return seconds > 0 ? seconds : nil
        }
        set { defaults.set(newValue ?? 0, forKey: Keys.rotationIntervalSeconds) }
    }

    public var showMenuBarIcon: Bool {
        get { bool(forKey: Keys.showMenuBarIcon, defaultValue: true) }
        set { defaults.set(newValue, forKey: Keys.showMenuBarIcon) }
    }

    public var showDockIcon: Bool {
        get { bool(forKey: Keys.showDockIcon, defaultValue: false) }
        set { defaults.set(newValue, forKey: Keys.showDockIcon) }
    }

    private func bool(forKey key: String, defaultValue: Bool) -> Bool {
        guard defaults.object(forKey: key) != nil else { return defaultValue }
        return defaults.bool(forKey: key)
    }
}
