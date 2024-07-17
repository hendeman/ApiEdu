import datetime
from datetime import datetime
import jwt
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Form, Request, Response, Cookie
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette import status
from fastapi.security import OAuth2PasswordRequestForm

from auth import authenticate_user, create_access_token, get_password_hash, oauth2_scheme, get_user
from config import ALGORITHM, SECRET_KEY, currencies
from database import get_db
from exception import InvalidUserDataException, custom_request_validation_exception_handler, not_found, validate_inputs
from models import User
from parser import get_exchange_data, convert_currency
from schemas import TodoModel, CurrencyExchange
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder

from templates import templates

app = FastAPI()

class UsernameMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in ["/register", "/login"]:
            token = request.cookies.get("access_token")
            if token:
                try:
                    token = token.split(" ")[1]  # Remove "Bearer " prefix
                    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                    username: str = payload.get("sub")
                    if username:
                        request.state.username = username
                except jwt.ExpiredSignatureError:
                    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
                except jwt.DecodeError:
                    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
            # else:
            #     return templates.TemplateResponse("protected_resource.html", {"request": request})

        response = await call_next(request)
        return response


# @app.post("/create_table")
# async def create_table():
#     query = ("CREATE TABLE users (id INTEGER PRIMARY KEY, title VARCHAR(255) NOT NULL, description VARCHAR(255) NOT NULL, completed BOOLEAN DEFAULT 0)")
#     try:
#         await database.execute(query=query, )
#         return {"message": "Таблица успешно создана"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail="Failed to create user")


# кастомный обработчик исключения для всех HTTPException
app.add_middleware(UsernameMiddleware)
app.add_exception_handler(404, not_found)
app.add_exception_handler(RequestValidationError, custom_request_validation_exception_handler)


def get_token_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def test(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/logout")
async def register(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response


@app.get("/protected_resource", response_class=HTMLResponse)
async def get_protected_resource_html(request: Request):
    username = getattr(request.state, 'username', None)
    return templates.TemplateResponse("protected_resource.html",
                                      {"request": request,
                                       "currencies": currencies,
                                       "username": username})


@app.post("/register", response_class=HTMLResponse)
async def add_todo(request: Request, username: str = Form(), password: str = Form(), db=Depends(get_db)):
    try:
        existing_user = get_user(username, db)
        if existing_user:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error_message": "Такое имя уже существует",
                "username": username,
                "password": password
            })
        item = User(username=username, password=get_password_hash(password))
        if item is None:
            raise InvalidUserDataException(status_code=404, detail="Объект не определен")

        db.add(item)
        db.commit()
        db.refresh(item)
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        return response

    except IntegrityError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unexpected error occurred: {}".format(e))


@app.post("/login")
async def login_for_access_token(username: str = Form(),
                                 password: str = Form(), db=Depends(get_db)):
    if not authenticate_user(db, username, password):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

    access_token = create_access_token(data={"sub": username})
    response = RedirectResponse(url="/protected_resource", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response


@app.post("/protected_resource")
async def protected_resource(request: Request,
                             rate_sale: str = Form(),
                             rate_buy: str = Form(),
                             value: float = Form()):

    await validate_inputs(rate_sale, rate_buy, value)

    current_date = datetime.now().strftime("%d/%m/%Y")
    url = f"https://www.belapb.by/api/ExCardsDaily/?ondate={current_date}"
    data = await get_exchange_data(url)
    try:
        converted_value, currency = await convert_currency(value, rate_sale, rate_buy, data)
    except:
        converted_value = "Ошибка получения значения"
        currency = None
    username = getattr(request.state, 'username', None)
    return templates.TemplateResponse("protected_resource.html", {
        "request": request,
        "rate_sale": rate_sale,
        "rate_buy": rate_buy,
        "currencies": currencies,
        "value": value,
        "username": username,
        "success_message": f'{converted_value} {currency}'
    }, status_code=200 if username else 401)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
