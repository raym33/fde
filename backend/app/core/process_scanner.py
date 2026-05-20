"""Process Scanner: first step toward an AI implementation scanner.

The scanner turns process artifacts (SOPs, emails, tickets, invoices, CSV
exports, interview notes) into an auditable map of processes and automation
candidates. It does not touch production systems; it proposes sandbox-first
experiments with human approval.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


ArtifactType = Literal[
    "procedure",
    "email_sample",
    "ticket_sample",
    "invoice_sample",
    "csv_export",
    "interview_notes",
    "policy",
    "other",
]

AutomationMode = Literal["copilot", "human_approval", "partial_automation", "do_not_automate"]


class ProcessArtifact(BaseModel):
    name: str
    artifact_type: ArtifactType = "other"
    text: str
    system: str | None = None
    department: str | None = None
    volume_per_month: int | None = None


class ProcessScannerRequest(BaseModel):
    company_name: str = "Cliente"
    employee_count: int | None = None
    objective: str = "Detectar procesos automatizables con IA"
    artifacts: list[ProcessArtifact]
    risk_tolerance: Literal["low", "medium", "high"] = "medium"


class ProcessStep(BaseModel):
    id: str
    label: str
    systems: list[str] = Field(default_factory=list)
    data_objects: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class ProcessMap(BaseModel):
    primary_processes: list[str]
    systems: list[str]
    data_objects: list[str]
    actors: list[str]
    steps: list[ProcessStep]
    bottlenecks: list[str]
    sensitive_data: list[str]


class DeployabilityScore(BaseModel):
    total: float
    repetition: int
    data_readiness: int
    risk: int
    integration_effort: int
    measurability: int
    human_approval_need: int


class SandboxPlan(BaseModel):
    dataset: str
    anonymization: list[str]
    replay_method: str
    success_metrics: list[str]
    go_no_go: list[str]
    expected_duration_days: int


class AutomationCandidate(BaseModel):
    id: str
    title: str
    problem: str
    proposed_solution: str
    mode: AutomationMode
    tools: list[str]
    data_needed: list[str]
    risks: list[str]
    first_sandbox: SandboxPlan
    score: DeployabilityScore
    recommended_phase: str


class ProcessScannerResult(BaseModel):
    company_name: str
    objective: str
    readiness_label: str
    process_map: ProcessMap
    candidates: list[AutomationCandidate]
    quick_wins: list[str]
    sandbox_first: list[str]
    do_not_automate_yet: list[str]
    missing_context: list[str]
    governance_notes: list[str]
    disclaimer: str = (
        "Este scanner no ejecuta acciones en producción. Las automatizaciones "
        "deben probarse con datos históricos o anonimizados, medirse contra un "
        "baseline humano y aprobarse antes de integrarse en sistemas reales."
    )


@dataclass(frozen=True)
class CandidateTemplate:
    id: str
    title: str
    problem: str
    proposed_solution: str
    mode: AutomationMode
    tools: list[str]
    data_needed: list[str]
    risks: list[str]
    keywords: set[str]
    systems: set[str]
    base: dict[str, int]
    success_metrics: list[str]


_SYSTEM_KEYWORDS = {
    "Microsoft 365": {"outlook", "excel", "sharepoint", "teams", "office", "microsoft 365"},
    "Google Workspace": {"gmail", "google drive", "sheets", "docs", "calendar"},
    "ERP": {"erp", "sap", "sage", "holded", "a3", "contaplus", "odoo", "dynamics"},
    "CRM": {"crm", "salesforce", "hubspot", "pipedrive", "zoho"},
    "Ticketing": {"zendesk", "freshdesk", "jira", "servicedesk", "ticket", "tickets"},
    "File Share": {"nas", "carpeta compartida", "servidor de archivos", "drive", "sharepoint"},
    "Email": {"email", "correo", "outlook", "gmail", "buzón", "buzon"},
}

_DATA_OBJECTS = {
    "facturas": {"factura", "facturas", "proveedor", "albarán", "albaran", "iva"},
    "emails": {"email", "correo", "buzón", "buzon", "respuesta"},
    "tickets": {"ticket", "incidencia", "reclamación", "reclamacion", "soporte"},
    "contratos": {"contrato", "cláusula", "clausula", "legal", "expediente"},
    "clientes": {"cliente", "clientes", "lead", "contacto", "crm"},
    "pedidos": {"pedido", "orden", "sap", "erp", "stock"},
    "documentos internos": {"procedimiento", "manual", "política", "politica", "sop"},
}

_ACTORS = {
    "administración": {"administración", "administracion", "contabilidad", "finanzas", "cfo"},
    "soporte": {"soporte", "atención al cliente", "atencion al cliente", "helpdesk"},
    "ventas": {"ventas", "comercial", "sales", "lead"},
    "operaciones": {"operaciones", "producción", "produccion", "logística", "logistica"},
    "legal/compliance": {"legal", "compliance", "rgpd", "gdpr", "ai act"},
    "IT": {"it", "sistemas", "ciberseguridad", "seguridad"},
}

_SENSITIVE_TERMS = {
    "datos personales": {"dni", "nif", "email", "teléfono", "telefono", "dirección", "direccion"},
    "datos sanitarios": {"paciente", "historia clínica", "historia clinica", "diagnóstico", "diagnostico"},
    "datos financieros": {"iban", "banco", "factura", "nómina", "nomina", "salario", "importe"},
    "datos legales": {"contrato", "expediente", "demanda", "cláusula", "clausula"},
}

_CANDIDATES = [
    CandidateTemplate(
        id="email_triage_responder",
        title="Triage y borradores de respuesta para emails repetitivos",
        problem="El equipo responde manualmente consultas similares y pierde tiempo clasificando prioridades.",
        proposed_solution="Clasificar correos, recuperar contexto interno y generar borradores con aprobación humana.",
        mode="human_approval",
        tools=["Microsoft Graph/Gmail API", "RAG local", "LM Studio/Ollama", "n8n"],
        data_needed=["emails históricos", "FAQs", "precios/horarios", "políticas de respuesta"],
        risks=["respuesta incorrecta al cliente", "datos personales en correo", "tono no alineado"],
        keywords={"email", "correo", "buzón", "buzon", "respuesta", "consulta", "cliente", "faq"},
        systems={"Email", "Microsoft 365", "Google Workspace"},
        base={"repetition": 5, "data": 4, "risk": 3, "integration": 2, "measure": 4, "approval": 4},
        success_metrics=["% emails clasificados correctamente", "tiempo medio de respuesta", "% borradores aprobados sin edición"],
    ),
    CandidateTemplate(
        id="invoice_extraction_validation",
        title="Extracción y prevalidación de facturas",
        problem="La entrada de facturas y validación contra reglas contables consume tiempo y genera errores.",
        proposed_solution="Extraer campos de facturas, validar reglas y preparar borrador para revisión.",
        mode="human_approval",
        tools=["OCR/document parser", "RAG de reglas contables", "ERP export/import CSV", "n8n"],
        data_needed=["facturas históricas", "plan contable", "proveedores", "reglas de aprobación"],
        risks=["error contable", "datos fiscales sensibles", "integración ERP incompleta"],
        keywords={"factura", "facturas", "proveedor", "contabilidad", "erp", "iva", "conciliación", "conciliacion"},
        systems={"ERP", "File Share"},
        base={"repetition": 5, "data": 4, "risk": 4, "integration": 3, "measure": 5, "approval": 5},
        success_metrics=["precisión de extracción", "% facturas sin excepción", "minutos ahorrados por factura"],
    ),
    CandidateTemplate(
        id="ticket_knowledge_copilot",
        title="Copiloto de soporte con base de conocimiento interna",
        problem="Los tickets repetitivos dependen de expertos y documentación dispersa.",
        proposed_solution="Responder o sugerir respuestas con RAG sobre manuales, tickets resueltos y FAQs.",
        mode="copilot",
        tools=["Zendesk/Freshdesk/Jira API", "RAG local", "BM25+vector retrieval", "LM Studio/Ollama"],
        data_needed=["tickets históricos", "manuales", "FAQs", "políticas de escalado"],
        risks=["alucinación sin cita", "permisos documentales", "escalado humano insuficiente"],
        keywords={"ticket", "tickets", "soporte", "incidencia", "faq", "manual", "helpdesk", "sla"},
        systems={"Ticketing", "File Share"},
        base={"repetition": 4, "data": 4, "risk": 3, "integration": 2, "measure": 4, "approval": 3},
        success_metrics=["deflection rate", "first contact resolution", "citas correctas en respuestas"],
    ),
    CandidateTemplate(
        id="document_search_policy_copilot",
        title="Buscador documental y copiloto de procedimientos",
        problem="Los usuarios pierden tiempo buscando procedimientos, contratos y políticas vigentes.",
        proposed_solution="Indexar documentos internos con permisos y responder con citas obligatorias.",
        mode="copilot",
        tools=["RAG local", "SharePoint/Drive/NAS connector", "embeddings locales", "feedback de usuarios"],
        data_needed=["procedimientos", "manuales", "políticas", "contratos", "owners documentales"],
        risks=["documentos obsoletos", "permisos mal aplicados", "respuesta sin fuente"],
        keywords={"procedimiento", "manual", "política", "politica", "documento", "contrato", "buscar", "rag"},
        systems={"File Share", "Microsoft 365", "Google Workspace"},
        base={"repetition": 4, "data": 5, "risk": 2, "integration": 2, "measure": 4, "approval": 2},
        success_metrics=["tiempo hasta encontrar respuesta", "% respuestas con cita válida", "satisfacción de usuarios"],
    ),
    CandidateTemplate(
        id="csv_reporting_anomaly",
        title="Informes automáticos y detección de anomalías en CSV/Excel",
        problem="Los informes se construyen manualmente copiando datos entre Excel, ERP o CRM.",
        proposed_solution="Analizar exports, detectar anomalías y generar informe ejecutivo con revisión humana.",
        mode="partial_automation",
        tools=["CSV/Excel parser", "n8n", "Python analysis", "LLM para narrativa ejecutiva"],
        data_needed=["exports CSV/Excel", "definición de KPIs", "informes anteriores", "umbrales de alerta"],
        risks=["datos incompletos", "KPIs mal definidos", "conclusiones sin validación"],
        keywords={"csv", "excel", "informe", "reporting", "kpi", "dashboard", "anomalía", "anomalia"},
        systems={"ERP", "CRM", "Microsoft 365", "Google Workspace"},
        base={"repetition": 4, "data": 4, "risk": 2, "integration": 2, "measure": 5, "approval": 2},
        success_metrics=["horas ahorradas por informe", "anomalías confirmadas", "reducción de errores de copia"],
    ),
]


def scan_processes(body: ProcessScannerRequest) -> ProcessScannerResult:
    if not body.artifacts:
        raise ValueError("Se necesita al menos un artefacto de proceso.")

    corpus = "\n".join([body.objective, *[a.text for a in body.artifacts]])
    systems = _detect_systems(body.artifacts, corpus)
    data_objects = _detect_named(_DATA_OBJECTS, corpus)
    actors = _detect_named(_ACTORS, corpus)
    sensitive = _detect_named(_SENSITIVE_TERMS, corpus)
    steps = _build_steps(body.artifacts, systems, data_objects, actors)
    bottlenecks = _detect_bottlenecks(corpus)

    process_map = ProcessMap(
        primary_processes=_infer_processes(corpus, data_objects),
        systems=systems,
        data_objects=data_objects,
        actors=actors,
        steps=steps,
        bottlenecks=bottlenecks,
        sensitive_data=sensitive,
    )
    candidates = [
        _score_candidate(t, body, corpus, systems, data_objects, sensitive)
        for t in _CANDIDATES
    ]
    candidates.sort(key=lambda c: (-c.score.total, c.score.risk, c.score.integration_effort))
    candidates = [c for c in candidates if c.score.total >= 48][:6]
    if not candidates:
        candidates = [_score_candidate(_CANDIDATES[3], body, corpus, systems, data_objects, sensitive)]

    quick_wins = [
        c.id for c in candidates
        if c.score.total >= 76 and c.score.risk <= 3 and c.score.integration_effort <= 3
    ][:3]
    sandbox_first = [
        c.id for c in candidates
        if c.mode in {"human_approval", "partial_automation"} or c.score.risk >= 3
    ][:4]
    do_not_automate = [
        c.id for c in candidates
        if c.score.risk >= 5 or c.score.data_readiness <= 2
    ][:3]

    return ProcessScannerResult(
        company_name=body.company_name,
        objective=body.objective,
        readiness_label=_readiness_label(candidates),
        process_map=process_map,
        candidates=candidates,
        quick_wins=quick_wins,
        sandbox_first=sandbox_first,
        do_not_automate_yet=do_not_automate,
        missing_context=_missing_context(body, systems, data_objects),
        governance_notes=_governance_notes(body, sensitive),
    )


def render_markdown(result: ProcessScannerResult) -> str:
    lines: list[str] = [
        "## AI Implementation Scanner",
        "",
        f"**Empresa:** {result.company_name}",
        f"**Estado:** {result.readiness_label}",
        "",
        "### Mapa operativo detectado",
        "",
        f"- Procesos: {', '.join(result.process_map.primary_processes) or 'no detectados'}",
        f"- Sistemas: {', '.join(result.process_map.systems) or 'no detectados'}",
        f"- Datos: {', '.join(result.process_map.data_objects) or 'no detectados'}",
        f"- Riesgos de datos: {', '.join(result.process_map.sensitive_data) or 'no detectados'}",
        "",
        "### Candidatos de automatización",
        "",
        "| # | Candidato | Modo | Score | Fase | Primer sandbox |",
        "|---:|---|---|---:|---|---|",
    ]
    for idx, candidate in enumerate(result.candidates, start=1):
        lines.append(
            f"| {idx} | {candidate.title} | {candidate.mode} | {candidate.score.total} | "
            f"{candidate.recommended_phase} | {candidate.first_sandbox.dataset} |"
        )
    lines.append("")

    for candidate in result.candidates[:3]:
        lines.append(f"**{candidate.title}**")
        lines.append(f"- Problema: {candidate.problem}")
        lines.append(f"- Solución: {candidate.proposed_solution}")
        lines.append(f"- Herramientas: {', '.join(candidate.tools)}")
        lines.append(f"- Métricas sandbox: {', '.join(candidate.first_sandbox.success_metrics)}")
        lines.append(f"- Riesgos: {'; '.join(candidate.risks)}")
        lines.append("")

    if result.missing_context:
        lines.append("### Contexto que falta")
        lines.extend(f"- {item}" for item in result.missing_context)
        lines.append("")

    lines.append("### Gobierno mínimo")
    lines.extend(f"- {item}" for item in result.governance_notes)
    lines.append("")
    lines.append(f"_{result.disclaimer}_")
    return "\n".join(lines)


def _score_candidate(
    template: CandidateTemplate,
    body: ProcessScannerRequest,
    corpus: str,
    systems: list[str],
    data_objects: list[str],
    sensitive: list[str],
) -> AutomationCandidate:
    hits = _hit_count(template.keywords, corpus)
    system_hits = len(template.systems & set(systems))
    artifact_bonus = _artifact_bonus(template.id, body.artifacts)
    repetition = _clamp(template.base["repetition"] + min(2, hits // 3))
    data = _clamp(template.base["data"] + min(1, artifact_bonus))
    risk = _risk_score(template.base["risk"], body.risk_tolerance, sensitive, template.id)
    integration = _clamp(template.base["integration"] + (0 if system_hits else 1))
    measure = _clamp(template.base["measure"] + (1 if any(a.volume_per_month for a in body.artifacts) else 0))
    approval = _clamp(template.base["approval"] + (1 if risk >= 4 else 0))
    total = _deployability_total(
        repetition=repetition,
        data=data,
        risk=risk,
        integration=integration,
        measure=measure,
        approval=approval,
    )
    mode = template.mode
    if risk >= 5:
        mode = "do_not_automate"
    elif risk >= 4 and template.mode == "partial_automation":
        mode = "human_approval"

    return AutomationCandidate(
        id=template.id,
        title=template.title,
        problem=template.problem,
        proposed_solution=template.proposed_solution,
        mode=mode,
        tools=template.tools,
        data_needed=template.data_needed,
        risks=template.risks,
        first_sandbox=SandboxPlan(
            dataset=_sandbox_dataset(template.id, body.artifacts),
            anonymization=_anonymization(sensitive),
            replay_method=_replay_method(template.id),
            success_metrics=template.success_metrics,
            go_no_go=_go_no_go(template.id, risk),
            expected_duration_days=10 if integration <= 2 else 15,
        ),
        score=DeployabilityScore(
            total=total,
            repetition=repetition,
            data_readiness=data,
            risk=risk,
            integration_effort=integration,
            measurability=measure,
            human_approval_need=approval,
        ),
        recommended_phase=_phase(total, risk, integration),
    )


def _deployability_total(
    *,
    repetition: int,
    data: int,
    risk: int,
    integration: int,
    measure: int,
    approval: int,
) -> float:
    inverse_risk = 6 - risk
    inverse_integration = 6 - integration
    inverse_approval = 6 - approval
    total = (
        repetition * 0.24
        + data * 0.20
        + inverse_risk * 0.16
        + inverse_integration * 0.16
        + measure * 0.16
        + inverse_approval * 0.08
    )
    return round((total / 5) * 100, 1)


def _detect_systems(artifacts: list[ProcessArtifact], corpus: str) -> list[str]:
    found = set(_detect_named(_SYSTEM_KEYWORDS, corpus))
    for artifact in artifacts:
        if artifact.system:
            found.add(artifact.system)
    return sorted(found)


def _detect_named(catalog: dict[str, set[str]], text: str) -> list[str]:
    low = text.lower()
    return sorted([name for name, terms in catalog.items() if any(term in low for term in terms)])


def _build_steps(
    artifacts: list[ProcessArtifact],
    systems: list[str],
    data_objects: list[str],
    actors: list[str],
) -> list[ProcessStep]:
    steps = []
    for idx, artifact in enumerate(artifacts[:8], start=1):
        summary = _summarize_artifact(artifact.text)
        steps.append(
            ProcessStep(
                id=f"step_{idx}",
                label=summary or artifact.name,
                systems=[artifact.system] if artifact.system else systems[:2],
                data_objects=_objects_in_text(artifact.text, data_objects),
                actors=_objects_in_text(artifact.text, actors),
                evidence=[artifact.name],
            )
        )
    return steps


def _summarize_artifact(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    for sentence in sentences:
        if len(sentence) >= 25:
            return sentence[:150]
    return clean[:150]


def _objects_in_text(text: str, candidates: list[str]) -> list[str]:
    low = text.lower()
    return [item for item in candidates if item.lower() in low][:4]


def _infer_processes(corpus: str, data_objects: list[str]) -> list[str]:
    processes = []
    low = corpus.lower()
    if any(term in low for term in ["factura", "contabilidad", "proveedor"]):
        processes.append("administración y facturación")
    if any(term in low for term in ["email", "correo", "consulta", "cliente"]):
        processes.append("atención y comunicación con cliente")
    if any(term in low for term in ["ticket", "incidencia", "soporte"]):
        processes.append("soporte y resolución de incidencias")
    if any(term in low for term in ["informe", "csv", "excel", "kpi"]):
        processes.append("reporting operativo")
    if any(term in low for term in ["procedimiento", "manual", "contrato", "política", "politica"]):
        processes.append("gestión documental interna")
    if not processes and data_objects:
        processes.append(f"proceso documental sobre {data_objects[0]}")
    return processes[:5]


def _detect_bottlenecks(corpus: str) -> list[str]:
    low = corpus.lower()
    checks = [
        ("copiar y pegar entre sistemas", {"copiar", "pegar", "manual", "duplicar"}),
        ("esperas por aprobación humana", {"aprobar", "aprobación", "aprobacion", "validar"}),
        ("búsqueda documental lenta", {"buscar", "no encuentro", "documento", "manual"}),
        ("clasificación repetitiva", {"clasificar", "categorizar", "priorizar"}),
        ("entrada manual de datos", {"introducir", "rellenar", "teclear", "excel"}),
    ]
    out = [label for label, terms in checks if any(term in low for term in terms)]
    return out or ["falta cuantificar tiempos, volúmenes y excepciones del proceso"]


def _artifact_bonus(candidate_id: str, artifacts: list[ProcessArtifact]) -> int:
    types = {artifact.artifact_type for artifact in artifacts}
    mapping = {
        "email_triage_responder": {"email_sample"},
        "invoice_extraction_validation": {"invoice_sample", "csv_export"},
        "ticket_knowledge_copilot": {"ticket_sample", "procedure"},
        "document_search_policy_copilot": {"procedure", "policy"},
        "csv_reporting_anomaly": {"csv_export"},
    }
    return 1 if mapping.get(candidate_id, set()) & types else 0


def _risk_score(base: int, tolerance: str, sensitive: list[str], candidate_id: str) -> int:
    value = base
    if sensitive:
        value += 1
    if tolerance == "low":
        value += 1
    if candidate_id == "invoice_extraction_validation" and "datos financieros" in sensitive:
        value += 1
    return _clamp(value)


def _sandbox_dataset(candidate_id: str, artifacts: list[ProcessArtifact]) -> str:
    volumes = [a.volume_per_month for a in artifacts if a.volume_per_month]
    sample = min(max(volumes) if volumes else 50, 500)
    labels = {
        "email_triage_responder": f"{sample} emails históricos etiquetados por resultado humano",
        "invoice_extraction_validation": f"{sample} facturas históricas con campos validados",
        "ticket_knowledge_copilot": f"{sample} tickets resueltos + artículos de conocimiento",
        "document_search_policy_copilot": "50 preguntas reales contra documentos internos críticos",
        "csv_reporting_anomaly": f"{sample} filas/exportaciones históricas con informe humano de referencia",
    }
    return labels.get(candidate_id, "muestra histórica anonimizada del proceso")


def _anonymization(sensitive: list[str]) -> list[str]:
    if not sensitive:
        return ["reemplazar nombres de cliente por identificadores sintéticos"]
    return [
        "enmascarar identificadores personales y fiscales",
        "sustituir clientes/proveedores por códigos sintéticos",
        "mantener importes y fechas solo si son necesarios para medir precisión",
    ]


def _replay_method(candidate_id: str) -> str:
    mapping = {
        "email_triage_responder": "replay offline: email histórico -> clasificación + borrador -> comparación con respuesta humana",
        "invoice_extraction_validation": "replay offline: factura histórica -> extracción -> validación contra campos humanos",
        "ticket_knowledge_copilot": "replay offline: ticket histórico -> respuesta sugerida con citas -> comparación con resolución real",
        "document_search_policy_copilot": "evaluación RAG: pregunta real -> respuesta con cita -> revisión humana",
        "csv_reporting_anomaly": "replay analítico: export histórico -> informe/anomalías -> comparación con informe humano",
    }
    return mapping.get(candidate_id, "replay offline contra resultado humano histórico")


def _go_no_go(candidate_id: str, risk: int) -> list[str]:
    base = [
        "precisión mínima del 85% en casos normales",
        "100% de acciones críticas quedan como borrador o requieren aprobación",
        "errores clasificados y revisados por owner humano antes de producción",
    ]
    if risk >= 4:
        base.append("validación legal/compliance antes de cualquier integración real")
    if candidate_id == "invoice_extraction_validation":
        base.append("0 pagos o asientos contables automáticos en fase piloto")
    return base


def _phase(total: float, risk: int, integration: int) -> str:
    if total >= 78 and risk <= 3 and integration <= 2:
        return "Semana 1-4 prototipo"
    if total >= 68:
        return "Semana 5-8 piloto sandbox"
    return "Semana 9-12 evaluar antes de desplegar"


def _readiness_label(candidates: list[AutomationCandidate]) -> str:
    best = candidates[0].score.total if candidates else 0
    if best >= 80:
        return "alto potencial: empezar por sandbox controlado"
    if best >= 68:
        return "potencial medio: recopilar contexto y pilotar"
    return "preparación baja: ordenar datos/procesos antes de automatizar"


def _missing_context(
    body: ProcessScannerRequest,
    systems: list[str],
    data_objects: list[str],
) -> list[str]:
    missing = []
    if len(body.artifacts) < 3:
        missing.append("Añadir al menos 3 artefactos: procedimiento, ejemplo real y export de datos.")
    if not systems:
        missing.append("Indicar sistemas implicados: ERP, CRM, correo, carpetas, ticketing.")
    if not data_objects:
        missing.append("Aportar ejemplos de datos: facturas, emails, tickets, contratos o CSV.")
    if not any(a.volume_per_month for a in body.artifacts):
        missing.append("Incluir volumen mensual para estimar ROI y tamaño de sandbox.")
    if body.employee_count is None:
        missing.append("Indicar tamaño aproximado de empresa/equipo afectado.")
    return missing[:5]


def _governance_notes(body: ProcessScannerRequest, sensitive: list[str]) -> list[str]:
    notes = [
        "Empezar en modo solo lectura o sandbox; no tocar producción en el primer ciclo.",
        "Registrar owner humano, criterios go/no-go y plan de rollback por candidato.",
        "Guardar evidencias: dataset usado, métricas, errores y aprobaciones.",
    ]
    if sensitive:
        notes.append("Aplicar anonimización y permisos mínimos por contener datos sensibles: " + ", ".join(sensitive))
    if body.risk_tolerance == "low":
        notes.append("Usar IA local/RAG privado por defecto y escalar a cloud solo con datos no sensibles.")
    return notes


def _hit_count(terms: set[str], text: str) -> int:
    low = text.lower()
    return sum(1 for term in terms if term in low)


def _clamp(value: int) -> int:
    return max(1, min(5, value))
