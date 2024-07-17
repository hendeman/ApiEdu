from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from typing import Any, Coroutine
from fastapi.encoders import jsonable_encoder
import datetime

from config import currencies
from templates import templates


class ErrorResponseModel(BaseModel):
    status_code: int
    detail: str
    error_code: int


class UserNotFoundException(HTTPException):
    def __init__(self, detail: str = 'lol', status_code: int = 400):
        super().__init__(detail=detail, status_code=status_code)


class InvalidUserDataException(HTTPException):
    def __init__(self, detail: str = 'lol', status_code: int = 404):
        super().__init__(detail=detail, status_code=status_code)


async def custom_request_validation_exception_handler(request, exc):
    error_messages = []
    for error in exc.errors():
        if error['type'] == 'float_parsing':
            error_messages.append('Значение должно быть числом')
        elif error['type'] == 'value_error':
            error_messages.append('Валюты не должны совпадать')
        elif error['type'] == 'negative_value_error':
            error_messages.append('Значение не должно быть отрицательным')
        else:
            error_messages.append(error['msg'])

    form_data = await request.form()
    rate_sale = form_data.get('rate_sale', 'BYN')
    rate_buy = form_data.get('rate_buy', 'USD')
    value = form_data.get('value', 0)
    print(error_messages)
    username = getattr(request.state, 'username', None)

    return templates.TemplateResponse("protected_resource.html", {
        "request": request,
        "rate_sale": rate_sale,
        "rate_buy": rate_buy,
        "value": value,
        "currencies": currencies,
        "username": username,
        "error_message": '; '.join(error_messages)
    }, status_code=422)


async def user_not_found_handler(request: Request, exc: ErrorResponseModel):
    start = datetime.datetime.now()
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers={'X-ErrorHandleTime': str(datetime.datetime.now() - start)}
    )


async def integrity_error_handler(request, exc):
    return JSONResponse(
        status_code=401,
        content={"message": "Integrity Error occurred: {}".format(exc.__cause__)}
    )


async def invalid_user_data_handler(request: Request, exc: ErrorResponseModel):
    start = datetime.datetime.now()
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers={'X-ErrorHandleTime': str(datetime.datetime.now() - start)}
    )


async def not_found(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


async def validate_inputs(rate_sale: str, rate_buy: str, value: float):
    if rate_sale == rate_buy:
        error = {
            'loc': ['body', 'rate_sale'],
            'msg': 'Валюты не должны совпадать',
            'type': 'value_error'
        }
        raise RequestValidationError([error])

    if value < 0:
        error = {
            'loc': ['body', 'value'],
            'msg': 'Значение не должно быть отрицательным',
            'type': 'negative_value_error'
        }
        raise RequestValidationError([error])
