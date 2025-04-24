from pydantic import BaseModel
import typing
from enum import Enum
import json
from base import FlowData
import pandas as pd
class Direction(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"

class RelativeTo(str, Enum):
    AREA = "area"
    PARSER = "parser"
    START = "start"

class Coord(BaseModel):
    row: int
    col: int

class CoordRange(BaseModel):
    coord: Coord
    direction: Direction
    max_count: int | None = None

class Value(BaseModel):
    value: typing.Any

Source = typing.Union[Coord, CoordRange, Value]

class TableException(BaseModel):
    class Action(str, Enum):
        FAIL = "fail"
        SKIP = "skip"
        STOP = "stop"
        PASS = "pass"

class ExtractParams(BaseModel):
    regex: typing.Pattern | None = None
    default: typing.Any | None = None
    last_value_as_default: bool = False
    on_validation_error: TableException.Action = TableException.Action.FAIL

class RoleEnum(str, Enum):
    VALUE = "value"
    DATE = "date"
    TITLE = "title"
    TITLE_ID = "title_id"
    DIMENSION = "dimension"
    METRIC = "metric"
    ORGANIZATION = "organization"

class MetricSource(BaseModel):
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.METRIC]

class ComposedDate(BaseModel):
    year: "DateSource"
    month: "DateSource"

class DateSource(BaseModel):
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    composed: ComposedDate | None = None
    date_pattern: str | None = None
    role: typing.Literal[RoleEnum.DATE]



class DataHeaders(BaseModel):
    roles: typing.List[typing.Union[MetricSource, DateSource]]

    data_cells: CoordRange  # first data after the header
    data_direction: Direction  # perpendicular to data_cells

class TitleSource(BaseModel):
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.TITLE]

class TitleIdKind(str, Enum):
    ISBN = "ISBN"
    Print_ISSN = "Print_ISSN"
    Online_ISSN = "Online_ISSN"
    Proprietary = "Proprietary"
    DOI = "DOI"
    URI = "URI"

class TitleIdSource(BaseModel):
    name: TitleIdKind
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.TITLE_ID]

class OrganizationSource(BaseModel):
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.ORGANIZATION]

class DimensionSource(BaseModel):
    name: str
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.DIMENSION]

class NonCounterGeneric(BaseModel): #Generic Area Definition
    metrics: typing.Optional[MetricSource]
    data_headers: DataHeaders
    dates: typing.Optional[DateSource]
    titles: typing.Optional[TitleSource]
    title_ids: typing.List[TitleIdSource] = []
    dimensions: typing.List[DimensionSource] = []
    organizations: typing.Optional[OrganizationSource]

class Heuristics(BaseModel):
    conds: typing.List = []
    kind: typing.Literal["and"] = "and"

class DataFormat(BaseModel):
    name: str = "format"

class ParserDefinitionData(FlowData):
    parser_name: str
    data_format: DataFormat
    platforms: typing.List[str] = []
    metrics_to_skip: typing.List[str] = []
    available_metrics: typing.Optional[typing.List[str]]
    on_metric_check_failed: TableException.Action = TableException.Action.SKIP
    titles_to_skip: typing.List[str] = []
    areas: typing.List[NonCounterGeneric]
    metric_aliases: typing.List[typing.Tuple[str, str]] = []
    dimension_aliases: typing.List[typing.Tuple[str, str]] = []

    kind: typing.Literal["non_counter.generic"] = "non_counter.generic"
    heuristics: Heuristics = Heuristics()

    #dimensions_to_skip: typing.Dict[str, typing.List[str]] = {}

    @staticmethod
    def flow_data_name():
        return 'parser_definition_data'


class Granularity(str, Enum):
    MONTHLY = "monthly"
    DAILY = "daily"
    OTHER = "other"



class PlatformData(FlowData):

    """
    Includes platform name, whether it exists and its parser names
    """

    platform_name: str
    exists: bool
    parser_names: typing.List[str]

    @staticmethod
    def flow_data_name():
        return 'platform_data'

class UserInfoData(FlowData):

    user_comment: str

    @staticmethod
    def flow_data_name():
        return 'user_info_data'

class FileData(FlowData):

    """
    Includes file name,
    should also include helpter functions to get the files
    """
    filename: str

    @staticmethod
    def flow_data_name():
        return 'file_data'
    
class DataDescriptionData(FlowData):
    """
    Includes data description
    """
    begin_month_year: str
    end_month_year: str
    english: bool
    title_report: bool
    granularity: Granularity
    title_identifiers : typing.List[TitleIdKind]
    metrics: typing.List[str]
    dimensions: typing.List[str]

    @staticmethod
    def flow_data_name():
        return 'data_description_data'

class ParsedData(FlowData):
    columns: list[dict[str,str]]
    rows: list[dict[str,str]]

    def from_df(self, df: pd.DataFrame):
        self.columns = [{"field": col, "header": col} for col in df.columns]
        self.rows = df.to_dict(orient="records")

    @staticmethod
    def flow_data_name():
        return 'parsed_data'
    
FLOW_DATA: set[type[FlowData]] = {PlatformData, FileData, DataDescriptionData, ParserDefinitionData, UserInfoData, ParsedData}