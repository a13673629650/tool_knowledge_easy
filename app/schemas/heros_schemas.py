from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class CreateHeroes(BaseModel):
    name:str
    power: int
    countryId: int
class UpdateHeroes(BaseModel):
    # orm对象序列化  前端传来的驼峰转_
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel,
                              populate_by_name=True)
    id:int
    name:str  = Field(...)
    power: int = Field(...)
    countryId: int


