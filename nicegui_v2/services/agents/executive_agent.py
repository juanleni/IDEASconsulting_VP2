from .base_agent import BaseDomainAgent


class ExecutiveAgent(BaseDomainAgent):
    agent_key = "executive"
    title = "Direccion IA"
    data_domains = ("kpis.company", "risks.matrix", "quality.corrective_actions", "lab.iso17025")
