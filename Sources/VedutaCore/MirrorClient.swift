import Foundation
import CryptoKit

/// Abstracts the network so the mirror logic is unit-testable without a server.
public protocol MirrorTransport {
    /// Fetch the full contents at `url`. Throws on transport error or non-2xx.
    func get(_ url: URL) throws -> Data
}

public enum MirrorError: Error, Equatable {
    case noResponse
    case http(Int)
    case allCandidatesFailed
}

/// Synchronous `URLSession` transport. The app calls into the mirror from a
/// background queue, so blocking here is fine and keeps call sites simple.
public struct URLSessionMirrorTransport: MirrorTransport {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func get(_ url: URL) throws -> Data {
        var request = URLRequest(url: url)
        request.timeoutInterval = 60
        let semaphore = DispatchSemaphore(value: 0)
        var result: Result<Data, Error> = .failure(MirrorError.noResponse)
        let task = session.dataTask(with: request) { data, response, error in
            defer { semaphore.signal() }
            if let error {
                result = .failure(error)
                return
            }
            guard let http = response as? HTTPURLResponse else {
                result = .failure(MirrorError.noResponse)
                return
            }
            guard (200..<300).contains(http.statusCode) else {
                result = .failure(MirrorError.http(http.statusCode))
                return
            }
            result = .success(data ?? Data())
        }
        task.resume()
        semaphore.wait()
        return try result.get()
    }
}

/// Reads the published library mirror: `<baseURL>/catalog.json`,
/// `<baseURL>/collections/*.json`, `<baseURL>/images/<collection>/<id>.jpg`.
public final class MirrorClient {
    public let baseURL: URL
    private let transport: MirrorTransport

    public init(baseURL: URL, transport: MirrorTransport = URLSessionMirrorTransport()) {
        self.baseURL = baseURL
        self.transport = transport
    }

    public func url(forRelativePath path: String) -> URL {
        baseURL.appendingPathComponent(path)
    }

    /// Fetch a small text resource (catalog or a collection manifest).
    public func fetch(relativePath: String) throws -> Data {
        try transport.get(url(forRelativePath: relativePath))
    }

    /// Download an image's bytes. Tries the mirror first, verifying the known
    /// sha256; then the upstream fallback URLs as a best effort (their bytes
    /// are a different rendition, so they're not checksum-verified).
    public func downloadImage(
        localPath: String,
        expectedSHA256: String?,
        fallbackUrls: [String]
    ) throws -> Data {
        var candidates: [(url: URL, verify: Bool)] = [(url(forRelativePath: localPath), true)]
        candidates += fallbackUrls.compactMap(URL.init(string:)).map { ($0, false) }

        for candidate in candidates {
            guard let data = try? transport.get(candidate.url) else { continue }
            if candidate.verify, let expectedSHA256, !expectedSHA256.isEmpty {
                guard Self.sha256Hex(data) == expectedSHA256 else { continue }
            }
            return data
        }
        throw MirrorError.allCandidatesFailed
    }

    static func sha256Hex(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
}
