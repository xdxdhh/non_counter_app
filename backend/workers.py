from base import FlowWorker
import requests
from agents import Runner, Agent, function_tool, RunContextWrapper, ModelSettings
import typing
from prompts import (
    get_data_description_prompt,
    get_parsing_rules_prompt,
    get_translation_prompt,
    get_platform_prompt,
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
    ParserDefinitionAPI,
)
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
                logger.error("Brain %s %s failed: %s", response.request.method, response.url, response.text)
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
            logger.error("Brain %s %s failed: %s", response.request.method, response.url, response.text)
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
            if metric.brain_metric is None:  # we have to create the metric
                metric.brain_metric = self.create_metric(metric.data_metric)
        for dimension in dimensions:
            if dimension.brain_dimension is None:
                dimension.brain_dimension = self.create_dimension(
                    dimension.data_dimension
                )
        return metrics_dimensions_data

    def create_report_type(
        self,
        metrics_dimensions_data: MetricsDimensionsData,
        platform_data: PlatformData,
        data_description_data: DataDescriptionData,
    ):
        dimension_ids = [
            dimension.brain_dimension.id
            for dimension in metrics_dimensions_data.dimensions
        ]
        metric_ids = [
            metric.brain_metric.id for metric in metrics_dimensions_data.metrics
        ]
        metrics_with_groups = [
            {"metric": mid, "interest_group": "Full text"} for mid in metric_ids
        ]
        report_type = {
            "short_name": f"{platform_data.short_name}-test",
            "name": f"{platform_data.name} Test",
            "platforms": [platform_data.pk],
            "dimensions": dimension_ids,
            "uses_titles": data_description_data.title_report,
            "uses_items": False,
            "metrics": metrics_with_groups,
        }
        logger.info(f"Creating report type: {report_type}")
        url = f"{self.base_url}/report_types/"
        response = requests.post(url, headers=self.headers, json=report_type, timeout=30)
        if not response.ok:
            logger.error("Brain %s %s failed: %s", response.request.method, response.url, response.text)
        response.raise_for_status()
        return response.json()

class PlatformAgentWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Platform Agent",
            handoff_description="Specialist agent for questions about platforms.",
            instructions=get_platform_prompt(),
            model="gpt-4o-mini",
            tools=[self.fetch_all_platforms],
            output_type=PlatformData,
        )

    @function_tool
    async def fetch_all_platforms() -> str:
        """Fetch all available platforms from Brain API.
        Returns them in format platform_name(short_name)."""

        url = "https://brain.celus.net/knowledgebase/platforms/"
        headers = {
            "Authorization": f"Token {os.environ.get('BRAIN_TOKEN')}"
        }  # expects BRAIN_TOKEN in env
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

    @function_tool
    async def fetch_all_parsers() -> str:
        """Fetch all available parsers from Brain API.
        Returns them in format parser_name(platforms).
        """
        url = "https://brain.celus.net/knowledgebase/parsers/"
        headers = {"Authorization": f"Token {os.environ.get('BRAIN_TOKEN')}"}
        logger.info("Fetching all parsers")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            parsers = [ParserDefinitionAPI.model_validate(p) for p in response.json()]
            return ",".join(f"Parser {p.parser_name}({p.platforms})" for p in parsers)
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

    @staticmethod
    def flow_worker_name():
        return "platform_worker"

    async def run(self, platform: PlatformData) -> set[PlatformData]:
        logger.info(f"Platform Agent: Checking platform {platform.platform_name}")
        prompt = f"I am interested in {platform.platform_name} platform."
        result = await Runner.run(self.agent, prompt)
        # create the PlatformData object
        logger.info(f"Platform Agent result: {result.final_output}")
        output = PlatformData.model_validate(result.final_output)
        return {output}


class DataDescriptionWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Data Description Agent",
            handoff_description="Specialist agent for describing data.",
            instructions=get_data_description_prompt(),
            model="gpt-4o",
            output_type=DataDescriptionData,
        )

    @staticmethod
    def flow_worker_name():
        return "data_description_worker"

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


class GitlabWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Gitlab Issue Agent",
            handoff_description="Agent for fetching information from Gitlab issue.",
            instructions=get_gitlab_prompt(),
            model="gpt-4o",
            output_type=PlatformData,
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

    async def run(self, user_info: UserInfoData) -> set[PlatformData | FileData]:
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
        output = PlatformData.model_validate(result.final_output)

        file_data = None
        paths = issue.get_file_paths()
        if paths:
            # Take the first file for now
            filename = paths[0].split("/")[-1]
            file_path = os.path.join("uploaded_files", filename)
            if os.path.exists(file_path):
                try:
                    file_format = FileFormat.from_file_extension(filename)
                    file_data = FileData(path=file_path, format=file_format)
                except ValueError:
                    logger.warning(f"Could not determine file format for {filename}")

        if file_data:
            return {output, file_data}
        return {output}


class ParsingRulesWorker(FlowWorker):
    @dataclass
    class Context:
        # necessary for sharing the information to the function tools, which cannot have self argument
        parser_definition: ParserDefinitionData | None = None
        parsed_data: ParsedData | None = None
        file_path: str | None = None

    def __init__(self):
        self.agent = Agent[self.Context](
            name="Parsing Rules Agent",
            handoff_description="Specialist agent for parsing rules.",
            model="gpt-5.1",
            model_settings=ModelSettings(reasoning={"effort": "medium"}),
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
        await Runner.run(self.agent, content, context=self.context)
        return {self.context.parser_definition, self.context.parsed_data}


FLOW_WORKERS: set[type[FlowWorker]] = {
    PlatformAgentWorker,
    DataDescriptionWorker,
    ParsingRulesWorker,
    TranslationWorker,
    GitlabWorker,
}
