"""Human-in-the-Loop (HITL) API routes."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.agent_service import approve_refund, resume_after_hitl

router = APIRouter()


class HITLApproveRequest(BaseModel):
    thread_id: str
    approved: bool = Field(..., description="True to approve, False to reject")
    approved_by: str = Field("human_agent", description="Identifier of the approving agent")


class HITLResumeRequest(BaseModel):
    thread_id: str


@router.post("/approve")
async def hitl_approve(request: HITLApproveRequest):
    """
    Approve or reject a pending action (e.g. refund).
    Call /resume afterwards to continue the graph.
    """
    return approve_refund(request.thread_id, request.approved, request.approved_by)


@router.post("/resume")
async def hitl_resume(request: HITLResumeRequest):
    """Resume the agent graph after HITL approval/rejection."""
    return resume_after_hitl(request.thread_id)
