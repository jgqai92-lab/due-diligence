from pydantic import BaseModel


class SearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str = ""
    type: str = "stock"


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    count: int
