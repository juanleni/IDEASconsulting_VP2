from .base_agent import BaseDomainAgent


class LabAgent(BaseDomainAgent):
    agent_key = "lab"
    title = "LAB IA"
    data_domains = ("lab.calibrations", "lab.iso17025")
