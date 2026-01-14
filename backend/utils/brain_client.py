import requests
import logging
import typing
from models import (
    BrainMetric,
    BrainDimension,
    PlatformData,
    BrainPlatform,
    MetricsDimensionsData,
    ReportTypeData,
    FileData,
    DataDescriptionData,
    UserInfoData,
    BrainParserDefinition,
    FileFormat,
)
from utils.gitlab_client import GitLabClient
from dotenv import load_dotenv
import os


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrainClient:
    def __init__(self):
        self.token = os.environ.get("BRAIN_TOKEN")
        brain_url = os.environ.get("BRAIN_URL")
        self.base_url = f"{brain_url}/knowledgebase"
        self.headers = {"Authorization": f"Token {self.token}"}

    def get_metrics(self) -> typing.List[BrainMetric]:
        url = f"{self.base_url}/metrics/"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return [BrainMetric.model_validate(m) for m in response.json()]

    def get_dimensions(self) -> typing.List[BrainDimension]:
        url = f"{self.base_url}/dimensions/"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return [BrainDimension.model_validate(d) for d in response.json()]

    def get_platforms(self) -> typing.List[BrainPlatform]:
        url = f"{self.base_url}/platforms/"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return [BrainPlatform.model_validate(p) for p in response.json()]

    def get_or_create_platform(self, platform_data: PlatformData) -> PlatformData:
        url = f"{self.base_url}/platforms/"
        if platform_data.exists:
            # Fetch the platform from Brain by pk (detail endpoint: /platforms/{id}/)
            if not platform_data.pk:
                raise ValueError(
                    "platform_data.exists=True but platform_data.pk is missing/0"
                )
            detail_url = f"{url}{platform_data.pk}/"
            logger.info(
                "Fetching existing platform from Brain: pk=%s", platform_data.pk
            )
            response = requests.get(detail_url, headers=self.headers, timeout=30)
            if not response.ok:
                logger.error(
                    "Brain %s %s failed: %s",
                    response.request.method,
                    response.url,
                    response.text,
                )
            response.raise_for_status()
            existing = BrainPlatform.model_validate(response.json())
            return PlatformData(
                name=existing.name,
                short_name=existing.short_name,
                provider=existing.provider or "",
                url=existing.url or "",
                exists=True,
                pk=existing.pk,
            )

        payload = {
            "short_name": platform_data.short_name,
            "name": platform_data.name,
            "provider": platform_data.provider,
            "url": platform_data.url,
        }
        logger.info(
            "Creating platform in Brain: short_name=%s name=%s",
            platform_data.short_name,
            platform_data.name,
        )
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        if not response.ok:
            logger.error(
                "Brain %s %s failed: %s",
                response.request.method,
                response.url,
                response.text,
            )
        response.raise_for_status()
        created = BrainPlatform.model_validate(response.json())
        return PlatformData(
            name=created.name,
            short_name=created.short_name,
            provider=created.provider or "",
            url=created.url or "",
            exists=True,
            pk=created.pk,
        )

    def create_metric(self, metric_name: str) -> BrainMetric:
        url = f"{self.base_url}/metrics/"
        payload = {
            "short_name": metric_name,
            "aliases": [],
        }
        logger.info(f"Creating metric {metric_name} in Brain, payload: {payload}")
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        created = BrainMetric.model_validate(response.json())
        return created

    def create_dimension(self, dimension_name: str) -> BrainDimension:
        url = f"{self.base_url}/dimensions/"
        payload = {
            "short_name": dimension_name,
            "aliases": [],
        }
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        created = BrainDimension.model_validate(response.json())
        return created

    def process_metrics_dimensions(
        self, metrics_dimensions_data: MetricsDimensionsData
    ) -> MetricsDimensionsData:
        metrics = metrics_dimensions_data.metrics
        dimensions = metrics_dimensions_data.dimensions

        for metric in metrics:
            if metric.brain_metric is not None:
                # If id is 0, it means we need to create a new metric with the provided short_name
                if metric.brain_metric.id == 0:
                    metric.brain_metric = self.create_metric(
                        metric.brain_metric.short_name
                    )
                # If id > 0, it's an existing metric - use it as is
                # (The metric should already exist in Brain)

        for dimension in dimensions:
            if dimension.brain_dimension is not None:
                # Same logic for dimensions
                if dimension.brain_dimension.id == 0:
                    dimension.brain_dimension = self.create_dimension(
                        dimension.brain_dimension.short_name
                    )
                # If id > 0, it's an existing dimension - use it as is

        return metrics_dimensions_data

    def create_report_type(self, report_type: ReportTypeData):
        logger.info(f"Creating report type: {report_type}")
        url = f"{self.base_url}/report_types/"
        response = requests.post(
            url,
            headers=self.headers,
            json=report_type.model_dump(mode="json"),
            timeout=30,
        )
        if not response.ok:
            logger.error(
                "Brain %s %s failed: %s",
                response.request.method,
                response.url,
                response.text,
            )
        response.raise_for_status()
        report_type = ReportTypeData.model_validate(response.json())
        return report_type

    def upload_input_sample(
        self,
        file_data: FileData,
        platform_data: PlatformData,
        data_description_data: DataDescriptionData,
        user_info_data: UserInfoData,
    ):
        url = f"{self.base_url}/samples/"
        gitlab_client = GitLabClient()

        mime_types = {
            FileFormat.CSV: "text/csv",
            FileFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            FileFormat.XLS: "application/vnd.ms-excel",
        }
        mime_type = mime_types[file_data.format]

        with open(file_data.path, "rb") as file:
            response = requests.post(
                url,
                headers=self.headers,
                data={
                    "name": user_info_data.source,
                    "platform": platform_data.pk,
                    "month_start": data_description_data.begin_month_year,
                    "month_end": data_description_data.end_month_year,
                },
                files={"file": (file_data.file_name, file, mime_type)},
            )
        response.raise_for_status()
        sample_id = response.json()["id"]
        comment = ""
        comment += "## Input Sample\n"
        comment += f"Uploaded input sample for {file_data.file_name}:\n {self.base_url}/admin/nibbler/inputsample/{sample_id}/\n"
        comment += f"Platform: {platform_data.name}\n"
        comment += f"Month start: {data_description_data.begin_month_year}\n"
        comment += f"Month end: {data_description_data.end_month_year}\n"
        gitlab_client.add_issue_comment(user_info_data.gitlab_issue, comment)

    def create_or_update_parser_definition(
        self,
        generated_rules: dict,
        report_type_id: int,
        issue_id: int,
        parser_id: int | None = None,
    ):
        logger.info(f"Creating or updating parser definition: {generated_rules}")
        # read report type from file:
        url = f"{self.base_url}/parsers/"
        kind = "non_counter.generic"
        version = 1
        parser_name = generated_rules.get("parser_name", "default_parser")
        report_type = report_type_id
        areas = generated_rules.get("areas", [])
        metrics_to_skip = generated_rules.get("metrics_to_skip", [])
        titles_to_skip = generated_rules.get("titles_to_skip", [])
        dimensions_to_skip = generated_rules.get("dimensions_to_skip", {})
        dimensions_validators = generated_rules.get("dimensions_validators", {})
        heuristics = generated_rules.get("heuristics", {})

        parser_def = BrainParserDefinition(
            kind=kind,
            version=version,
            parser_name=parser_name,
            report_type=report_type,
            areas=areas,
            metrics_to_skip=metrics_to_skip,
            titles_to_skip=titles_to_skip,
            dimensions_to_skip=dimensions_to_skip,
            dimensions_validators=dimensions_validators,
            heuristics=heuristics,
            possible_row_offsets=[0],
            lowest_nibbler_version="12.0.0",  # TODO get dynamically from pyproject
            highest_nibbler_version="12.0.0",
        )
        # if we have parser ID we want to PUT
        if parser_id:
            response = requests.put(
                f"{url}{parser_id}/",
                headers=self.headers,
                json=parser_def.model_dump(mode="json"),
                timeout=30,
            )
        else:
            response = requests.post(
                url,
                headers=self.headers,
                json=parser_def.model_dump(mode="json"),
                timeout=30,
            )
            gitlab_client = GitLabClient()
            pk = response.json()["pk"]
            gitlab_client.add_issue_comment(
                issue_id,
                f"Parser definition created: {self.base_url}/admin/knowledgebase/parserdefinition/{pk}/",
            )
            return pk
        logger.info(f"Parser definition created or updated: {response.json()}")
        response.raise_for_status()
        parser_id = response.json()["pk"]
        return parser_id
