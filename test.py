import ollama

MODEL = "qwen2.5:7b"


# 1. The tool: a normal Python function.
#    The docstring is important - the model reads it to understand the tool.
def get_department(category: str) -> str:
    """Return the city department responsible for a type of problem.

    Args:
        category: The problem type, e.g. pothole, streetlight, garbage, graffiti

    Returns:
        The name of the responsible department
    """
    departments = {
        "pothole": "Road Maintenance",
        "streetlight": "Street Lighting",
        "garbage": "Waste Management",
        "graffiti": "City Cleaning",
    }
    return departments.get(category.lower(), "Unknown department")


# A dictionary so we can find the right function by its name
available_tools = {"get_department": get_department}

# 2. The citizen's message
# messages = [
#  {"role": "user",
#   "content": "There is a huge pothole on Main Street. Which department should fix it?"}
# ]

messages = [{"role": "user", "content": "My neighbors dog barks all night"}]

# 3. First call: the model decides whether it needs a tool
response = ollama.chat(model=MODEL, messages=messages, tools=[get_department])
messages.append(response.message)

# 4. If the model asked for a tool, run it and send the result back
if response.message.tool_calls:
    for call in response.message.tool_calls:
        name = call.function.name
        args = call.function.arguments
        print(f"Model wants to call: {name}({args})")

        result = available_tools[name](**args)
        print(f"Tool returned: {result}")

        messages.append({"role": "tool", "content": result, "tool_name": name})

    # 5. Second call: the model writes its final answer using the tool result
    final = ollama.chat(model=MODEL, messages=messages)
    print("\nFinal answer:", final.message.content)
else:
    print("Model answered without a tool:", response.message.content)
