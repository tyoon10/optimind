import asyncio
from src.graph.builder import graph
from langchain_core.messages import HumanMessage
from src.config import config

async def run_test():
    print(f"Environment: {config.ENV}")
    print("--- Testing OptiMind Graph with Expanded Team ---")
    
    # Test 1: Scheduler (Coach Persona)
    print("\nTest 1: Scheduler (Coach check)")
    # Asking for a meeting at 6 AM (conflict with Deep Work)
    inputs = {
        "messages": [HumanMessage(content="Schedule a call with John at 6 AM.")],
        "user_id": "test_user", "user_profile": {}
    }
    async for output in graph.astream(inputs):
        for key, value in output.items():
            print(f"Node: {key}")
            if "messages" in value:
                print(f"Response: {value['messages'][-1].content}")

    # Test 2: Nutritionist (Brand rules)
    print("\nTest 2: Nutritionist (Brand check)")
    inputs = {
        "messages": [HumanMessage(content="I need eggs. Any brand?")],
        "user_id": "test_user", "user_profile": {}
    }
    async for output in graph.astream(inputs):
        for key, value in output.items():
            print(f"Node: {key}")
            if "messages" in value:
                print(f"Response: {value['messages'][-1].content}")

    # Test 3: Medical (Scientific explanation)
    print("\nTest 3: Medical (Science check)")
    inputs = {
        "messages": [HumanMessage(content="Why does UV damage skin?")],
        "user_id": "test_user", "user_profile": {}
    }
    async for output in graph.astream(inputs):
        for key, value in output.items():
            print(f"Node: {key}")
            if "messages" in value:
                print(f"Response: {value['messages'][-1].content}")

    # Test 4: Product Manager (Structure check)
    print("\nTest 4: PM (Output structure check)")
    inputs = {
        "messages": [HumanMessage(content="Let's build a new feature for the app.")],
        "user_id": "test_user", "user_profile": {}
    }
    async for output in graph.astream(inputs):
        for key, value in output.items():
            print(f"Node: {key}")
            if "messages" in value:
                print(f"Response: {value['messages'][-1].content}")

if __name__ == "__main__":
    asyncio.run(run_test())
