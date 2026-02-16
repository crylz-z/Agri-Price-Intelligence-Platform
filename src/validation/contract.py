import pandera as pa
from pandera.typing import DataFrame, Series
from datetime import datetime

class RawPriceSchema(pa.DataFrameModel):
    """
    Strict Data Contract for APIP Raw Price Data.
    enforces types and constraints before data enters the Silver Layer.
    """
    extract_dt: Series[str] = pa.Field(coerce=True) # Check date format later or allow string for now
    region_id: Series[str] = pa.Field(coerce=True, nullable=False)
    market_name: Series[str] = pa.Field(coerce=True, nullable=False)
    category: Series[str] = pa.Field(coerce=True, nullable=False)
    commodity: Series[str] = pa.Field(coerce=True, nullable=False)
    price: Series[float] = pa.Field(ge=0, coerce=True, nullable=False) # Price must be positive float

    class Config:
        strict = True # Reject columns not defined in schema
        coerce = True # Attempt to convert types (e.g. "10.50" -> 10.5)
