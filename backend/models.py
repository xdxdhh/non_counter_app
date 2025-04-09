from pydantic import BaseModel
import typing
from enum import Enum
from pathlib import Path
import json
from base import FlowData

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
    #row_relative_to: RelativeTo = RelativeTo.AREA

class CoordRange(BaseModel):
    coord: Coord
    direction: Direction
    max_count: typing.Optional[int]

class Value(BaseModel):
    #value: typing.Any 
    value: str | int | float | bool

#Source = Union[Coord, CoordRange, SheetAttr, Value]

Source = typing.Union[Coord, CoordRange, Value]


class TableException(BaseModel):
    class Action(str, Enum):
        FAIL = "fail"
        SKIP = "skip"
        STOP = "stop"
        PASS = "pass"

class ExtractParams(BaseModel):
    #regex: typing.Optional[typing.Pattern] GPT does not allow
    regex: typing.Optional[str]
    #default: typing.Optional[typing.Any] GPT does not allow
    default: typing.Optional[str]
    last_value_as_default: bool
    #blank_values: typing.Tuple[typing.Any, ...] = field(default_factory=lambda: (None, ""))
    #blank value nahrada prazdne '-' napr z tohoto udela 0
    #skip_validation: bool = False
    #prefix: str = ""
    #suffix: str = ""
    #special_extraction: SpecialExtraction = SpecialExtraction.NO
    on_validation_error: TableException.Action = TableException.Action.FAIL
    #max_idx: typing.Optional[int] = None

class RoleEnum(str, Enum):
    VALUE = "value"
    DATE = "date"
    TITLE = "title"
    TITLE_ID = "title_id"
    DIMENSION = "dimension"
    METRIC = "metric"
    ORGANIZATION = "organization"
    VOID = "void"
    AUTHORS = "authors"
    PUBLICATION_DATE = "publication_date"

class MetricSource(BaseModel):
    source: Source
    extract_params: ExtractParams
    #fallback: typing.Optional["MetricSource"] = None
    # cleanup_during_header_processing: bool
    role: typing.Literal[RoleEnum.METRIC]

class ComposedDate(BaseModel):
    year: "DateSource"
    month: "DateSource"

class DateSource(BaseModel):
    composed: typing.Optional[ComposedDate]
    source: Source
    extract_params: ExtractParams
    #fallback: typing.Optional["DateSource"] = None
    #cleanup_during_header_processing: bool = True
    #preferred_date_format: DateFormat = DateFormat.US
    
    date_pattern: typing.Optional[str]
    #force_aligned: bool = False
    role: typing.Literal[RoleEnum.DATE]



class DataHeaders(BaseModel):
    roles: typing.List[typing.Union[MetricSource, DateSource]]

    data_cells: CoordRange  # first data after the header
    data_direction: Direction  # perpendicular to data_cells
    #data_extract_params: ExtractParams = field(
    #    default_factory=lambda: ExtractParams(on_validation_error=TableException.Action.STOP)
    #)
    #data_allow_negative: bool = False
    #data_cells_options: "DataCellsOptions" = field(
    #    default_factory=lambda: DataCellsOptions(use_header_year=True, use_header_month=True)
    #)

    #rules: typing.List[DataHeaderRule] = Field(default_factory=lambda: [DataHeaderRule()])
    #condition: typing.Optional[Condition] = None
    


class TitleSource(BaseModel):
    source: Source
    extract_params: ExtractParams
    #fallback: typing.Optional["TitleSource"] = None
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
    extract_params: ExtractParams
    #fallback: typing.Optional["TitleIdSource"] = None
    #validator_opts: typing.Optional[IdValidatorOpts] = None
    role: typing.Literal[RoleEnum.TITLE_ID]

class OrganizationSource(BaseModel):
    source: Source
    extract_params: ExtractParams
    #fallback: typing.Optional["OrganizationSource"] = None
    #cleanup_during_header_processing: bool = True
    role: typing.Literal[RoleEnum.ORGANIZATION]

class DimensionSource(BaseModel):
    name: str
    source: Source
    extract_params: ExtractParams
    #fallback: typing.Optional["DimensionSource"] = None
    #cleanup_during_header_processing: bool = True
    role: typing.Literal[RoleEnum.DIMENSION]

class NonCounterGeneric(BaseModel): #Generic Area Definition
    data_headers: DataHeaders
    metrics: typing.Optional[MetricSource]
    dates: typing.Optional[DateSource]
    titles: typing.Optional[TitleSource]
    #title_ids: typing.List[TitleIdSource] = []
    title_ids: typing.List[TitleIdSource]
    #dimensions: typing.List[DimensionSource] = []
    dimensions: typing.List[DimensionSource]
    organizations: typing.Optional[OrganizationSource]

class ParserDefinitionData(FlowData):
    parser_name: str
    platforms: typing.List[str]
    metrics_to_skip: typing.List[str]
    available_metrics: typing.Optional[typing.List[str]]
    on_metric_check_failed: TableException.Action
    titles_to_skip: typing.List[str]
    areas: typing.List[NonCounterGeneric]
    #dimensions_to_skip: typing.Dict[str, typing.List[str]]
    #metric_aliases: typing.List[typing.Tuple[str, str]] TODO solve, GPT does not want this
    #metric_aliases: list[tuple[str, str]]
    #dimension_aliases: typing.List[typing.Tuple[str, str]]

    @staticmethod
    def flow_data_name():
        return 'parser_definition_data'

#Path("parser_request.json").write_text(json.dumps(ParserDefinitionData.model_json_schema(), indent=4))


class Granularity(str, Enum):
    MONTHLY = "monthly"
    DAILY = "daily"
    OTHER = "other"



class PlatformData(FlowData):

    """
    Includes platform name, and whether it exists #TODO parsers
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
    
FLOW_DATA: set[type[FlowData]] = {PlatformData, FileData, DataDescriptionData, ParserDefinitionData, UserInfoData}