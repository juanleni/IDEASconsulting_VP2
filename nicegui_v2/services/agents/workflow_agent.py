from .base_agent import BaseDomainAgent


class WorkflowAgent(BaseDomainAgent):
    agent_key = "workflow"
    title = "Workflow IA"
    data_domains = ("quality.corrective_actions", "alerts.company", "documents.expiring")
