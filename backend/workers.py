from base import FlowWorker
import requests
from agents import Runner, Agent, function_tool, RunContextWrapper, ModelSettings
import typing
from prompts import (
    get_data_description_prompt,
    get_parsing_rules_prompt,
    get_translation_prompt,
    get_gitlab_prompt,
)
from models import (
    PlatformData,
    DataDescriptionData,
    FileData,
    FileFormat,
    ParserDefinitionData,
    ParsedData,
    TranslationData,
    MetricsDimensionsData,
    UserInfoData,
    BrainMetric,
    BrainDimension,
    BrainPlatform,
    ReportTypeData,
    BrainParserDefinition,
)
from pydantic import BaseModel
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import json
from celus_nibbler.definitions import Definition
from celus_nibbler.parsers.dynamic import gen_parser
from celus_nibbler import eat
import pandas as pd
import logging
from utils.gitlab_client import GitLabClient, Issue

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrainClient:
    def __init__(self):
        self.token = os.environ.get("BRAIN_TOKEN")
        self.base_url = "https://staging.brain.celus.net/knowledgebase"
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
        gitlab_client = GitLabClient(
            token=os.environ.get("GITLAB_API_TOKEN"),
            project_id=os.environ.get("GITLAB_PROJECT_ID"),
        )

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
        comment += f"Uploaded input sample for {file_data.file_name}:\n https://staging.brain.celus.net/admin/nibbler/inputsample/{sample_id}/\n"
        comment += f"Platform: {platform_data.name}\n"
        comment += f"Month start: {data_description_data.begin_month_year.strftime('%Y-%m-%d')}\n"
        comment += (
            f"Month end: {data_description_data.end_month_year.strftime('%Y-%m-%d')}\n"
        )
        gitlab_client.add_issue_comment(user_info_data.gitlab_issue, comment)

    def create_or_update_parser_definition(self, generated_rules: dict, report_type_id: int, parser_id: int | None = None):
        logger.info(f"Creating or updating parser definition: {generated_rules}")
        # read report type from file:
        url = f"{self.base_url}/parsers/"
        kind = "non_counter.generic"
        version = 1
        parser_name = "default_parser"
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
            lowest_nibbler_version="12.1.1",
            highest_nibbler_version="12.1.1",
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
        logger.info(f"Parser definition created or updated: {response.json()}")
        response.raise_for_status()
        parser_id = response.json()["pk"]
        return parser_id


class DataDescriptionWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Data Description Agent",
            handoff_description="Specialist agent for describing data.",
            instructions=get_data_description_prompt(),
            model="gpt-4o",
            output_type=DataDescriptionData,
            tools=[self.fetch_all_metrics, self.fetch_all_dimensions],
        )

    @staticmethod
    def flow_worker_name():
        return "data_description_worker"

    @function_tool
    async def fetch_all_metrics() -> list[BrainMetric]:
        """Fetch all available metrics from Brain API."""
        url = "https://staging.brain.celus.net/knowledgebase/metrics/"
        headers = {"Authorization": f"Token {os.environ.get('BRAIN_TOKEN')}"}
        logger.info("Fetching all metrics")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return [BrainMetric.model_validate(m) for m in response.json()]
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

    @function_tool
    async def fetch_all_dimensions() -> list[BrainDimension]:
        """Fetch all available dimensions from Brain API."""
        url = "https://staging.brain.celus.net/knowledgebase/dimensions/"
        headers = {"Authorization": f"Token {os.environ.get('BRAIN_TOKEN')}"}
        logger.info("Fetching all dimensions")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return [BrainDimension.model_validate(d) for d in response.json()]
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

    async def run(
        self, file: FileData, user_info: UserInfoData
    ) -> set[DataDescriptionData]:
        """
        Generate data description based on the uploaded file and optional user comment.

        The user comment (if provided) is prepended to the file contents so the agent
        can take it into account when describing the data.
        """
        logger.info("Data Description worker: using file %s", file.file_name)
        # Base content from the prepared file (potentially multiple sheets)
        content = file.to_llm_format()

        # If user provided a comment, prepend it to the content sent to the agent
        if user_info.user_comment:
            content = (
                "User comment (additional context to consider):\n"
                f"{user_info.user_comment}\n"
                "\n"
                "------------------------------\n"
                "Data file content to analyze:\n\n"
                f"{content}"
            )

        result = await Runner.run(self.agent, content)
        logger.info("Data Description Agent result:")
        logger.info(result.final_output)
        return {result.final_output}


class TranslationWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Translation Agent",
            handoff_description="Agent for metric and dimension translations.",
            instructions=get_translation_prompt(),
            model="gpt-4o-mini",
            output_type=TranslationData,
        )

    @staticmethod
    def flow_worker_name():
        return "translation_worker"

    async def run(self, data_description: DataDescriptionData) -> set[TranslationData]:
        metrics = data_description.metrics
        dimensions = data_description.dimensions
        logger.info("Translation worker: metrics: %s", metrics)
        logger.info("Translation worker: dimensions: %s", dimensions)
        input = f"""Metrics: {metrics},Dimensions: {dimensions}"""
        result = await Runner.run(self.agent, input)
        logger.info("Translation Agent result:")
        logger.info(result.final_output)
        return {result.final_output}


class GitlabIssueOutput(BaseModel):
    """Combined output from GitLab issue parsing."""

    platform: PlatformData
    user_info: UserInfoData


class GitlabWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Gitlab Issue Agent",
            handoff_description="Agent for fetching information from Gitlab issue.",
            instructions=get_gitlab_prompt(),
            model="gpt-4o",
            output_type=GitlabIssueOutput,
            tools=[self.fetch_all_platforms],
        )

    @staticmethod
    def flow_worker_name():
        return "gitlab_worker"

    @function_tool
    async def fetch_all_platforms() -> str:
        """Fetch all available platforms from Brain API.
        Returns them in format platform_name(short_name)."""

        url = "https://brain.celus.net/knowledgebase/platforms/"
        headers = {"Authorization": f"Token {os.environ.get('BRAIN_TOKEN')}"}
        logger.info("Fetching all platforms")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            platforms = [BrainPlatform.model_validate(p) for p in response.json()]
            return platforms
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

    async def run(
        self, user_info: UserInfoData
    ) -> set[PlatformData | FileData | UserInfoData]:
        issue_iid = user_info.gitlab_issue
        if issue_iid is None:
            return {
                PlatformData(platform_name="", short_name="", provider=None, url=None)
            }

        # Fetch issue manually
        logger.info(f"Fetching Gitlab issue {issue_iid}")
        client = GitLabClient(
            token=os.environ.get("GITLAB_API_TOKEN"),
            project_id=os.environ.get("GITLAB_PROJECT_ID"),
        )
        issue: Issue = client.get_issue(issue_iid)
        client.download_files(
            issue.get_file_paths(), destination_folder="uploaded_files"
        )

        # Prepare content for the agent
        issue_content = issue.model_dump_json()

        # Run agent with issue content directly
        result = await Runner.run(self.agent, issue_content)

        output = GitlabIssueOutput.model_validate(result.final_output)

        platform_output = output.platform
        user_info_output = output.user_info

        file_data = None
        paths = issue.get_file_paths()
        if paths:
            # Take the first file for now-TODO deal with more files(separate issues)
            filename = paths[0].split("/")[-1]
            file_path = os.path.join("uploaded_files", filename)
            if os.path.exists(file_path):
                try:
                    file_format = FileFormat.from_file_extension(filename)
                    file_data = FileData(path=file_path, format=file_format)
                except ValueError:
                    logger.warning(f"Could not determine file format for {filename}")

        if file_data:
            return {platform_output, user_info_output, file_data}
        return {platform_output, user_info_output}


class ParsingRulesWorker(FlowWorker):
    # TODO interal parsing rules ID to allow for PUT requests
    @dataclass
    class Context:
        # necessary for sharing the information to the function tools, which cannot have self argument
        parser_definition: ParserDefinitionData | None = None
        parsed_data: ParsedData | None = None
        file_path: str | None = None
        report_type_id: int | None = None
        parser_id: int | None = None

    def __init__(self):
        self.agent = Agent[self.Context](
            name="Parsing Rules Agent",
            handoff_description="Specialist agent for parsing rules.",
            model="gpt-5.1",
            model_settings=ModelSettings(
                reasoning={"effort": "medium", "summary": "detailed"}
            ),
            tools=[self.check_parsing_rules],
        )
        self.context = self.Context()

    @staticmethod
    def flow_worker_name():
        return "parsing_rules_worker"

    @staticmethod
    def parse_data(string_json_parsing_rules: str, filename: str) -> pd.DataFrame | str:
        """Try to parse the data using the parsing rules."""
        dict_rules = json.loads(string_json_parsing_rules)
        parser_definition = Definition.parse(dict_rules)

        dynamic_parsers = [gen_parser(parser_definition)]

        poops = eat(
            file_path=filename,
            platform="val",
            check_platform=False,
            parsers=[e.name for e in dynamic_parsers],
            dynamic_parsers=dynamic_parsers,
        )

        poops[0].records_with_stats()
        df = pd.DataFrame(poops[0].records())

        # drop item_ids column
        df = df.drop(columns=["item_ids"], errors="ignore")

        # dimension data is dict, divide it into columns
        for col in df.columns:
            if isinstance(df[col].iloc[0], dict):
                # create new columns for each key in the dict
                dict_df = pd.json_normalize(df[col])
                # rename the columns to include the original column name
                dict_df.columns = [f"{col}.{k}" for k in dict_df.columns]
                # concatenate the new columns with the original dataframe
                df = pd.concat([df, dict_df], axis=1)
                # drop the original column
                df = df.drop(columns=[col])

        # keep only non None columns
        df = df.dropna(axis=1, how="all")
        # save the csv into uploaded_files folder
        df.to_csv(
            os.path.join("uploaded_files", f"{filename.split('/')[-1]}_parsed.csv"),
            index=False,
        )
        return df

    @staticmethod
    @function_tool
    def check_parsing_rules(
        wrapper: RunContextWrapper[Context], string_json_parsing_rules: str
    ) -> bool | str:
        """Check whether the generated parser rules conform to the expected format."""
        dict_rules = json.loads(string_json_parsing_rules)
        logger.info(f"Checking parsing rules: {dict_rules}")
        # upload into brain
        brain_client = BrainClient()
        parser_id =brain_client.create_or_update_parser_definition(generated_rules=dict_rules, report_type_id=wrapper.context.report_type_id, parser_id=wrapper.context.parser_id)
        wrapper.context.parser_id = parser_id
        # validate against parser definiton:
        try:
            ParserDefinitionData.model_validate(dict_rules)
            df = ParsingRulesWorker.parse_data(
                string_json_parsing_rules, filename=wrapper.context.file_path
            )
            parsed_data = ParsedData(columns=[], rows=[])
            parsed_data.from_df(df)
            wrapper.context.parsed_data = parsed_data
            wrapper.context.parser_definition = ParserDefinitionData.model_validate(
                dict_rules
            )
        except Exception as e:
            logger.exception(e)
            return str(e)

        return True

    async def run(
        self,
        data_description: DataDescriptionData,
        platform: PlatformData,
        metrics_dimensions: MetricsDimensionsData,
        file: FileData,
        user_info: UserInfoData,
        report_type: ReportTypeData,
    ) -> set[ParserDefinitionData, ParsedData]:
        metrics_for_llm = [
            (m.data_metric, m.brain_metric.short_name)
            for m in metrics_dimensions.metrics
        ]
        dimensions_for_llm = [
            (d.data_dimension, d.brain_dimension.short_name)
            for d in metrics_dimensions.dimensions
        ]
        self.agent.instructions = get_parsing_rules_prompt(
            metrics_for_llm,
            dimensions_for_llm,
            data_description.begin_month_year,
            data_description.end_month_year,
            data_description.title_report,
            data_description.title_identifiers,
            platform.name,
            user_info.user_comment,
        )
        logger.info("USER COMMENT: %s", user_info.user_comment)
        content = file.to_llm_format()
        self.context.file_path = file.path  # todo name more reasonably
        self.context.report_type_id = report_type.pk
        await Runner.run(self.agent, content, context=self.context)
        return {self.context.parser_definition, self.context.parsed_data}


FLOW_WORKERS: set[type[FlowWorker]] = {
    DataDescriptionWorker,
    ParsingRulesWorker,
    TranslationWorker,
    GitlabWorker,
}
