from .base_agent import BaseDomainAgent


class MaintenanceAgent(BaseDomainAgent):
    agent_key = "maintenance"
    title = "Mantenimiento IA"
    data_domains = ("lab.calibrations", "alerts.company")
