from .base_agent import BaseDomainAgent


class BuilderAgent(BaseDomainAgent):
    agent_key = "builder"
    title = "Builder IA"
    data_domains = ("kpis.company", "risks.matrix", "quality.corrective_actions")
