from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import requests

from base import Runtime
from workers import FLOW_WORKERS, BrainClient
from models import FLOW_DATA, FileData, FileFormat, PlatformData, UserInfoData, MetricsDimensionsData, DataDescriptionData
from utils.gitlab_client import GitLabClient


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
        runtime.set_state(FileData(path=file_location, format=FileFormat.from_file_extension(file.filename)))
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

@app.get("/metrics")
async def get_brain_metrics():
    brain_client = BrainClient()
    metrics = brain_client.get_metrics()
    return metrics

@app.get("/dimensions")
async def get_brain_dimensions():
    brain_client = BrainClient()
    dimensions = brain_client.get_dimensions()
    return dimensions

@app.get("/submit_platform/{session_id}")
async def submit_platform(session_id: int):
    runtime = get_runtime(session_id)
    platform_data = runtime.get_state('platform_data', PlatformData)
    user_info_data = runtime.get_state('user_info_data', UserInfoData)
    brain_client = BrainClient()
    # Create platform in Brain if needed and store updated state (exists/id)
    try:
        platform_data = brain_client.get_or_create_platform(platform_data)
    except requests.HTTPError as e:
        # Extract meaningful error detail from the Brain API response
        detail = {"error": str(e)}
        if e.response is not None:
            try:
                detail = e.response.json()
            except ValueError:
                detail = {"error": e.response.text or str(e)}
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    runtime.set_state(platform_data)
    gitlab_client = GitLabClient(
            token=os.environ.get("GITLAB_API_TOKEN"),
            project_id=os.environ.get("GITLAB_PROJECT_ID")
        )
    gitlab_client.add_issue_comment(user_info_data.gitlab_issue, platform_data.to_gitlab_comment())

@app.post("/submit_metrics_dimensions/{session_id}")
async def process_metrics_dimensions(session_id: int):
    runtime = get_runtime(session_id)
    metrics_dimensions_data = runtime.get_state('metrics_dimensions_data', MetricsDimensionsData)
    user_info_data = runtime.get_state('user_info_data', UserInfoData)
    brain_client = BrainClient()
    metrics_dimensions_data = brain_client.process_metrics_dimensions(metrics_dimensions_data)
    runtime.set_state(metrics_dimensions_data)
    gitlab_client = GitLabClient(
            token=os.environ.get("GITLAB_API_TOKEN"),
            project_id=os.environ.get("GITLAB_PROJECT_ID")
        )
    gitlab_client.add_issue_comment(user_info_data.gitlab_issue,metrics_dimensions_data.to_gitlab_comment())
    platform_data = runtime.get_state('platform_data', PlatformData)
    data_description_data = runtime.get_state('data_description_data', DataDescriptionData)
    brain_client.create_report_type(metrics_dimensions_data, platform_data, data_description_data)
