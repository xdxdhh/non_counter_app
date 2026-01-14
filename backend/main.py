from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
import logging
import requests
import json

from base import Runtime
from workers import FLOW_WORKERS, BrainClient
from models import (
    FLOW_DATA,
    FileData,
    FileFormat,
    PlatformData,
    UserInfoData,
    MetricsDimensionsData,
    DataDescriptionData,
    ReportTypeData,
)
from utils.gitlab_client import GitLabClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

runtimes: dict[int, Runtime] = {}  # Dictionary to store all runtimes

app = FastAPI()

app.add_middleware(  # Middleware to handle CORS
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


@app.get("/worker/{session_id}/{worker_name}/stream")
async def call_worker_stream(session_id: int, worker_name: str):
    """
    Execute the specified FlowWorker and stream progress updates.
    Currently only supports parsing_rules_worker.
    """
    logger.info(f"Calling worker {worker_name} with streaming")
    runtime = get_runtime(session_id)
    flow_worker = get_flow_worker(worker_name)
    
    async def generate():
        try:
            worker = flow_worker()
            
            # Only parsing_rules_worker supports streaming
            if worker_name == "parsing_rules_worker" and hasattr(worker, 'run_with_progress'):
                # Get required inputs
                args = []
                for input_type in worker.input_data:
                    args.append({t.__class__: t for t in runtime.state.values()}[input_type])
                
                # Stream progress - this completes the work and updates the context
                async for progress in worker.run_with_progress(*args):
                    try:
                        yield f"data: {json.dumps(progress)}\n\n"
                    except Exception as e:
                        logger.exception(f"Error yielding progress: {e}")
                        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
                        break
                
                # After streaming completes, save the results from context to state
                try:
                    if worker.context.parser_definition:
                        runtime.set_state(worker.context.parser_definition)
                    if worker.context.parsed_data:
                        runtime.set_state(worker.context.parsed_data)
                except Exception as e:
                    logger.exception(f"Error saving results to state: {e}")
                    yield f"data: {json.dumps({'error': f'Error saving results: {str(e)}', 'done': True})}\n\n"
                    
            else:
                # Fallback for other workers - run normally and send completion
                await runtime.run(worker)
                yield f"data: {json.dumps({'done': True, 'message': 'Complete'})}\n\n"
                
        except Exception as e:
            logger.exception(f"Error in generate(): {e}")
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
    response = StreamingResponse(generate(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # Disable buffering for nginx
    return response


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
    platform_data = runtime.get_state("platform_data", PlatformData)
    user_info_data = runtime.get_state("user_info_data", UserInfoData)
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
    gitlab_client = GitLabClient()
    gitlab_client.add_issue_comment(
        user_info_data.gitlab_issue, platform_data.to_gitlab_comment()
    )


@app.post("/submit_metrics_dimensions/{session_id}")
async def process_metrics_dimensions(session_id: int):
    runtime = get_runtime(session_id)
    metrics_dimensions_data = runtime.get_state(
        "metrics_dimensions_data", MetricsDimensionsData
    )
    user_info_data = runtime.get_state("user_info_data", UserInfoData)
    brain_client = BrainClient()
    metrics_dimensions_data = brain_client.process_metrics_dimensions(
        metrics_dimensions_data
    )
    runtime.set_state(metrics_dimensions_data)
    gitlab_client = GitLabClient()
    gitlab_client.add_issue_comment(
        user_info_data.gitlab_issue, metrics_dimensions_data.to_gitlab_comment()
    )
    platform_data = runtime.get_state("platform_data", PlatformData)
    data_description_data = runtime.get_state(
        "data_description_data", DataDescriptionData
    )
    report_type_data = ReportTypeData.from_flow_data(
        metrics_dimensions_data, platform_data, data_description_data
    )

    runtime.set_state(report_type_data)
    report_type_data = brain_client.create_report_type(report_type_data)
    runtime.set_state(report_type_data)
    gitlab_client.add_issue_comment(
        user_info_data.gitlab_issue, report_type_data.to_gitlab_comment()
    )
    file_data = runtime.get_state("file_data", FileData)
    brain_client.upload_input_sample(
        file_data, platform_data, data_description_data, user_info_data
    )
