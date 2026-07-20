from .base_agent import BaseDomainAgent


class AuditAgent(BaseDomainAgent):
    agent_key = "audit"
    title = "Auditor IA"
    data_domains = ("lab.iso17025", "quality.corrective_actions", "documents.expiring")
