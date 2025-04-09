from functools import lru_cache
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
from base import Runtime

from workers import (
    FLOW_WORKERS,
    PlatformAgentWorker,
    DataDescriptionWorker,
    ParsingRulesWorker,
)
from models import (
    FLOW_DATA,
    PlatformData,
    FileData,
    DataDescriptionData,
    ParserDefinitionData,
)

runtimes: dict[int, Runtime] = {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

""" @lru_cache
def get_settings():
    settings = config.Settings()
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    return settings """


class PlatformRequest(BaseModel):
    platform: str


def create_runtime():
    session_id = max(list(runtimes.keys()), default=0) + 1
    runtimes[session_id] = Runtime()
    return session_id


@app.post("/start_session")
def start_session():
    session_id = create_runtime()
    return {"session_id": session_id}


def get_runtime(session_id: int):
    try:
        return runtimes[session_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


@app.post("/new_platform/{session_id}")
async def check_platform(session_id: int, request: PlatformRequest):
    print("backend: Checking platform", request.platform)
    runtime = get_runtime(session_id)
    runtime.set_state(
        PlatformData(platform_name=request.platform, exists=False, parser_names=[])
    )
    await runtime.run(PlatformAgentWorker())

    platform_after = runtime.get_state("platform_data", PlatformData)
    if platform_after.exists:
        return {"exists": True}  # i dont have to send the msg
    else:
        return {"exists": False}


@app.post("/upload_file/{session_id}")
async def upload_file(session_id: int, file: UploadFile = File(...)):
    runtime = get_runtime(session_id)
    try:
        file_location = f"uploaded_files/{file.filename}"
        os.makedirs("uploaded_files", exist_ok=True)
        with open(file_location, "wb") as buffer:
            buffer.write(await file.read())
        runtime.set_state(FileData(filename=file_location))
        return {"filename": file.filename, "message": "File uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_flow_data(data_name: str):
    for t in FLOW_DATA:
        if t.flow_data_name() == data_name:
            return t
    raise HTTPException(status_code=404, detail="Flow data not found")


def get_flow_worker(worker_name: str):
    print("getting correct flow worker")
    for t in FLOW_WORKERS:
        if t.flow_worker_name() == worker_name:
            return t
    raise HTTPException(status_code=404, detail="Flow worker not found")


@app.get("/state/{session_id}/{data_name}")
async def get_state(session_id: int, data_name: str):
    print("Getting state.")
    runtime = get_runtime(session_id)

    flow_data = get_flow_data(data_name)
    state = runtime.get_state(data_name, flow_data)
    print("current state:", state)
    return state.model_dump()


@app.post("/state/{session_id}/{data_name}")
async def set_state(request: Request, session_id: int, data_name: str):
    print("Setting new state from POST.", data_name)
    runtime = get_runtime(session_id)

    flow_data = get_flow_data(data_name)
    data = await request.json()
    print("received data:", data)
    print("after validation:", flow_data.model_validate(data))
    runtime.set_state(flow_data.model_validate(data))


@app.get("/parsing_rules/{session_id}")
async def get_parsing_rules(session_id: int):
    runtime = get_runtime(session_id)
    await runtime.run(ParsingRulesWorker())
    return runtime.get_state(
        "parser_definition_data", ParserDefinitionData
    ).model_dump_json(indent=4)


@app.get("/worker/{session_id}/{worker_name}")
async def call_worker(session_id: int, worker_name: str):
    print("Calling worker", worker_name)
    runtime = get_runtime(session_id)
    flow_worker = get_flow_worker(worker_name)
    await runtime.run(flow_worker())
    return {"message": f"Worker {worker_name} executed successfully."}
