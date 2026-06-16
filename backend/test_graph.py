from src.agent_graph import graph

def run_test_simulation(target_role: str, description: str):
    print(f"\n=======================================================")
    print(f"RUNNING SECURITY PROFILE TEST: {description} ({target_role})")
    print(f"=======================================================")
    
    mock_payload = {
        "query": "What specific criteria are listed under the chatbot takehome assignment?",
        "current_user": f"test_{target_role}_user",
        "user_role": target_role,
        "retrieved_docs": [],
        "generated_response": "",
        "retry_count": 0,
        "is_valid": False,
        "evaluation_feedback": ""
    }
    
    output = graph.invoke(mock_payload)
    print(f"\nFinal Execution Result for ({target_role}):")
    print(output["generated_response"])

if __name__ == "__main__":
    run_test_simulation("collaborator", "Expect Total Isolation Block")
    run_test_simulation("admin", "Expect Authorized Elevation Access")
