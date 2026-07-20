from .base_agent import BaseDomainAgent


class EnvironmentalAgent(BaseDomainAgent):
    agent_key = "environmental"
    title = "Ambiente IA"
    data_domains = ("environmental.indicators", "documents.expiring")
