"""AI Opportunity Discovery for SMEs.

This workflow answers the hardest first question for many SMEs: *where should
we implement AI inside the company?*  The ranking is deterministic and
auditable; the LLM may later add narrative, but it does not invent the scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import Citation, RetrievedChunk


CompanySize = Literal["small", "mid_market", "large"]


class OpportunityScore(BaseModel):
    total: float
    impact: int
    effort: int
    data_readiness: int
    risk: int
    time_to_value: int
    strategic_fit: int
    confidence: int


class Opportunity(BaseModel):
    id: str
    area: str
    title: str
    problem: str
    ai_solution: str
    expected_value: str
    annual_benefit_eur: tuple[int, int]
    setup_cost_eur: tuple[int, int]
    monthly_cost_eur: tuple[int, int]
    score: OpportunityScore
    recommended_phase: str
    owner: str
    data_needed: list[str] = Field(default_factory=list)
    first_experiment: str
    risks: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class OpportunityDiagnosis(BaseModel):
    question: str
    company_size: CompanySize
    assumed_employee_count: int | None = None
    top_opportunities: list[Opportunity]
    quick_wins: list[str]
    strategic_bets: list[str]
    not_now: list[str]
    roadmap_90_days: list[dict]
    missing_context: list[str]
    rationale: str
    disclaimer: str = (
        "Las cifras son estimaciones orientativas. Antes de invertir, valide "
        "volúmenes, costes internos, calidad de datos, riesgos RGPD/EU AI Act "
        "y responsable humano de cada iniciativa."
    )


@dataclass(frozen=True)
class OpportunityTemplate:
    id: str
    area: str
    title: str
    problem: str
    ai_solution: str
    expected_value: str
    annual_benefit_eur: tuple[int, int]
    setup_cost_eur: tuple[int, int]
    monthly_cost_eur: tuple[int, int]
    owner: str
    data_needed: list[str]
    first_experiment: str
    risks: list[str]
    keywords: set[str]
    base: dict[str, int]
    evidence_terms: set[str] = field(default_factory=set)


_OPPORTUNITIES: list[OpportunityTemplate] = [
    OpportunityTemplate(
        id="support_knowledge_agent",
        area="Atención al cliente / Soporte",
        title="Agente de soporte con RAG sobre FAQs, tickets y manuales",
        problem="Tickets repetitivos, tiempos de respuesta altos y conocimiento disperso.",
        ai_solution="Chatbot interno/externo con RAG, escalado humano y analítica de motivos.",
        expected_value="Reduce tickets de nivel 1, mejora SLA y captura conocimiento operativo.",
        annual_benefit_eur=(60000, 240000),
        setup_cost_eur=(6000, 25000),
        monthly_cost_eur=(300, 2500),
        owner="Responsable de Soporte + IT + VirtuDirector IA",
        data_needed=["FAQs", "histórico de tickets", "manuales", "políticas de escalado"],
        first_experiment="PoC de 2 semanas con las 50 preguntas más frecuentes y medición de deflection rate.",
        risks=["Respuestas incorrectas al cliente", "datos personales en tickets", "necesidad de escalado humano"],
        keywords={"soporte", "ticket", "tickets", "cliente", "clientes", "faq", "helpdesk", "chatbot", "call center"},
        evidence_terms={"ticket", "faq", "soporte", "sla", "cliente"},
        base={"impact": 5, "effort": 2, "data": 4, "risk": 3, "ttv": 2},
    ),
    OpportunityTemplate(
        id="sales_lead_scoring",
        area="Ventas",
        title="Scoring de leads y priorización comercial",
        problem="El equipo comercial dedica tiempo a oportunidades con baja probabilidad de cierre.",
        ai_solution="Modelo de scoring + recomendaciones de siguiente acción en CRM.",
        expected_value="Aumenta conversión, reduce ciclo de venta y mejora foco del equipo comercial.",
        annual_benefit_eur=(50000, 300000),
        setup_cost_eur=(8000, 30000),
        monthly_cost_eur=(400, 2500),
        owner="Dirección Comercial + RevOps/CRM",
        data_needed=["CRM", "histórico de oportunidades", "motivos de pérdida", "fuentes de lead"],
        first_experiment="Entrenar scoring con 12-24 meses de CRM y comparar top 20% vs conversión real.",
        risks=["Sesgos comerciales", "datos CRM incompletos", "rechazo del equipo si no es explicable"],
        keywords={"ventas", "comercial", "crm", "leads", "lead", "oportunidades", "pipeline", "conversion", "conversión"},
        evidence_terms={"crm", "lead", "pipeline", "venta", "oportunidad"},
        base={"impact": 5, "effort": 3, "data": 3, "risk": 2, "ttv": 3},
    ),
    OpportunityTemplate(
        id="document_search_copilot",
        area="Operaciones / Conocimiento interno",
        title="Buscador documental y copiloto interno",
        problem="Los empleados pierden tiempo buscando procedimientos, contratos, políticas y documentación.",
        ai_solution="RAG interno con permisos, citas obligatorias y feedback de calidad.",
        expected_value="Ahorro transversal de tiempo y menor dependencia de expertos saturados.",
        annual_benefit_eur=(80000, 400000),
        setup_cost_eur=(7000, 35000),
        monthly_cost_eur=(300, 3000),
        owner="IT + Operaciones + responsables documentales",
        data_needed=["SharePoint/Drive", "manuales", "contratos", "políticas", "procedimientos"],
        first_experiment="Indexar 200 documentos críticos y medir precisión con 40 preguntas reales.",
        risks=["Permisos mal aplicados", "documentos obsoletos", "alucinación sin cita"],
        keywords={"documentos", "documental", "procedimientos", "manuales", "intranet", "conocimiento", "rag", "buscador"},
        evidence_terms={"manual", "procedimiento", "política", "documento", "contrato"},
        base={"impact": 5, "effort": 2, "data": 4, "risk": 2, "ttv": 2},
    ),
    OpportunityTemplate(
        id="finance_invoice_automation",
        area="Finanzas / Administración",
        title="Automatización inteligente de facturas y conciliación",
        problem="Procesos manuales de facturas, validación, imputación y conciliación contable.",
        ai_solution="OCR/document AI + reglas + revisión humana para excepciones.",
        expected_value="Reduce coste administrativo, errores y tiempos de cierre mensual.",
        annual_benefit_eur=(40000, 180000),
        setup_cost_eur=(10000, 40000),
        monthly_cost_eur=(500, 3000),
        owner="CFO + Administración + IT",
        data_needed=["facturas", "ERP", "plan contable", "reglas de aprobación", "proveedores"],
        first_experiment="Procesar 500 facturas históricas y medir precisión de extracción e imputación.",
        risks=["Errores contables", "integración ERP", "datos fiscales sensibles"],
        keywords={"facturas", "factura", "contabilidad", "finanzas", "erp", "conciliación", "conciliacion", "proveedores"},
        evidence_terms={"factura", "proveedor", "erp", "contable", "conciliación"},
        base={"impact": 4, "effort": 3, "data": 4, "risk": 3, "ttv": 3},
    ),
    OpportunityTemplate(
        id="hr_employee_assistant",
        area="RRHH",
        title="Asistente de RRHH para políticas, onboarding y consultas internas",
        problem="RRHH responde muchas preguntas repetidas y el onboarding depende de personas concretas.",
        ai_solution="Asistente con RAG sobre políticas internas, convenios, onboarding y escalado a RRHH.",
        expected_value="Reduce consultas repetitivas y acelera onboarding sin perder control humano.",
        annual_benefit_eur=(25000, 120000),
        setup_cost_eur=(6000, 25000),
        monthly_cost_eur=(250, 1800),
        owner="Dirección RRHH + IT",
        data_needed=["manual del empleado", "políticas RRHH", "onboarding", "organigrama", "FAQs"],
        first_experiment="Piloto interno con 30 empleados nuevos y 80 preguntas frecuentes.",
        risks=["Datos personales", "respuestas laborales con impacto legal", "necesidad de disclaimer y escalado"],
        keywords={"rrhh", "recursos humanos", "empleados", "onboarding", "formación", "formacion", "políticas rrhh"},
        evidence_terms={"empleado", "onboarding", "rrhh", "política", "convenio"},
        base={"impact": 3, "effort": 2, "data": 3, "risk": 3, "ttv": 2},
    ),
    OpportunityTemplate(
        id="procurement_vendor_intelligence",
        area="Compras / Supply Chain",
        title="Inteligencia de proveedores y compras",
        problem="Dificultad para comparar proveedores, detectar riesgos y optimizar condiciones.",
        ai_solution="Análisis de proveedores, contratos, incidencias y señales externas de riesgo.",
        expected_value="Mejora negociación, reduce riesgo de proveedor y descubre ahorro recurrente.",
        annual_benefit_eur=(50000, 250000),
        setup_cost_eur=(12000, 45000),
        monthly_cost_eur=(500, 3500),
        owner="Compras + Finanzas + Legal",
        data_needed=["proveedores", "contratos", "pedidos", "incidencias", "precios históricos"],
        first_experiment="Analizar top 30 proveedores por gasto y proponer oportunidades de renegociación.",
        risks=["Datos contractuales sensibles", "fuentes externas incompletas", "falsos positivos de riesgo"],
        keywords={"compras", "proveedores", "supply", "suministro", "contratos", "pedidos", "stock"},
        evidence_terms={"proveedor", "contrato", "pedido", "stock", "suministro"},
        base={"impact": 4, "effort": 3, "data": 3, "risk": 3, "ttv": 3},
    ),
    OpportunityTemplate(
        id="marketing_content_ops",
        area="Marketing",
        title="Producción y adaptación de contenido con control de marca",
        problem="Crear, adaptar y revisar contenido multicanal consume mucho tiempo.",
        ai_solution="Copiloto de contenido con guías de marca, revisión legal y reutilización de activos.",
        expected_value="Acelera campañas y reduce coste de contenido manteniendo consistencia.",
        annual_benefit_eur=(30000, 160000),
        setup_cost_eur=(5000, 22000),
        monthly_cost_eur=(300, 2500),
        owner="Marketing + Legal/Compliance",
        data_needed=["guía de marca", "campañas anteriores", "catálogo", "aprobaciones", "claims permitidos"],
        first_experiment="Generar 3 variantes de una campaña y medir tiempo de aprobación y calidad.",
        risks=["Claims no aprobados", "tono de marca inconsistente", "copyright/licencias"],
        keywords={"marketing", "campañas", "campanas", "contenido", "redes", "seo", "marca", "copy"},
        evidence_terms={"marca", "campaña", "contenido", "seo", "catálogo"},
        base={"impact": 3, "effort": 2, "data": 3, "risk": 2, "ttv": 1},
    ),
    OpportunityTemplate(
        id="quality_anomaly_detection",
        area="Calidad / Producción",
        title="Detección de anomalías y soporte a calidad",
        problem="Incidencias de calidad detectadas tarde o con análisis manual lento.",
        ai_solution="Modelos de anomalías sobre registros, sensores, reclamaciones o inspecciones visuales.",
        expected_value="Reduce defectos, retrabajo y coste de no calidad.",
        annual_benefit_eur=(70000, 500000),
        setup_cost_eur=(20000, 90000),
        monthly_cost_eur=(1000, 6000),
        owner="Operaciones + Calidad + IT/OT",
        data_needed=["incidencias", "sensores", "órdenes de producción", "reclamaciones", "imágenes si aplica"],
        first_experiment="Tomar una línea/proceso y comparar alertas contra incidencias reales de 6 meses.",
        risks=["Datos industriales dispersos", "integración OT", "falsos positivos operativos"],
        keywords={"calidad", "producción", "produccion", "fábrica", "fabrica", "sensores", "anomalías", "anomalias", "defectos"},
        evidence_terms={"calidad", "producción", "defecto", "sensor", "incidencia"},
        base={"impact": 5, "effort": 4, "data": 2, "risk": 3, "ttv": 4},
    ),
    OpportunityTemplate(
        id="it_security_triage",
        area="IT / Seguridad",
        title="Triage de tickets IT y alertas de seguridad",
        problem="IT y seguridad reciben tickets/alertas repetitivas con priorización manual.",
        ai_solution="Clasificación, resumen, priorización y playbooks asistidos con humano en el loop.",
        expected_value="Reduce tiempo de respuesta, mejora priorización y captura aprendizaje operativo.",
        annual_benefit_eur=(40000, 220000),
        setup_cost_eur=(8000, 35000),
        monthly_cost_eur=(400, 3000),
        owner="CIO/CISO + Service Desk",
        data_needed=["tickets IT", "alertas", "CMDB", "playbooks", "histórico de incidentes"],
        first_experiment="Clasificar 1.000 tickets históricos y medir precisión de prioridad/categoría.",
        risks=["Exposición de datos sensibles", "automatizaciones peligrosas si no hay aprobación humana"],
        keywords={"it", "seguridad", "ciberseguridad", "tickets it", "alertas", "incidentes", "service desk"},
        evidence_terms={"ticket", "alerta", "incidente", "seguridad", "playbook"},
        base={"impact": 4, "effort": 3, "data": 4, "risk": 4, "ttv": 3},
    ),
    OpportunityTemplate(
        id="executive_ai_governance",
        area="Dirección / Gobierno IA",
        title="Gobierno IA, portfolio y control de ROI",
        problem="La empresa prueba IA de forma dispersa, sin priorización, riesgos ni medición de valor.",
        ai_solution="Portfolio de casos de uso, registro de riesgos, políticas y comité de decisión asistido.",
        expected_value="Evita proyectos fallidos, prioriza inversión y reduce riesgo regulatorio.",
        annual_benefit_eur=(50000, 300000),
        setup_cost_eur=(8000, 30000),
        monthly_cost_eur=(500, 3000),
        owner="CEO/COO + IT + Legal + VirtuDirector IA",
        data_needed=["organigrama", "procesos", "sistemas", "políticas", "proyectos IA existentes"],
        first_experiment="Workshop de 2 horas + inventario de 10 procesos críticos y scoring de portfolio.",
        risks=["Falta de sponsor ejecutivo", "decisiones sin datos", "políticas que nadie adopta"],
        keywords={"estrategia", "roadmap", "gobierno", "portfolio", "priorizar", "donde", "dónde", "implementar ia"},
        evidence_terms={"proceso", "roadmap", "gobierno", "política", "riesgo"},
        base={"impact": 5, "effort": 2, "data": 2, "risk": 2, "ttv": 2},
    ),
]


def diagnose_opportunities(
    question: str,
    chunks: list[RetrievedChunk] | None = None,
    *,
    client_name: str,
    employee_count: int | None = None,
    top_k: int = 8,
) -> OpportunityDiagnosis:
    chunks = chunks or []
    company_size = _infer_company_size(question, employee_count)
    inferred_employees = employee_count or _infer_employee_count(question)
    evidence_text = _evidence_text(question, chunks)

    opportunities = [
        _score_template(t, question, evidence_text, chunks, company_size)
        for t in _OPPORTUNITIES
    ]
    opportunities.sort(
        key=lambda o: (-o.score.total, o.score.risk, o.setup_cost_eur[0])
    )
    selected = opportunities[:top_k]

    quick_wins = [
        o.id for o in selected
        if o.score.effort <= 2 and o.score.time_to_value <= 2 and o.score.risk <= 3
    ][:4]
    strategic_bets = [
        o.id for o in selected
        if o.score.impact >= 5 and (o.score.effort >= 3 or o.score.risk >= 3)
    ][:3]
    not_now = [
        o.id for o in opportunities
        if o.score.effort >= 4 and o.score.data_readiness <= 2
    ][:3]

    rationale = (
        f"Para {client_name}, el mapa prioriza oportunidades con impacto alto, "
        "datos razonablemente disponibles, bajo riesgo operativo y tiempo a valor "
        "corto. El primer ciclo debe validar valor con pilotos pequeños antes de "
        "integrar automatizaciones en procesos críticos."
    )

    return OpportunityDiagnosis(
        question=question,
        company_size=company_size,
        assumed_employee_count=inferred_employees,
        top_opportunities=selected,
        quick_wins=quick_wins,
        strategic_bets=strategic_bets,
        not_now=not_now,
        roadmap_90_days=_roadmap(selected),
        missing_context=_missing_context(evidence_text),
        rationale=rationale,
    )


def render_markdown(d: OpportunityDiagnosis) -> str:
    lines: list[str] = []
    lines.append("## Mapa de oportunidades IA para la pyme")
    lines.append("")
    lines.append(d.rationale)
    lines.append("")
    if d.assumed_employee_count:
        lines.append(f"**Tamaño asumido:** {d.assumed_employee_count} empleados · perfil: {d.company_size}.")
    else:
        lines.append(f"**Perfil asumido:** {d.company_size}.")
    lines.append("")

    lines.append("### Top oportunidades priorizadas")
    lines.append("")
    lines.append("| # | Área | Oportunidad | Score | ROI anual estimado | Coste inicial | Fase | Confianza |")
    lines.append("|---:|---|---|---:|---:|---:|---|---:|")
    for i, o in enumerate(d.top_opportunities, 1):
        lines.append(
            f"| {i} | {o.area} | {o.title} | {o.score.total} | "
            f"{o.annual_benefit_eur[0]:,}–{o.annual_benefit_eur[1]:,}€ | "
            f"{o.setup_cost_eur[0]:,}–{o.setup_cost_eur[1]:,}€ | "
            f"{o.recommended_phase} | {o.score.confidence}% |"
        )
    lines.append("")

    lines.append("### Recomendación ejecutiva")
    lines.append("")
    for o in d.top_opportunities[:3]:
        lines.append(f"**{o.area}: {o.title}**")
        lines.append(f"- Problema: {o.problem}")
        lines.append(f"- Solución IA: {o.ai_solution}")
        lines.append(f"- Primer experimento: {o.first_experiment}")
        lines.append(f"- Datos necesarios: {', '.join(o.data_needed)}")
        lines.append(f"- Riesgos: {'; '.join(o.risks)}")
        lines.append("")

    id_to_title = {o.id: o.title for o in d.top_opportunities}
    if d.quick_wins:
        lines.append("### Quick wins")
        lines.extend(f"- {id_to_title.get(i, i)}" for i in d.quick_wins)
        lines.append("")
    if d.strategic_bets:
        lines.append("### Apuestas estratégicas")
        lines.extend(f"- {id_to_title.get(i, i)}" for i in d.strategic_bets)
        lines.append("")
    if d.not_now:
        lines.append("### No priorizar todavía")
        lines.extend(f"- {i}" for i in d.not_now)
        lines.append("")

    lines.append("### Roadmap 90 días")
    lines.append("")
    for item in d.roadmap_90_days:
        lines.append(
            f"{item['phase']}. {item['name']} — {item['weeks']} semanas · "
            f"owner: {item['owner']} · entregable: {item['deliverable']}"
        )
    lines.append("")

    if d.missing_context:
        lines.append("### Información que conviene pedir al cliente")
        lines.append("")
        lines.extend(f"- {x}" for x in d.missing_context)
        lines.append("")

    lines.append(f"_{d.disclaimer}_")
    return "\n".join(lines)


def _score_template(
    t: OpportunityTemplate,
    question: str,
    evidence_text: str,
    chunks: list[RetrievedChunk],
    company_size: CompanySize,
) -> Opportunity:
    keyword_hits = _hit_count(t.keywords, question)
    evidence_hits = _hit_count(t.evidence_terms | t.keywords, evidence_text)
    strategic_fit = _strategic_fit(t, keyword_hits, evidence_hits, company_size)

    impact = _boost(t.base["impact"], 1 if company_size == "mid_market" and t.area in {
        "Operaciones / Conocimiento interno",
        "Dirección / Gobierno IA",
        "Atención al cliente / Soporte",
    } else 0)
    effort = t.base["effort"]
    data = _boost(t.base["data"], 1 if evidence_hits >= 2 else 0)
    risk = t.base["risk"]
    ttv = t.base["ttv"]
    confidence = min(88, 45 + keyword_hits * 8 + evidence_hits * 5 + min(len(chunks), 4) * 3)

    total = _weighted_score(
        impact=impact,
        effort=effort,
        data=data,
        risk=risk,
        ttv=ttv,
        strategic_fit=strategic_fit,
    )
    phase = _recommended_phase(total, effort, risk, data)
    citations = _citations_for_template(t, chunks)

    return Opportunity(
        id=t.id,
        area=t.area,
        title=t.title,
        problem=t.problem,
        ai_solution=t.ai_solution,
        expected_value=t.expected_value,
        annual_benefit_eur=t.annual_benefit_eur,
        setup_cost_eur=t.setup_cost_eur,
        monthly_cost_eur=t.monthly_cost_eur,
        score=OpportunityScore(
            total=total,
            impact=impact,
            effort=effort,
            data_readiness=data,
            risk=risk,
            time_to_value=ttv,
            strategic_fit=strategic_fit,
            confidence=confidence,
        ),
        recommended_phase=phase,
        owner=t.owner,
        data_needed=t.data_needed,
        first_experiment=t.first_experiment,
        risks=t.risks,
        citations=citations,
    )


def _weighted_score(
    *,
    impact: int,
    effort: int,
    data: int,
    risk: int,
    ttv: int,
    strategic_fit: int,
) -> float:
    inverse_effort = 6 - effort
    inverse_risk = 6 - risk
    inverse_ttv = 6 - ttv
    total = (
        impact * 0.28
        + data * 0.15
        + inverse_effort * 0.15
        + inverse_risk * 0.12
        + inverse_ttv * 0.14
        + strategic_fit * 0.16
    )
    return round((total / 5) * 100, 1)


def _strategic_fit(
    t: OpportunityTemplate,
    keyword_hits: int,
    evidence_hits: int,
    company_size: CompanySize,
) -> int:
    value = 2 + min(2, keyword_hits) + min(1, evidence_hits // 2)
    if company_size == "mid_market" and t.id in {
        "document_search_copilot",
        "executive_ai_governance",
        "support_knowledge_agent",
    }:
        value += 1
    return max(1, min(5, value))


def _recommended_phase(total: float, effort: int, risk: int, data: int) -> str:
    if total >= 78 and effort <= 2 and risk <= 3:
        return "0-30 días"
    if total >= 70 and data >= 3:
        return "31-60 días"
    if total >= 62:
        return "61-90 días"
    return "Backlog"


def _roadmap(selected: list[Opportunity]) -> list[dict]:
    top = selected[:3]
    return [
        {
            "phase": 1,
            "name": "Inventario de procesos y datos",
            "weeks": 2,
            "owner": "COO/IT + VirtuDirector IA",
            "deliverable": "Mapa de procesos, sistemas, datos y riesgos por área",
        },
        {
            "phase": 2,
            "name": f"Piloto quick win: {top[0].title if top else 'caso de uso prioritario'}",
            "weeks": 3,
            "owner": top[0].owner if top else "humano+IA",
            "deliverable": "PoC medible con baseline, ROI y criterio go/no-go",
        },
        {
            "phase": 3,
            "name": "Gobierno IA mínimo viable",
            "weeks": 2,
            "owner": "Dirección + Legal/Compliance + IT",
            "deliverable": "Registro de casos de uso, riesgos, responsables y política de uso IA",
        },
        {
            "phase": 4,
            "name": f"Segundo piloto: {top[1].title if len(top) > 1 else 'siguiente oportunidad priorizada'}",
            "weeks": 5,
            "owner": top[1].owner if len(top) > 1 else "humano+IA",
            "deliverable": "Piloto operativo con métricas de adopción y plan de escalado",
        },
    ]


def _missing_context(text: str) -> list[str]:
    checks = [
        ("Mapa de procesos por departamento", {"proceso", "procedimiento", "flujo"}),
        ("Sistemas principales: ERP, CRM, ticketing, HRIS, BI", {"erp", "crm", "ticket", "hris", "bi"}),
        ("Volúmenes: tickets/mes, facturas/mes, leads/mes, empleados por área", {"mes", "volumen", "tickets", "facturas", "leads"}),
        ("Coste horario aproximado por perfil y tiempos actuales", {"coste", "hora", "tiempo", "sla"}),
        ("Riesgos y restricciones RGPD/EU AI Act por proceso", {"rgpd", "ai act", "riesgo", "compliance"}),
    ]
    lower = text.lower()
    missing = [label for label, terms in checks if not any(t in lower for t in terms)]
    return missing[:5]


def _citations_for_template(t: OpportunityTemplate, chunks: list[RetrievedChunk]) -> list[Citation]:
    citations: list[Citation] = []
    for chunk in chunks:
        text = chunk.text.lower()
        if any(term in text for term in t.evidence_terms):
            citations.append(
                Citation(
                    source_id=f"{chunk.document_id}#{chunk.chunk_id}",
                    source_type="document" if chunk.metadata.get("kind") != "platform_knowledge_brief" else "knowledge_base",
                    snippet=chunk.text[:260],
                    date=chunk.metadata.get("uploaded_at"),
                )
            )
        if len(citations) >= 2:
            break
    if not citations:
        citations.append(
            Citation(
                source_id=f"opportunity_catalog:{t.id}",
                source_type="knowledge_base",
                snippet="Patrón de oportunidad curado por VirtuDirector IA para pymes.",
            )
        )
    return citations


def _hit_count(terms: set[str], text: str) -> int:
    lower = text.lower()
    return sum(1 for term in terms if term in lower)


def _evidence_text(question: str, chunks: list[RetrievedChunk]) -> str:
    return "\n".join([question, *[c.text for c in chunks[:12]]])


def _boost(value: int, amount: int) -> int:
    return max(1, min(5, value + amount))


def _infer_employee_count(question: str) -> int | None:
    import re

    match = re.search(r"(\d{2,5})\s*(empleados|personas|trabajadores)", question.lower())
    if match:
        return int(match.group(1))
    if "pyme mediana" in question.lower():
        return 500
    return None


def _infer_company_size(question: str, employee_count: int | None) -> CompanySize:
    count = employee_count or _infer_employee_count(question)
    if count is None:
        return "mid_market" if "pyme" in question.lower() else "small"
    if count < 100:
        return "small"
    if count <= 1000:
        return "mid_market"
    return "large"
