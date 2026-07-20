from .base_agent import BaseDomainAgent


class QualityAgent(BaseDomainAgent):
    agent_key = "quality"
    title = "Calidad IA"
    data_domains = ("quality.corrective_actions",)
