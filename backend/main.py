from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

from base import Runtime
from workers import FLOW_WORKERS
from models import FLOW_DATA, FileData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

runtimes: dict[int, Runtime] = {} # Dictionary to store all runtimes

app = FastAPI()

app.add_middleware( # Middleware to handle CORS
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_runtime():
    """
    Helper function to create a new runtime instance.
    This function is used to create a new session and store it in the runtimes dictionary.
    It computes the next session ID by finding the maximum key in the runtimes dictionary and adding 1.
    """
    session_id = max(list(runtimes.keys()), default=0) + 1
    runtimes[session_id] = Runtime()
    return session_id

@app.post("/start_session")
def start_session():
    """
    Start a new session and return the session ID.
    This function creates a new Runtime instance and stores it in the runtimes dictionary.
    The session ID is the key in the dictionary.
    The session ID is incremented for each new session.
    """
    session_id = create_runtime()
    return {"session_id": session_id}


def get_runtime(session_id: int) -> Runtime:
    """
    Get runtime for given session_id.
    """
    try:
        return runtimes[session_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

@app.post("/upload_file/{session_id}")
async def upload_file(session_id: int, file: UploadFile = File(...)) -> dict:
    """
    Upload a file, store it in the server and update current state.
    The file is stored in the 'uploaded_files' directory.
    The session ID is used to get the correct runtime instance.
    The file name is used to create a new FileData instance, which is stored in the runtime state.
    """
    runtime = get_runtime(session_id)
    try:
        file_location = f"uploaded_files/{file.filename}"
        os.makedirs("uploaded_files", exist_ok=True) # create directory if it doesn't exist
        with open(file_location, "wb") as buffer:
            buffer.write(await file.read())
        runtime.set_state(FileData(filename=file_location))
        return {"filename": file.filename, "message": "File uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_flow_data(data_name: str):
    """
    Helper function to get flow data by name.
    """
    for t in FLOW_DATA:
        if t.flow_data_name() == data_name:
            return t
    raise HTTPException(status_code=404, detail="Flow data not found")

def get_flow_worker(worker_name: str):
    """
    Helper function to get flow worker by name.
    """
    for t in FLOW_WORKERS:
        if t.flow_worker_name() == worker_name:
            return t
    raise HTTPException(status_code=404, detail="Flow worker not found")

@app.get("/state/{session_id}/{data_name}")
async def get_state(session_id: int, data_name: str) -> dict:
    """
    Get the current state of the specified FlowData.
    """
    logger.info(f"Getting state for {data_name}")
    runtime = get_runtime(session_id)
    flow_data = get_flow_data(data_name)
    state = runtime.get_state(data_name, flow_data)
    logger.info(f"State: {state}")
    return state.model_dump()


@app.post("/state/{session_id}/{data_name}")
async def set_state(request: Request, session_id: int, data_name: str):
    """
    Set the state of the specified FlowData.
    The state is set using the data provided in the request body.
    """
    logger.info(f"Setting new state for {data_name}")
    runtime = get_runtime(session_id)
    flow_data = get_flow_data(data_name)
    data = await request.json()
    runtime.set_state(flow_data.model_validate(data))
    logger.info(f"State set: {data_name}")


@app.get("/worker/{session_id}/{worker_name}")
async def call_worker(session_id: int, worker_name: str):
    """
    Execute the specified FlowWorker.
    After execution, inform the user about the success of the operation.
    """
    logger.info(f"Calling worker {worker_name}")
    runtime = get_runtime(session_id)
    flow_worker = get_flow_worker(worker_name)
    await runtime.run(flow_worker())
    return {"message": f"Worker {worker_name} executed successfully."}
