from pydantic import BaseModel, validator, model_validator

allowed_currencies = {"USD", "BYN", "CNY", "EUR", "RUB"}


class TodoModel(BaseModel):
    username: str
    password: str


class CurrencyExchange(BaseModel):
    rate_sale: str = "BYN"
    rate_buy: str = "USD"
    value: float = 0

    @validator('rate_sale', 'rate_buy')
    def validate_currency(cls, v):
        if v not in allowed_currencies:
            raise ValueError(f'Валюта {v} не найдена. Список допустимых валют: {allowed_currencies}')
        return v

    @model_validator(mode='after')
    def verify_square(self):
        if self.rate_sale == self.rate_buy:
            raise ValueError('валюты не должны совпадать')
        return self
