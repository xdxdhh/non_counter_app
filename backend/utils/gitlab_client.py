import requests
import logging
from typing import Dict, Any
from pydantic import BaseModel
from datetime import datetime
import re 
import os

logger = logging.getLogger(__name__)


class Issue(BaseModel):
    iid: int
    title: str
    description: str
    created_at: datetime
    web_url: str

    def get_file_paths(self) -> list[str]:
        pattern = r'\[.*?\]\((\/uploads\/[^\)]+)\)'
        matches = re.findall(pattern, self.description)
        # strip the /uploads/ from the beginning of the path
        matches = [path.replace('/uploads/', '') for path in matches]
        return matches
 

class GitLabClient:
    """GitLab API client for fetching issues."""
    
    def __init__(self, token: str, project_id: str):
        """
        Initialize GitLab API client.
        Args:
            token: GitLab personal access token or project access token
            project_id: Project ID from Gitlab
        """
        self.api_base = "https://gitlab.com/api/v4"
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.project_id = project_id
    
    def get_issue(self, issue_iid: int) -> Issue:
        """
        Fetch an issue from a GitLab project.
        
        Args:
            project_id: Project ID or path (e.g., "group/project" or numeric ID)
            issue_iid: Issue IID (internal ID within the project, not the global issue ID)
        
        Returns:
            Dictionary containing issue data from GitLab API
        
        Raises:
            requests.HTTPError: If the API request fails
            Exception: For other errors
        """
        
        url = f"{self.api_base}/projects/{self.project_id}/issues/{issue_iid}"
        
        logger.info(f"Fetching issue {issue_iid} from project {self.project_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            issue_data = response.json()
            logger.info(f"Successfully fetched issue: {issue_data.get('title', 'N/A')}")
            return Issue.model_validate(issue_data)
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error occurred while fetching issue: {http_err}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'N/A'}")
            raise
        except Exception as err:
            logger.error(f"An error occurred while fetching issue: {err}")
            raise

    def download_files(self, paths: list[str], destination_folder: str) -> None:
        logger.info(f"Downloading files from {paths} to {destination_folder}")
        os.makedirs(destination_folder, exist_ok=True)
        for file_path in paths:
            url = f"{self.api_base}/projects/{self.project_id}/uploads/{file_path}"
            logger.info(f"Downloading file from {url}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            with open(os.path.join(destination_folder, file_path.split('/')[-1]), 'wb') as f:
                f.write(response.content)
            logger.info(f"Downloaded file {file_path.split('/')[-1]} to {destination_folder}")