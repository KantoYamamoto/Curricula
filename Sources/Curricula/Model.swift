import Foundation

// These value types are the explicit schema 0.1.0 exchange contract.
public enum EntityKind: String, Codable, Sendable { case frameworkItem, subjectMatter, competency }
public enum Origin: String, Codable, Sendable { case original, editorial, synthetic }
public enum ReviewStatus: String, Codable, Sendable { case draft, reviewed }
public enum Investigation: String, Codable, Sendable { case uninvestigated, scopedBoundary, investigated }
public enum RelationKind: String, Codable, Sendable { case alignment, knowledge, dependency, enrollment }
public enum Coverage: String, Codable, Sendable { case full, partial }
public enum Strength: String, Codable, Sendable { case required, recommended, alternative }

public struct Provenance: Codable, Equatable, Sendable {
    public var origin: Origin
    public var sourceIDs: [String]
    public var rationale: String
    public var reviewStatus: ReviewStatus
    public init(_ origin: Origin, sources: [String] = [], rationale: String, reviewStatus: ReviewStatus = .draft) {
        self.origin = origin; sourceIDs = sources; self.rationale = rationale; self.reviewStatus = reviewStatus
    }
}
public struct SourceDocument: Codable, Equatable, Sendable {
    public var id: String
    public var title: String
    public var publisher: String
    public var url: String
    public var promulgated: String
    public var distributionVersion: String
    public var retrievedOn: String
    public var sha256: String
    public var verification: String
    public init(id: String, title: String, publisher: String, url: String, promulgated: String,
                distributionVersion: String, retrievedOn: String, sha256: String, verification: String) {
        self.id = id; self.title = title; self.publisher = publisher; self.url = url; self.promulgated = promulgated
        self.distributionVersion = distributionVersion; self.retrievedOn = retrievedOn; self.sha256 = sha256; self.verification = verification
    }
}
public struct Framework: Codable, Equatable, Sendable {
    public var id: String
    public var label: String
    public var issuer: String
    public var version: String
    public var sourceIDs: [String]
    public var origin: Origin
    public init(id: String, label: String, issuer: String, version: String, sourceIDs: [String] = [], origin: Origin = .original) {
        self.id = id; self.label = label; self.issuer = issuer; self.version = version; self.sourceIDs = sourceIDs; self.origin = origin
    }
}
public struct Context: Codable, Equatable, Sendable {
    public var id: String
    public var label: String
    public var conditions: String
    public var frameworkID: String?
    public init(id: String, label: String, conditions: String, frameworkID: String? = nil) {
        self.id = id; self.label = label; self.conditions = conditions; self.frameworkID = frameworkID
    }
}
public struct Entity: Codable, Equatable, Sendable {
    public var id: String
    public var kind: EntityKind
    public var label: String
    public var text: String
    public var conditions: String
    public var provenance: Provenance
    public var frameworkID: String?
    public var parentID: String?
    public var externalIDs: [String: String]
    public var sourceLocator: String?
    public var targetIDs: [String]
    public var criteria: [String]
    public var prerequisiteStatus: Investigation?
    public var category: String?
    public init(id: String, kind: EntityKind, label: String, text: String, conditions: String = "", provenance: Provenance,
                frameworkID: String? = nil, parentID: String? = nil, externalIDs: [String: String] = [:], sourceLocator: String? = nil,
                targetIDs: [String] = [], criteria: [String] = [], prerequisiteStatus: Investigation? = nil, category: String? = nil) {
        self.id = id; self.kind = kind; self.label = label; self.text = text; self.conditions = conditions; self.provenance = provenance
        self.frameworkID = frameworkID; self.parentID = parentID; self.externalIDs = externalIDs; self.sourceLocator = sourceLocator
        self.targetIDs = targetIDs; self.criteria = criteria; self.prerequisiteStatus = prerequisiteStatus; self.category = category
    }
}
public struct Relation: Codable, Equatable, Sendable {
    public var id: String
    public var kind: RelationKind
    public var from: String
    public var to: String
    public var contextID: String?
    public var predicate: String
    public var coverage: Coverage?
    public var excluded: [String]
    public var strength: Strength?
    public var provenance: Provenance
    public init(id: String, kind: RelationKind, from: String, to: String, contextID: String? = nil, predicate: String,
                coverage: Coverage? = nil, excluded: [String] = [], strength: Strength? = nil, provenance: Provenance) {
        self.id = id; self.kind = kind; self.from = from; self.to = to; self.contextID = contextID; self.predicate = predicate
        self.coverage = coverage; self.excluded = excluded; self.strength = strength; self.provenance = provenance
    }
}
public struct ReadingSection: Codable, Equatable, Sendable {
    public var id: String
    public var label: String
    public var entityIDs: [String]
    public init(id: String, label: String, entityIDs: [String]) { self.id = id; self.label = label; self.entityIDs = entityIDs }
}
public struct ReadingOutline: Codable, Equatable, Sendable {
    public var id: String
    public var label: String
    public var sections: [ReadingSection]
    public init(id: String, label: String, sections: [ReadingSection]) { self.id = id; self.label = label; self.sections = sections }
}
public struct Dataset: Codable, Equatable, Sendable {
    public var schemaVersion: String = "0.1.0"
    public var release: String
    public var sources: [SourceDocument]
    public var frameworks: [Framework]
    public var contexts: [Context]
    public var entities: [Entity]
    public var relations: [Relation]
    public var readingOutlines: [ReadingOutline]
    public var limitations: [String]
    public init(release: String, sources: [SourceDocument], frameworks: [Framework], contexts: [Context], entities: [Entity], relations: [Relation], readingOutlines: [ReadingOutline], limitations: [String]) {
        self.release = release; self.sources = sources; self.frameworks = frameworks; self.contexts = contexts; self.entities = entities
        self.relations = relations; self.readingOutlines = readingOutlines; self.limitations = limitations
    }
    /// Unordered collections are sorted by ID. Reading order and criteria order are meaningful.
    public func canonicalJSON() throws -> Data {
        var copy = self
        copy.sources.sort { $0.id < $1.id }; copy.frameworks.sort { $0.id < $1.id }; copy.contexts.sort { $0.id < $1.id }
        copy.entities.sort { $0.id < $1.id }; copy.relations.sort { $0.id < $1.id }; copy.readingOutlines.sort { $0.id < $1.id }
        for i in copy.entities.indices {
            copy.entities[i].targetIDs.sort(); copy.entities[i].provenance.sourceIDs.sort()
        }
        for i in copy.frameworks.indices { copy.frameworks[i].sourceIDs.sort() }
        for i in copy.relations.indices { copy.relations[i].provenance.sourceIDs.sort(); copy.relations[i].excluded.sort() }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        var data = try encoder.encode(copy); data.append(10); return data
    }
}
