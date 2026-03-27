from langgraph.graph import StateGraph, START, END
from ultralytics import YOLO
import cv2
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from typing import TypedDict, Annotated
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama
import tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import InMemorySaver
import os
import datetime


class ObjectState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


model = YOLO("yolov8n.pt")

llm = ChatOllama(
    model="llama3.2",
    temperature=0.25
)

search = DuckDuckGoSearchRun()


@tool
def detect_objects(image_path: str = "") -> str:
    """
    Detect objects in an image using YOLOv8.

    Args:
        image_path: THE EXACT FILE PATH provided in the user message or system notes. 
                   Do not make up a path; use the one ending in .jpg provided in the chat.
    """
    placeholders = ["<user's image", "path_to_your", "NONE", "None"]
    if any(p in image_path for p in placeholders) or not os.path.exists(image_path):
        return "Error: No valid image file was found on the server. Please ask the user to upload an image."

    results = model(image_path)

    detected_objects = []

    for r in results:
        boxes = r.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            detected_objects.append(label)

    if not detected_objects:
        return "No objects detected."

    return f"Detected objects: {list(set(detected_objects))}"


tools = [search, detect_objects]

llm_with_tools = llm.bind_tools(tools=tools)

checkpointer = InMemorySaver()


def chat_node(state: ObjectState):
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    return {
        'messages': [response]
    }


tools_node = ToolNode(tools=tools)

graph = StateGraph(ObjectState)
graph.add_node('chat_node', chat_node)
graph.add_node('tools', tools_node)

graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node')
graph.add_edge('chat_node', END)

workflow = graph.compile(checkpointer=checkpointer)

prompt = """
You are Aaron, a warm, friendly, and helpful AI assistant!

CORE PERSONALITY:
- Be conversational and concise. 
- Greet the user warmly if they say 'hi' or 'hey'.
- Do not mention your tools or the 'IMAGE_PATH' unless necessary for the task.

TOOL SELECTION LOGIC:
1. CONVERSATION: If the user is just chatting or asking something you know, just reply.
2. IMAGE ANALYSIS (detect_objects): Use ONLY if IMAGE_PATH is NOT 'NONE' AND the user asks about the image. 
3. WEB SEARCH (duckduckgo_search): Use ONLY if the user asks about current events, real-time data (weather, stocks, news), or topics you don't have certain knowledge about.

CRITICAL RULES:
- If IMAGE_PATH is 'NONE', act as if you don't even have a camera. 
- Never try to 'search' for the IMAGE_PATH on the web.
- If the user asks a general question while an image is present, answer the question first; only analyze the image if asked.
"""


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# @app.post("/chat")
# async def chat(
#     message: str = Form(...),
#     image: UploadFile = File(None)
# ):

#     image_path = None

#     if image:

#         contents = await image.read()

#         with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
#             tmp.write(contents)
#             image_path = tmp.name
#         result = workflow.invoke({
#             "messages": [SystemMessage(content=prompt), HumanMessage(content=f"{message}\n\n Image path: {image_path if image_path else 'None'}")],

#         }, config={
#             'configurable': {
#                 "thread_id": "thread_id_1"
#             }
#         })
#     else:
#         result = workflow.invoke({
#             "messages": [SystemMessage(content=prompt), HumanMessage(content=message)],

#         }, config={
#             'configurable': {
#                 "thread_id": "thread_id_1"
#             }
#         })

#         # message = f"""
#         # {message}

#         # Image path: {image_path}

#         # If the question refers to objects in the image,
#         # use the detect_objects tool.
#         # """

#     # result = workflow.invoke({
#     #     "messages": [SystemMessage(content=prompt), HumanMessage(content=f"{message}\n\n Image path: {image_path if image_path else 'None'}")],

#     # }, config={
#     #     'configurable': {
#     #         "thread_id": "thread_id_1"
#     #     }
#     # })

#     response = result["messages"][-1].content

#     return {"response": response}

@app.post("/chat")
async def chat(
    message: str = Form(...),
    image: UploadFile = File(None),
    thread_id: str = Form("default_user")  # Get this from frontend!
):
    image_path = "NONE"

    if image:
        contents = await image.read()
        temp_dir = tempfile.gettempdir()
        image_path = os.path.join(temp_dir, f"upload_{image.filename}")
        with open(image_path, "wb") as f:
            f.write(contents)

    # Use a cleaner format for the LLM to parse
   # Clearly label the metadata so the LLM treats it as context, not user speech
    formatted_message = f"""
    [CONTEXT]
    IMAGE_PATH: {image_path}
  

    [USER MESSAGE]
    {message}
    """

    result = workflow.invoke({
        "messages": [
            SystemMessage(content=prompt),
            HumanMessage(content=formatted_message)
        ]
    }, config={"configurable": {"thread_id": thread_id}})

    return {"response": result["messages"][-1].content}
