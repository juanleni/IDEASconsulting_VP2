from .base_agent import BaseDomainAgent


class RiskAgent(BaseDomainAgent):
    agent_key = "risk"
    title = "Riesgo IA"
    data_domains = ("risks.matrix", "alerts.company")
