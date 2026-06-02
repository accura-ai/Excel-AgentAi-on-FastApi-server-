import shutil

from tools import transform_excel, list_source_columns
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from typing import Annotated, Optional, TypedDict, Sequence
from langchain_core.messages import BaseMessage, HumanMessage
import pandas as pd
from pandas import DataFrame as df
from pandas import ExcelWriter, ExcelFile, read_excel, read_csv
from langgraph.types import interrupt
import os 
import json
from datetime import datetime

# Getting Local Enviorment Ollama model
# For this we will use qwen3:14b, he is pretty small, operating on around 10GB of VRAM also he was trained to handle structured data like dataframes or JSON structrued data
# For more specification and how to run this locally read README.md file in this repository

# ollama pull qwen3:14b

from langchain_ollama import ChatOllama

model = ChatOllama(model="qwen3:14b")

# AgentState, it help agent remember what he did, what he has to do, also managing Dictionary of tools and their results
class AgentState(TypedDict):
 
    messages: Annotated[list, add_messages]

    user_input: str # Message he received from user
    input_file_path: str # It takes the input file path given in upload file endpoint
    output_file_path: str # It takes the output file path given in upload file endpoint, if user didn't provide it, it will be set to "wynik.xlsx"

    work_sketch: str # Sketch of what he is going to do, for example if he needs to transform excel file, he can write sketch of how he is going to do it, what tools he will use, what steps he will take, this is not a plan, just sketch of what he is going to do, it can be very short and not detailed, for example "I will use transform_excel tool to transform excel file according to specification provided by user"
    plan: Optional[dict] # Plan for our agent, it will help him be more efficient in the future
    current_file: str # Current file he is working on, for example if he has to transform excel file, this variable will be set to name of this file, so if he needs to use transform_excel tool, he can check if current_file is set to name of file he want to transform, if not he can set it and then use tool, if yes, he can just use tool without setting it again
    tools_results: dict # Dictionary of tools and their results, for example if he used transform_excel tool, he will save the result in this dictionary with key "transform_excel"
    result: str # Final result he will return to user, for example if he transformed excel file, he can save the path to transformed file in this variable and return it to user at the end of conversation
    steps: int # Counter of steps model took in tool_agent graph, it help to count if every step was done

# Creating function that will be the Start of our Graph, it will tak input from users and save it to AgentState

def start_agent(state: AgentState) -> AgentState:
  
    user_input = state["messages"][-1].content if state["messages"] else ""

    return {"user_input": user_input, "steps": 0}

# Planning Agent, he's job is to do two main thing, first one is to create sketch of what our agent will do in next graphs, second one is to create dictionery from users input, dictionary will be necessary for our LLM to use tools that we provided

def planning_agent(state: AgentState) -> AgentState:

    user_input = state["user_input"]
    input_file_path = state["input_file_path"]
    output_file_path = state["output_file_path"]

    # Promp to our model so he know what to do, how to create dictionary for tools

    sketch_prompt = """
        You are a JSON specification builder. 
        TASK: Analyze the user message and extract ALL sheets and ALL columns mentioned.
        CRITICAL RULES:
        - Create a separate entry in "sheets" for EVERY sheet the user mentioned
        - Create a separate entry in "columns" for EVERY column the user mentioned in that sheet
        - If user mentions 3 columns -> "columns" list has 3 entries
        - If user mentions 2 sheets -> "sheets" list has 2 entries
        - Return ONLY raw JSON, no thinking, no explanation, no markdown, no backticks
        
        OUTPUT FORMAT:
        {
            "file_path":""" + input_file_path + """ ,
            "output_path": """ + output_file_path + """,
            "header_row": <int, default 0>,
            "sort_by": <str or null if not provided>,
            "sheets": [
                {
                    "sheet_name": <str, default "Sheet1">,
                    "start_row": <int, default 0>,
                    "start_col": <int, default 0>,
                    "columns": [
                        {
                            "target": <str, column name in output>,
                            "source": <str, source column name or "Couldn't find the source column">,
                            "value": <str or null>,
                            "transform": <str or null>
                        }
                    ]
                }
            ]
        }

        
        User message:
    """ + user_input + """ Remember: extract EVERY sheet and EVERY column from the message above. Return ONLY JSON. """

    work_sketch = model.invoke(sketch_prompt)
    raw_text = work_sketch.content

    # Qwen3 sometimes thinks out loud and write some explanation, we need to extract only JSON from his answer
    if "<think>" in raw_text:
        json_part = raw_text.split("</think>")[-1]

    # Clean markdown
    clean_text = raw_text.strip()
    if clean_text.startswith("```") and clean_text.endswith("```"):
        clean_text = clean_text.split("```")[1]
        if clean_text.startswith("json"):
            clean_text = clean_text[4:]
        clean_text = clean_text.rsplit("```",1 )[0]

    work_sketch = json.loads(clean_text.strip())

    # Now we have the work sketch that model will use for tools, now we need to create plan for our agent so in future he can look at it to help him be more efficient

    plan_prompt = """

    You are a task planner. Based on the user message and avaible tools you have, create an execution plan. User Message: """ + user_input + """ 
    Tools you have and their descriptions:""" + tools_description + """ 
    TASK: Devide what or whitch tools need to be used and in what order: 
    
    CRITICAL RULES:
        - Include ONLY tools that are needed for this task
        - Keep the order logical (e.g. first read, then transform, then write)
        - Return ONLY raw JSON, no thinking, no markdown, no backticks

    OUTPUT FORMAT:
                {
                    "steps": [
                        {
                            "step": <int, step number starting from 1>,
                            "tool": <str, tool name>,
                            "description": <str, what this step does>,
                            "status": "pending"
                        }
                    ]
                }

    Remember to return ONLY JSON.
    
    """

    plan = model.invoke(plan_prompt)
    raw_text_of_plan = plan.content

    # Same as with work sketch, we need to extract only JSON from model answer

    if "<think>" in raw_text:
        raw_text = raw_text.split("</think>")[-1]

    raw_text_of_plan = raw_text_of_plan.strip()
    if raw_text_of_plan.startswith("```"):
        raw_text_of_plan = raw_text_of_plan.split("```")[1]
        if raw_text_of_plan.startswith("json"):
            raw_text_of_plan = raw_text_of_plan[4:]
        raw_text_of_plan = raw_text_of_plan.rsplit("```", 1)[0]

    plan = json.loads(raw_text_of_plan.strip())

    return {"work_sketch": work_sketch, "plan": plan}

# At this point we can test our planning_agent withoout need of doing whole graph, we can just create AgentState with message and pass it to planning_agent function

# print(planning_agent({"user_input": "I want to transform my excel file, its caleed Sheet21 it has columns Name and Surname, i want to transform them into new file as NameOfPerson and SurnameOfPerson"}))
# print(planning_agent({"user_input": "Hey, so i need you to name columns that i have in my excel file Arkusz1"}))

# Now we need to create TollNodes for our graph, moment where agent will decide to use certain tools based on plan we created in planning_agent

# Pulling tools from tools.py file so our model can use them

tools_list = [transform_excel, list_source_columns]

# Also we have to provide some kind of "prompt" for our model about tools he has avaible so he can be more efficient in planning and then in doing his tasks
tools_description = """

    Available tools:
    1. transform_excel(spec: dict, file_path: str, output_path: str = "wynik.xlsx") - This tool is used to transform excel file according to specification provided by user into a new file, spec are saved as work_sketch in your AgentState
    2. list_source_columns(file_path: str) - This tool is used to list all columns from excel file, it can be useful when you want to transform excel file but you don't know what columns are in it, you can use this tool to check columns and then use transform_excel tool to transform file according to specification provided by user

"""

# Binding tools to our model:
model_tools = model.bind_tools(tools_list)

# Creating a node that will use tools based on plan created earlier

def tool_user(state: AgentState) -> AgentState:

    plan = state["plan"]
    work_sketch = state["work_sketch"]
    print(f"DEBUG: Plan steps: {len(plan['steps'])}, current step: {state['steps']}")  # Temporary debug print

    if state["steps"] == 0:
        messages = [HumanMessage(content=f"Plan: {plan}\nWork Sketch: {work_sketch}")]
        print("DEBUG: First step, sending plan and work sketch to model")  # Temporary debug print
    else:
        messages = state["messages"]
        print("DEBUG: Subsequent step, sending previous messages to model")  # Temporary debug print

    response = model_tools.invoke(messages)
    return {"messages": [response], "steps": state["steps"] + 1}

#end or loop if we need to end the graph or we need to do another step using tools

def end_or_loop(state: AgentState) -> str: 
    last = state["messages"][-1]
    
    # Jeśli ostatnia wiadomość ma tool_calls — model chce jeszcze użyć narzędzia
    if hasattr(last, "tool_calls") and last.tool_calls:
        print("DEBUG: Tool calls detected, looping back")
        return "loop"
    
    print("DEBUG: No tool calls, ending graph")
    return "done"
    
    
# Define an node that will collect results from tools he used previousle so our user can clearly see what was done in the agent loop

def results(state: AgentState) -> AgentState:
    print("DEBUG messages:", state["messages"])  # tymczasowo
    results = {}
    for msg in state["messages"]:
        if hasattr(msg, "name") and msg.type == "tool": # REMEMBER: hasattr is used to check if object has attribute, in this case we check if message has attribute "name", because when model use tool, the response will be a message with attribute "name" equal to name of tool and attribute "content" equal to result of tool
            results[msg.name] = msg.content
    return {"tools_results": results}



# Define END node
def end_agent(state: AgentState) -> AgentState:
    print("Results:")
    # Print the tool results
    for tool_name, result in state["tools_results"].items():
        print(f"{tool_name}: {result}")
    # Print the final result
    last_msg = state["messages"][-1]
    print(f"Final Result: {last_msg.content}")
    return {}

# Define our graph 

excelGraph = StateGraph(AgentState)
tool_node = ToolNode(tools_list)

excelGraph.add_node("start_agent", start_agent)
excelGraph.add_node("planning", planning_agent)
excelGraph.add_node("tool_user", tool_user)
excelGraph.add_node("tools", tool_node)  
excelGraph.add_node("results", results)
excelGraph.add_node("end_agent", end_agent)

excelGraph.add_edge(START, "start_agent")
excelGraph.add_edge("start_agent", "planning")
excelGraph.add_edge("planning", "tool_user")
excelGraph.add_conditional_edges("tool_user", end_or_loop, {"done": "results", "loop": "tools"})
excelGraph.add_edge("tools", "tool_user")  # po wykonaniu narzędzia wróć do tool_user
excelGraph.add_edge("results", "end_agent")
excelGraph.add_edge("end_agent", END)

#question = input("What you want to do with your excel file? (Press Enter to start the agent): ")

#graph = excelGraph.compile()
#graph.invoke({"messages": [HumanMessage(content=question)], "steps": 0})

# Test prompt from user: Please create a new excel file with name Arkusz67.xlsx, i will need to have there ID, Dział and Typ Dokumentu in this exact order taken from "Arkusz1.xlsx" sorted by ID


# TODO: After end of first command open chat with user so he can please for some adjustments if he want to, add RAG with excel code to work on excel files
# TODO: Connect it to Azure PostreSQL and deploy it on FASTAPI 

# Now were adding to all of this FastApi so we can deploy it and use it at the server not only in terminal

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Basic FastAPI setup

app = FastAPI(
    title="Excel Ai Agent",
    description="This API serves as your private assisatnce to manage your excel files, everything runs locally so all of ou private data is safe and secure",
    version="1.0"
)

UPLOAD_DIR = "processed_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Zezwala na otwieranie strony bezpośrednio z dysku/pliku
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str
    input_file_path: Optional[str] = None
    output_file_path: Optional[str] = None

# Creating endpoint for file upload
@app.post("/upload-excel", summary="Upload Excel File", description="Upload an Excel file to be processed by the agent.")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an Excel file.")
    
    try:
        safe_filename = f"user_{file.filename}"
        input_path = os.path.join(UPLOAD_DIR, safe_filename)
        output_filename = f"ready_{safe_filename}"
        output_path = os.path.join(UPLOAD_DIR, output_filename)

        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"input_file_path": input_path, "output_file_path": output_path}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during file uploading: {str(e)}")
    
# Creating endpoint for chat with our agent

@app.post("/chat", summary="Chat with Excel Agent", description="Send a message to the Excel Agent and get a response based on your request.")
async def chat_endpoint(payload: ChatMessage):
    
    question = payload.message
    input_file_path = payload.input_file_path
    output_file_path = payload.output_file_path
    try:
        graph = excelGraph.compile()
        result_state = graph.invoke({"messages": [HumanMessage(content=question)], "steps": 0, "input_file_path": input_file_path, "output_file_path": output_file_path})
        
        # Extracting the final result from the state
        final_result = result_state.get("messages", [])[-1].content if result_state.get("messages") else "No response from agent."
        
        return {"response": final_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
# Endpoint to download the processed file
@app.get("/download/{output_file_name}", summary="Download Processed Excel File", description="Download the processed Excel file after the agent has completed its task.")
async def download_file(output_file_name: str):
    file_path = os.path.join(UPLOAD_DIR, output_file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=output_file_name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")




