from __future__ import annotations
from typing import TypedDict, NotRequired
from langgraph.graph import StateGraph, START, END
from email_validator import is_valid_email
from email_service import send_image_email
from delivery_logger import write_delivery_log


class DeliveryState(TypedDict):
    recipient: str
    subject: str
    message: str
    attachment_bytes: bytes
    attachment_name: str
    original_kb: float
    compressed_kb: float
    selected_quality: int
    similarity: float
    max_attempts: int
    attempts: int
    sender: NotRequired[str]
    app_password: NotRequired[str]
    valid_input: NotRequired[bool]
    success: NotRequired[bool]
    status: NotRequired[str]
    result_message: NotRequired[str]


def validate_node(state: DeliveryState):
    valid = is_valid_email(state["recipient"]) and bool(state["attachment_bytes"])
    return {
        "valid_input": valid,
        "success": False,
        "status": "ready" if valid else "validation_error",
        "result_message": "Input validated." if valid else "Invalid recipient email or missing attachment.",
    }


def send_node(state: DeliveryState):
    attempt = state["attempts"] + 1
    result = send_image_email(
        recipient=state["recipient"],
        subject=state["subject"],
        message=state["message"],
        attachment_bytes=state["attachment_bytes"],
        attachment_name=state["attachment_name"],
        sender=state.get("sender"),
        app_password=state.get("app_password"),
    )
    return {
        "attempts": attempt,
        "success": result["success"],
        "status": result["status"],
        "result_message": result["message"],
    }


def log_node(state: DeliveryState):
    write_delivery_log({
        "recipient": state["recipient"],
        "original_kb": round(state["original_kb"], 3),
        "compressed_kb": round(state["compressed_kb"], 3),
        "selected_quality": state["selected_quality"],
        "similarity": round(state["similarity"], 5),
        "attempts": state["attempts"],
        "status": state.get("status", "unknown"),
        "message": state.get("result_message", ""),
    })
    return {}


def after_validation(state: DeliveryState):
    return "send" if state.get("valid_input") else "log"


def after_send(state: DeliveryState):
    if state.get("success"):
        return "log"
    if state["attempts"] < state["max_attempts"]:
        return "send"
    return "log"


def build_delivery_agent():
    graph = StateGraph(DeliveryState)
    graph.add_node("validate", validate_node)
    graph.add_node("send", send_node)
    graph.add_node("log", log_node)
    graph.add_edge(START, "validate")
    graph.add_conditional_edges("validate", after_validation, {"send": "send", "log": "log"})
    graph.add_conditional_edges("send", after_send, {"send": "send", "log": "log"})
    graph.add_edge("log", END)
    return graph.compile()


DELIVERY_AGENT = build_delivery_agent()


def deliver_optimized_image(**kwargs) -> DeliveryState:
    state: DeliveryState = {
        "recipient": kwargs["recipient"],
        "subject": kwargs.get("subject", "Optimized Image"),
        "message": kwargs.get("message", "Please find the optimized image attached."),
        "attachment_bytes": kwargs["attachment_bytes"],
        "attachment_name": kwargs.get("attachment_name", "optimized_image.jpg"),
        "original_kb": kwargs["original_kb"],
        "compressed_kb": kwargs["compressed_kb"],
        "selected_quality": kwargs["selected_quality"],
        "similarity": kwargs["similarity"],
        "max_attempts": kwargs.get("max_attempts", 2),
        "attempts": 0,
        "sender": kwargs.get("sender"),
        "app_password": kwargs.get("app_password"),
    }
    return DELIVERY_AGENT.invoke(state)
