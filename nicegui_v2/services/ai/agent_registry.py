from __future__ import annotations

from services.agents import (
    AuditAgent,
    BuilderAgent,
    EnvironmentalAgent,
    ExecutiveAgent,
    KPIAgent,
    LabAgent,
    MaintenanceAgent,
    QualityAgent,
    RiskAgent,
    SafetyAgent,
    WorkflowAgent,
)


def build_agent_registry() -> dict[str, object]:
    agents = [
        QualityAgent(),
        EnvironmentalAgent(),
        SafetyAgent(),
        LabAgent(),
        KPIAgent(),
        AuditAgent(),
        RiskAgent(),
        MaintenanceAgent(),
        ExecutiveAgent(),
        WorkflowAgent(),
        BuilderAgent(),
    ]
    return {str(agent.agent_key): agent for agent in agents}
