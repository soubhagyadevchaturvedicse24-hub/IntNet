"""
Report Domain Service for CRIMENET.
Orchestrates live case data extraction, report generation, version lineage,
cryptographic SHA-256 sealing, BOLA/BFLA policy authorization, and audit logging.
Strictly zero mock data — only reports generated from real case evidence are stored.
"""

import time
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.auth.service import AuthService
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService
from src.cases.service import CaseService
from src.artifacts.repository import SQLiteArtifactRepository
from src.parsers.repository import SQLiteParsedArtifactRepository
from src.reports.models import (
    ReportDetail,
    ReportSummaryItem,
    ReportGenerateRequest
)
from src.reports.repository import SQLiteReportRepository
from src.reports.generator import ReportGenerator


class ReportService:
    def __init__(
        self,
        repository: Optional[SQLiteReportRepository] = None,
        case_service: Optional[CaseService] = None,
        artifact_repo: Optional[SQLiteArtifactRepository] = None,
        parsed_repo: Optional[SQLiteParsedArtifactRepository] = None,
        entity_graph_service: Optional[Any] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_service: Optional[AuditService] = None,
        auth_service: Optional[AuthService] = None
    ):
        self.repository = repository or SQLiteReportRepository()
        self.case_service = case_service or CaseService()
        self.artifact_repo = artifact_repo or SQLiteArtifactRepository()
        self.parsed_repo = parsed_repo or SQLiteParsedArtifactRepository()
        self.entity_graph_service = entity_graph_service
        self.policy_engine = policy_engine or getattr(self.case_service, "policy_engine", PolicyEngine())
        self.audit_service = audit_service or getattr(self.case_service, "audit_service", AuditService())
        self.auth_service = auth_service or getattr(self.case_service, "auth_service", AuthService())

    def _verify_auth(
        self,
        actor: TokenPayload,
        action: str,
        resource_id: str,
        target_case_id: str,
        resource_type: str = "report"
    ):
        user = self.auth_service.get_user_by_id(actor.sub)
        user_authorized_cases = user.authorized_case_ids if user else []

        req = AuthorizationRequest(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            target_case_id=target_case_id
        )

        decision = self.policy_engine.evaluate(req, user_authorized_cases)

        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value if hasattr(actor.role, "value") else str(actor.role),
            case_id=target_case_id,
            action=action,
            target_resource=f"{resource_type}:{resource_id}",
            decision="ALLOW" if decision.allowed else "DENY",
            metadata={"reason": decision.reason}
        )

        if not decision.allowed:
            raise PermissionError(f"Authorization Denied: {decision.reason}")

    def list_reports(self, actor: TokenPayload, case_id: str) -> List[ReportSummaryItem]:
        """
        Lists all generated reports for a specific case.
        Zero mock data: returns empty list if no reports have been generated yet.
        """
        self._verify_auth(actor, action="READ_CASE", resource_id=case_id, target_case_id=case_id, resource_type="case")
        return self.repository.list_by_case(case_id)

    def get_report(self, actor: TokenPayload, case_id: str, report_id: str) -> Optional[ReportDetail]:
        """
        Retrieves a full report by ID, verifying case boundary.
        """
        self._verify_auth(actor, action="READ_REPORT", resource_id=report_id, target_case_id=case_id, resource_type="report")
        return self.repository.get_by_id(case_id, report_id)

    def generate_report(
        self,
        actor: TokenPayload,
        case_id: str,
        request: ReportGenerateRequest
    ) -> ReportDetail:
        """
        Generates a new analytical report from LIVE case-scoped data only.
        Computes cryptographic SHA-256 digest, sets up version lineage,
        registers BOLA resource binding, and stores in repository.
        """
        self._verify_auth(actor, action="READ_CASE", resource_id=case_id, target_case_id=case_id, resource_type="case")

        # 1. Fetch live case metadata
        case = self.case_service.get_case(actor, case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found or access denied.")

        # 2. Fetch live artifacts
        try:
            artifacts = self.artifact_repo.list_by_case(case_id)
        except Exception:
            artifacts = []

        # 3. Fetch live graph data
        graph_data = {"nodes": [], "edges": [], "anchor": None}
        if self.entity_graph_service and hasattr(self.entity_graph_service, "get_case_graph"):
            try:
                graph_data = self.entity_graph_service.get_case_graph(actor, case_id)
            except Exception:
                pass

        # 4. Fetch parsed observations count
        obs_count = 0
        try:
            if hasattr(self.parsed_repo, "count_by_case"):
                obs_count = self.parsed_repo.count_by_case(case_id)
        except Exception:
            pass

        # 5. Determine version lineage
        existing_reports = self.repository.list_by_case(case_id)
        version_count = len(existing_reports)
        previous_version_id = None

        if version_count == 0:
            version_str = "v1.0"
            version_number = 1
        else:
            latest = self.repository.get_latest_for_case(case_id)
            if latest:
                previous_version_id = latest.report_id
                version_number = latest.version_number + 1
            else:
                version_number = version_count + 1
            version_str = f"v{version_number}.0"

        # 6. Generate report using live data
        author_name = actor.username if hasattr(actor, "username") else actor.sub
        report = ReportGenerator.generate(
            case=case,
            artifacts=artifacts,
            graph_data=graph_data,
            parsed_observations_count=obs_count,
            request=request,
            version_str=version_str,
            version_number=version_number,
            previous_version_id=previous_version_id,
            author=author_name
        )

        # 7. Persist to repository
        saved_report = self.repository.save(report)

        # 8. Register BOLA resource binding
        if hasattr(self.policy_engine, "register_resource"):
            self.policy_engine.register_resource(saved_report.report_id, case_id, "report")

        # 9. Audit event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value if hasattr(actor.role, "value") else str(actor.role),
            case_id=case_id,
            action="GENERATE_REPORT",
            target_resource=f"report:{saved_report.report_id}",
            decision="ALLOW",
            metadata={
                "version": version_str,
                "sha256": saved_report.sha256,
                "template_type": request.template_type.value
            }
        )

        return saved_report
