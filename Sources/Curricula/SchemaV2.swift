import Foundation

/// The 0.2 exchange contract. Version 0.1 remains readable and reproducible.
public enum V2 {
    public struct Ref: Codable, Equatable, Hashable, Sendable {
        public var id: String
        public var revisionID: String
        public init(_ id: String, _ revisionID: String) { self.id = id; self.revisionID = revisionID }
    }
    public enum Stage: String, Codable, Sendable { case elementary, lowerSecondary, upperSecondary, higherEducation, other }
    public enum GradeStatus: String, Codable, Sendable { case specified, notSpecified, notApplicable }
    public struct Education: Codable, Equatable, Hashable, Sendable {
        public var stage: Stage
        public var gradeStatus: GradeStatus
        public var grades: [Int]
        public var subjectID: String
        public var courseID: String?
        public init(stage: Stage, grades: [Int] = [], gradeStatus: GradeStatus = .notSpecified, subjectID: String, courseID: String? = nil) {
            self.stage = stage; self.grades = grades; self.gradeStatus = gradeStatus; self.subjectID = subjectID; self.courseID = courseID
        }
    }
    public enum TaxonKind: String, Codable, Sendable { case subject, course }
    public struct Taxon: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var kind: TaxonKind; public var label: String; public var parentID: String?
        public init(_ ref: Ref, kind: TaxonKind, label: String, parentID: String? = nil) {
            id = ref.id; revisionID = ref.revisionID; self.kind = kind; self.label = label; self.parentID = parentID
        }
    }
    public enum SourceKind: String, Codable, Sendable { case curriculum, commentary, book, article, syllabus, referenceStandard, webPage }
    public struct Source: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var kind: SourceKind; public var origin: Origin; public var title: String
        public var creators: [String] = []; public var publisher: String?; public var scope: String
        public var url: String?; public var issuedOn: String?; public var promulgatedOn: String?
        public var edition: String?; public var identifiers: [String: String] = [:]
        public var retrievedOn: String?; public var sha256: String?; public var verification: String?
        public init(_ ref: Ref, kind: SourceKind, origin: Origin, title: String, scope: String) {
            id = ref.id; revisionID = ref.revisionID; self.kind = kind; self.origin = origin; self.title = title; self.scope = scope
        }
    }
    public struct Provenance: Codable, Equatable, Sendable {
        public var origin: Origin; public var rationale: String
        public init(_ origin: Origin, _ rationale: String) { self.origin = origin; self.rationale = rationale }
    }
    public struct Framework: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var label: String; public var issuer: String; public var version: String
        public var sourceIDs: [String]; public var origin: Origin; public var education: [Education]
        public init(_ ref: Ref, label: String, issuer: String, version: String, sourceIDs: [String], origin: Origin, education: [Education]) {
            id = ref.id; revisionID = ref.revisionID; self.label = label; self.issuer = issuer; self.version = version
            self.sourceIDs = sourceIDs; self.origin = origin; self.education = education
        }
    }
    public struct Context: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var label: String; public var conditions: String; public var frameworkID: String?; public var education: [Education]
        public init(_ ref: Ref, label: String, conditions: String, frameworkID: String? = nil, education: [Education] = []) {
            id = ref.id; revisionID = ref.revisionID; self.label = label; self.conditions = conditions; self.frameworkID = frameworkID; self.education = education
        }
    }
    public enum EntityKind: String, Codable, Sendable { case frameworkItem, subjectMatter, goal }
    public enum Lifecycle: String, Codable, Sendable { case active, retired }
    public struct Entity: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var kind: EntityKind; public var label: String; public var text: String
        public var conditions: String = ""; public var education: [Education] = []
        public var provenance: Provenance; public var frameworkID: String?; public var parentID: String?
        public var externalIDs: [String: String] = [:]; public var sourceLocator: String?
        public var targetIDs: [String] = []; public var prerequisiteStatus: Investigation?; public var category: String?
        public var lifecycle: Lifecycle = .active; public var successorIDs: [String] = []
        public init(_ ref: Ref, kind: EntityKind, label: String, text: String, provenance: Provenance) {
            id = ref.id; revisionID = ref.revisionID; self.kind = kind; self.label = label; self.text = text; self.provenance = provenance
        }
        public var ref: Ref { .init(id, revisionID) }
    }
    public enum EvaluationMode: String, Codable, Sendable { case unspecified, humanObservation, software }
    /// Observations are optional annotations on goals, never a prerequisite for retaining a goal.
    public struct Annotation: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var goal: Ref; public var text: String; public var position: Int
        public var evaluationMode: EvaluationMode = .unspecified
        public var evaluatorID: String?; public var provenance: Provenance
        public init(_ ref: Ref, goal: Ref, text: String, position: Int, provenance: Provenance) {
            id = ref.id; revisionID = ref.revisionID; self.goal = goal; self.text = text; self.position = position; self.provenance = provenance
        }
    }
    public enum EvidenceField: String, Codable, Sendable { case text, conditions, education, coverage, expression }
    public struct Citation: Codable, Equatable, Sendable {
        public var source: Ref; public var locator: String
        public var item: Ref?
        public init(source: Ref, locator: String, item: Ref? = nil) { self.source = source; self.locator = locator; self.item = item }
    }
    public enum EvidenceRole: String, Codable, Sendable { case quotation, supports, contextualizes }
    public struct Evidence: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var target: Ref; public var field: EvidenceField; public var role: EvidenceRole
        public var citations: [Citation]; public var rationale: String
        public init(_ ref: Ref, target: Ref, field: EvidenceField, role: EvidenceRole = .supports, citations: [Citation], rationale: String) {
            id = ref.id; revisionID = ref.revisionID; self.target = target; self.field = field; self.role = role; self.citations = citations; self.rationale = rationale
        }
    }
    public enum RelationKind: String, Codable, Sendable { case alignment, knowledge, enrollment }
    public struct Relation: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var kind: RelationKind; public var from: String; public var to: String; public var contextID: String?
        public var predicate: String; public var coverage: Coverage?; public var excluded: [String] = []
        public var provenance: Provenance
        public init(_ ref: Ref, kind: RelationKind, from: String, to: String, predicate: String, provenance: Provenance) {
            id = ref.id; revisionID = ref.revisionID; self.kind = kind; self.from = from; self.to = to; self.predicate = predicate; self.provenance = provenance
        }
    }
    public enum Operator: String, Codable, Sendable { case goal, allOf, anyOf }
    public struct Requirement: Codable, Equatable, Sendable {
        public var op: Operator; public var goalID: String?; public var operands: [Requirement]
        public init(goalID: String) { op = .goal; self.goalID = goalID; operands = [] }
        public init(_ op: Operator, _ operands: [Requirement]) { self.op = op; self.operands = operands }
        public var goalIDs: Set<String> { op == .goal ? Set(goalID.map { [$0] } ?? []) : operands.reduce(into: Set<String>()) { $0.formUnion($1.goalIDs) } }
        public func isSatisfied(by goals: Set<String>) -> Bool {
            switch op {
            case .goal: return goalID.map(goals.contains) ?? false
            case .allOf: return !operands.isEmpty && operands.allSatisfy { $0.isSatisfied(by: goals) }
            case .anyOf: return operands.contains { $0.isSatisfied(by: goals) }
            }
        }
    }
    public enum Necessity: String, Codable, Sendable { case required, recommended }
    public struct Prerequisite: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String
        public var targetGoalID: String; public var contextID: String; public var strength: Necessity
        public var expression: Requirement; public var provenance: Provenance
        public init(_ ref: Ref, targetGoalID: String, contextID: String, strength: Necessity, expression: Requirement, provenance: Provenance) {
            id = ref.id; revisionID = ref.revisionID; self.targetGoalID = targetGoalID; self.contextID = contextID
            self.strength = strength; self.expression = expression; self.provenance = provenance
        }
    }
    public struct Section: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String; public var label: String; public var entityIDs: [String]
        public init(_ ref: Ref, label: String, entityIDs: [String]) { id = ref.id; revisionID = ref.revisionID; self.label = label; self.entityIDs = entityIDs }
    }
    public struct Outline: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String; public var label: String; public var sections: [Section]
        public init(_ ref: Ref, label: String, sections: [Section]) { id = ref.id; revisionID = ref.revisionID; self.label = label; self.sections = sections }
    }
    public struct SnapshotRef: Codable, Equatable, Sendable {
        public var release: String; public var record: Ref
        public init(release: String, record: Ref) { self.release = release; self.record = record }
    }
    public enum ChangeKind: String, Codable, Sendable { case edit, split, merge }
    public struct Change: Codable, Equatable, Sendable {
        public var id: String; public var revisionID: String; public var kind: ChangeKind
        public var before: [SnapshotRef]; public var after: [SnapshotRef]; public var rationale: String
        public init(_ ref: Ref, kind: ChangeKind, before: [SnapshotRef], after: [SnapshotRef], rationale: String) {
            id = ref.id; revisionID = ref.revisionID; self.kind = kind; self.before = before; self.after = after; self.rationale = rationale
        }
    }
    public struct Dataset: Codable, Equatable, Sendable {
        public var schemaVersion = "0.2.0"
        public var release: String
        public var aliases: [String: String] = [:]
        public var taxons: [Taxon] = []; public var sources: [Source] = []; public var frameworks: [Framework] = []
        public var contexts: [Context] = []; public var entities: [Entity] = []; public var annotations: [Annotation] = []
        public var evidence: [Evidence] = []; public var relations: [Relation] = []; public var prerequisites: [Prerequisite] = []
        public var readingOutlines: [Outline] = []; public var changes: [Change] = []; public var limitations: [String] = []
        public init(release: String) { self.release = release }
        public var recordRefs: [Ref] {
            taxons.map { .init($0.id, $0.revisionID) } + sources.map { .init($0.id, $0.revisionID) }
            + frameworks.map { .init($0.id, $0.revisionID) } + contexts.map { .init($0.id, $0.revisionID) }
            + entities.map(\.ref) + annotations.map { .init($0.id, $0.revisionID) }
            + evidence.map { .init($0.id, $0.revisionID) } + relations.map { .init($0.id, $0.revisionID) }
            + prerequisites.map { .init($0.id, $0.revisionID) } + readingOutlines.map { .init($0.id, $0.revisionID) }
            + readingOutlines.flatMap { $0.sections.map { Ref($0.id, $0.revisionID) } } + changes.map { .init($0.id, $0.revisionID) }
        }
        public func canonicalJSON() throws -> Data {
            // Swift and external consumers share the same key ordering. Arrays with authored order retain it.
            var d = self
            d.taxons.sort { $0.id < $1.id }; d.sources.sort { $0.id < $1.id }; d.frameworks.sort { $0.id < $1.id }
            d.contexts.sort { $0.id < $1.id }; d.entities.sort { $0.id < $1.id }; d.annotations.sort { $0.id < $1.id }
            d.evidence.sort { $0.id < $1.id }; d.relations.sort { $0.id < $1.id }; d.prerequisites.sort { $0.id < $1.id }
            d.readingOutlines.sort { $0.id < $1.id }; d.changes.sort { $0.id < $1.id }
            let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
            var bytes = try encoder.encode(d); bytes.append(10); return bytes
        }
    }
}
