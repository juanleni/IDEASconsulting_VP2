from .base_agent import BaseDomainAgent


class KPIAgent(BaseDomainAgent):
    agent_key = "kpi"
    title = "KPI IA"
    data_domains = ("kpis.company", "quality.corrective_actions")
