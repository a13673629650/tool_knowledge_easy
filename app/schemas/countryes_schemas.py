from pydantic import BaseModel


class CountriesSchema(BaseModel):
    id:int
    name:str