from .base_agent import BaseDomainAgent


class SafetyAgent(BaseDomainAgent):
    agent_key = "safety"
    title = "Seguridad IA"
    data_domains = ("alerts.company", "risks.matrix")
