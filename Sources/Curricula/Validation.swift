import Foundation

public struct ValidationIssue: Equatable, Sendable, CustomStringConvertible {
    public var code: String
    public var path: String
    public var message: String
    public var description: String { "\(code) at \(path): \(message)" }
}
public enum Validator {
    public static func validate(_ data: Dataset) -> [ValidationIssue] {
        var issues: [ValidationIssue] = []
        func report(_ code: String, _ path: String, _ message: String) {
            issues.append(.init(code: code, path: path, message: message))
        }
        let groups = [data.sources.map(\.id), data.frameworks.map(\.id), data.contexts.map(\.id), data.entities.map(\.id), data.relations.map(\.id), data.readingOutlines.map(\.id), data.readingOutlines.flatMap { $0.sections.map(\.id) }]
        var seen = Set<String>()
        for id in groups.flatMap({ $0 }) {
            if id.range(of: "^[a-z][a-z0-9.-]*$", options: .regularExpression) == nil { report("invalidID", id, "Use a stable lowercase ID") }
            if !seen.insert(id).inserted { report("duplicateID", id, "ID is already declared") }
        }
        if data.schemaVersion != "0.1.0" { report("schemaVersion", "schemaVersion", "Unsupported schema") }
        if data.release.isEmpty { report("release", "release", "Release is required") }
        let entities = Dictionary(data.entities.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        let frameworks = Set(data.frameworks.map(\.id)), sources = Set(data.sources.map(\.id)), contexts = Set(data.contexts.map(\.id))
        func reference(_ id: String, _ allowed: Set<String>, _ path: String) {
            if !allowed.contains(id) { report("missingReference", path, "Unknown ID: \(id)") }
        }
        func provenance(_ p: Provenance, _ path: String) {
            for id in p.sourceIDs { reference(id, sources, path + ".sourceIDs") }
            if p.rationale.isEmpty { report("missingRationale", path, "Record an editorial reason or evidence") }
            if p.origin == .original && p.sourceIDs.isEmpty { report("missingSource", path, "Original text requires a source") }
        }
        for f in data.frameworks { for s in f.sourceIDs { reference(s, sources, f.id + ".sourceIDs") } }
        for c in data.contexts { if let f = c.frameworkID { reference(f, frameworks, c.id + ".frameworkID") } }
        for e in data.entities {
            provenance(e.provenance, e.id + ".provenance")
            if let f = e.frameworkID { reference(f, frameworks, e.id + ".frameworkID") }
            if e.kind == .frameworkItem && e.frameworkID == nil { report("missingFramework", e.id, "Framework item requires frameworkID") }
            if let p = e.parentID {
                if let parent = entities[p] {
                    if e.kind != .frameworkItem || parent.kind != .frameworkItem || parent.frameworkID != e.frameworkID {
                        report("invalidParent", e.id, "Parent must be an item in the same framework")
                    }
                } else { report("missingReference", e.id + ".parentID", p) }
            }
            for t in e.targetIDs {
                if entities[t] == nil { report("missingReference", e.id + ".targetIDs", t) }
                else if entities[t]?.kind != .subjectMatter { report("invalidTarget", e.id, "Competency targets must be subject matter") }
            }
            if e.kind == .competency && (e.targetIDs.isEmpty || e.conditions.isEmpty || e.criteria.isEmpty || e.prerequisiteStatus == nil) {
                report("incompleteCompetency", e.id, "Targets, conditions, criteria and investigation status are required")
            }
        }
        for r in data.relations {
            provenance(r.provenance, r.id + ".provenance")
            if let c = r.contextID { reference(c, contexts, r.id + ".contextID") }
            guard let from = entities[r.from], let to = entities[r.to] else { report("missingReference", r.id, "Unknown relation endpoint: \(r.from) → \(r.to)"); continue }
            switch r.kind {
            case .alignment:
                if from.kind != .frameworkItem || to.kind == .frameworkItem { report("invalidEndpoints", r.id, "Alignment: framework item → subject matter / competency") }
                if r.coverage == nil || (r.coverage == .partial && r.excluded.isEmpty) || (r.coverage == .full && !r.excluded.isEmpty) {
                    report("invalidCoverage", r.id, "Partial coverage requires excluded scope; full coverage cannot exclude scope")
                }
            case .knowledge:
                if from.kind != .subjectMatter || to.kind != .subjectMatter { report("invalidEndpoints", r.id, "Knowledge relations require subject matter endpoints") }
            case .dependency, .enrollment:
                if from.kind != .competency || to.kind != .competency { report("invalidEndpoints", r.id, "Dependency/enrollment requires competency endpoints") }
                if r.contextID == nil || r.strength == nil { report("missingContext", r.id, "Dependency/enrollment requires context and strength") }
                if r.strength == .alternative { report("unsupportedAlternative", r.id, "AND/OR groups are not implemented; do not flatten into required edges") }
            }
        }
        func detectCycles(_ edges: [(String, String)], path: String) {
            var graph: [String: [String]] = [:]
            for (a, b) in edges { graph[a, default: []].append(b) }
            var complete = Set<String>(), active: [String] = []
            func visit(_ node: String) {
                if let start = active.firstIndex(of: node) { report("cycle", path, (Array(active[start...]) + [node]).joined(separator: " → ")); return }
                if complete.contains(node) { return }
                active.append(node)
                for next in (graph[node] ?? []).sorted() { visit(next) }
                active.removeLast(); complete.insert(node)
            }
            for node in graph.keys.sorted() { visit(node) }
        }
        detectCycles(data.entities.compactMap { e in e.parentID.map { (e.id, $0) } }, path: "frameworkHierarchy")
        for context in contexts.sorted() {
            detectCycles(data.relations.filter { $0.kind == .dependency && $0.strength == .required && $0.contextID == context }.map { ($0.from, $0.to) }, path: "dependencies[\(context)]")
        }
        for outline in data.readingOutlines { for section in outline.sections { for id in section.entityIDs { reference(id, Set(entities.keys), section.id + ".entityIDs") } } }
        return issues.sorted { ($0.path, $0.code, $0.message) < ($1.path, $1.code, $1.message) }
    }
}
