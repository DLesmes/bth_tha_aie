from langgraph.graph import StateGraph, END
from .state import AgentState
from .agents import AgentCluster

cluster = AgentCluster()
workflow = StateGraph(AgentState)

# Register all nodes
workflow.add_node("router", cluster.front_router)
workflow.add_node("retriever", cluster.retrieve_secured_context)
workflow.add_node("specialist", cluster.specialist_synthesis)
workflow.add_node("reviewer", cluster.reviewer_verification)

# Set the Entry Point to your Front Router
workflow.set_entry_point("router")

# Define the conditional routing logic directly out of the Router node
def route_after_input(state):
    flag = state.get("evaluation_feedback")
    if flag == "off_topic":
        return "end_immediately"
    elif flag in ["casual_greeting", "casual_goodbye"]:
        return "go_to_specialist"
    else:
        return "go_to_retriever"

workflow.add_conditional_edges(
    "router",
    route_after_input,
    {
        "end_immediately": END,
        "go_to_specialist": "specialist",
        "go_to_retriever": "retriever"
    }
)

# Keep your original execution flow from retriever onwards
workflow.add_edge("retriever", "specialist")
workflow.add_edge("specialist", "reviewer")

# Keep your original self-healing conditional edge loops out of your Reviewer
def route_evaluation_loop(state):
    if state.get("evaluation_feedback") in ["casual_greeting", "casual_goodbye", "off_topic"]:
        return "approved"
        
    if state["is_valid"]:
        print("--> Reviewer Approved Generation Outcome.")
        return "approved"
    elif state["retry_count"] >= 3:
        print("--> System Retry Exhausted. Falling Back Safely.")
        return "halt"
    else:
        print(f"--> Reviewer Flagged Hallucination. Routing back to Specialist. Retry #{state['retry_count']}")
        return "reject"

workflow.add_conditional_edges(
    "reviewer",
    route_evaluation_loop,
    {
        "approved": END,
        "reject": "specialist",
        "halt": END
    }
)

graph = workflow.compile()
