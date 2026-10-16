"""Sincroniza D09 PlantUML y vistas temáticas con el Mermaid de la sección 9.

Uso: python scripts/generar_modelo_er.py
Solo requiere Python 3. No interpreta ni modifica el diccionario de datos.
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/secciones/03-datos-api.md"
OUTPUT = ROOT / "docs/diagramas"

STYLE = """@startuml
!pragma layout smetana
hide circle
skinparam backgroundColor #FFFFFF
skinparam shadowing false
skinparam defaultFontName Arial
skinparam defaultFontSize 14
skinparam ArrowColor #526E87
skinparam entityBackgroundColor #EAF3FA
skinparam noteBackgroundColor #FFF4D6
skinparam nodesep 50
skinparam ranksep 55
top to bottom direction
"""

NOTES = [
    "PK = primaria · FK = foránea · UK = única · o = opcional · | = uno · { = varios",
    "Atributos estructurales; obligatoriedad, enums, índices y restricciones completos en §8.",
]
RULES = [
    "chunks: exactamente un origen, document_id o source_version_id.",
    "exports.origin_kind: CONVERSATION_SUMMARY = conversation_id + draft_id; DRAFT = solo draft_id; ACCOUNT = solo privacy_request_id.",
    "citations(run_id,chunk_id) referencia el par efectivamente recuperado en retrieved_evidence.",
    "artifacts.kind exige un subtipo compatible; artifact_dependencies es un DAG del mismo propietario.",
]

# Las tablas repetidas son referencias al mismo esquema, no copias de datos.
VIEWS = [
    ("D09a-acceso", "D09a · Acceso, MFA y auditoría", {
        "users", "sessions", "password_reset_tokens", "mfa_credentials",
        "mfa_challenges", "mfa_recovery_codes", "audit_events",
    }, []),
    ("D09b-expedientes", "D09b · Expedientes, conversación y reportes", {
        "users", "cases", "documents", "conversations", "messages", "feedback", "ai_runs",
    }, ["messages.run_id es opcional para USER y obligatorio para ASSISTANT; feedback solo comparte el fragmento elegido."]),
    ("D09c-evidencia", "D09c · Fuentes, recuperación y evidencia", {
        "legal_sources", "source_versions", "documents", "chunks", "ai_runs",
        "retrieved_evidence", "citations", "analyses",
    }, RULES[:1] + RULES[2:3]),
    ("D09d-resultados", "D09d · Borradores, exportaciones y privacidad", {
        "users", "cases", "conversations", "ai_runs", "drafts", "exports", "privacy_requests",
    }, RULES[1:2]),
    ("D09e-artefactos", "D09e · Artefactos e invalidación de derivados", {
        "users", "artifacts", "artifact_dependencies", "documents", "messages", "ai_runs",
        "analyses", "drafts", "exports",
    }, RULES[3:4]),
    ("D09f-trabajos", "D09f · Trabajos persistidos y recursos procesados", {
        "users", "jobs", "documents", "source_versions", "ai_runs", "privacy_requests", "exports",
    }, ["jobs.requested_by puede ser NULL para trabajo del sistema; leases y generaciones protegen la publicación."]),
]


def parse_mermaid(text):
    section = text.split("## 9. Modelo entidad-relación", 1)[1].split("## 10.", 1)[0]
    block = re.search(r"```mermaid\s+erDiagram\s+(.*?)```", section, re.S)
    if not block:
        raise ValueError("No se encontró el ER Mermaid de §9")
    entities = {}
    current = None
    relationships = []
    for raw in block.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        entity = re.fullmatch(r"(\w+)\s*\{", line)
        if entity:
            current = entity.group(1)
            entities[current] = []
        elif line == "}":
            current = None
        elif current:
            field = re.fullmatch(r"(\S+)\s+(\w+)(?:\s+([A-Z,]+))?", line)
            if not field:
                raise ValueError(f"Atributo no reconocido: {line}")
            datatype, name, keys = field.groups()
            entities[current].append((name, datatype, keys))
        else:
            relation = re.fullmatch(r"(\w+)\s+([|o}{]+)(--|\.\.)([|o}{]+)\s+(\w+)\s*:\s*(.+)", line)
            if not relation:
                raise ValueError(f"Relación no reconocida: {line}")
            left, cardinal_left, connector, cardinal_right, right, label = relation.groups()
            # Mermaid escribe o| en el extremo izquierdo; PlantUML requiere |o.
            if cardinal_left == "o|":
                cardinal_left = "|o"
            relationships.append((left, cardinal_left + connector + cardinal_right, right, label))
    if not entities or not relationships:
        raise ValueError("Modelo vacío")
    for left, _, right, _ in relationships:
        if left not in entities or right not in entities:
            raise ValueError(f"Relación con entidad desconocida: {left}, {right}")
    return entities, relationships


def write_view(name, title, selected, notes, entities, relationships, overview=False):
    missing = selected - entities.keys()
    if missing:
        raise ValueError(f"Entidades faltantes para {name}: {sorted(missing)}")
    lines = [STYLE, "' Generado desde §9 por scripts/generar_modelo_er.py; editar el Mermaid de origen."]
    lines += ["title", title, "Claves y cardinalidades · diccionario completo en §8", "end title"]
    for entity, fields in entities.items():
        if entity not in selected:
            continue
        lines.append(f'entity "{entity}" as {entity} {{')
        for field, datatype, keys in fields:
            suffix = f" <<{keys}>>" if keys else ""
            lines.append(f"  {field} : {datatype}{suffix}")
        lines.append("}")
    included = set()
    for relation in relationships:
        left, cardinalities, right, label = relation
        if left in selected and right in selected:
            lines.append(f"{left} {cardinalities} {right} : {label}")
            included.add(relation)
    lines += ["legend bottom"] + NOTES
    if not overview:
        lines.append("Vista parcial: las tablas repetidas designan las mismas entidades; todas las relaciones figuran en D09.")
    lines += notes + ["endlegend", "@enduml", ""]
    (OUTPUT / f"{name}.puml").write_text("\n".join(lines), encoding="utf-8")
    return included


def main():
    entities, relationships = parse_mermaid(SOURCE.read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_view("D09-modelo-datos", "D09 · Modelo entidad-relación completo",
               set(entities), RULES, entities, relationships, overview=True)
    covered = set()
    for name, title, selected, notes in VIEWS:
        covered |= write_view(name, title, selected, notes, entities, relationships)
    omitted = set(relationships) - covered
    if omitted:
        raise ValueError(f"Relaciones sin vista temática: {sorted(omitted)}")
    print(f"D09: {len(entities)} entidades y {len(relationships)} relaciones; 6 vistas cubren todas las relaciones.")


if __name__ == "__main__":
    main()
