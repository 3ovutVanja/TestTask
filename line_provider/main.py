from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from tortoise import Tortoise
from tortoise_conf import TORTOISE_ORM
import logging
from fastapi.responses import JSONResponse
from logging_config import setup_logging, logging_config
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
import config
import json
from typing import Optional
import aio_pika
from datetime import datetime
from models import Event, EventStatus
from schemas import EventIn, EventOut, StatusUpdate, EventBasicOut


setup_logging()
logger = logging.getLogger(__name__)

uvicorn_log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": logging_config["formatters"],
    "handlers": logging_config["handlers"],
    "loggers": {
        "uvicorn.error": {
            "level": "DEBUG",
            "handlers": ["file", "console"],
            "propagate": False
        },
        "uvicorn.access": {
            "formatter": "default",
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False
        },
    },
}

connection: Optional[aio_pika.Connection] = None
channel: Optional[aio_pika.Channel] = None


async def startup():
    global connection, channel
    connection = await aio_pika.connect_robust(f"amqp://{config.mq_user}:{config.mq_pwd}@{config.mq_host}/")
    channel = await connection.channel()
    await channel.declare_queue("event_status_updates", durable=True)


async def shutdown():
    global connection
    if connection:
        await connection.close()
        print("Closed RabbitMQ connection")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    await startup()
    logger.info(f'Database initiated')
    yield
    await shutdown()
    await Tortoise.close_connections()


app = FastAPI(title="Line Provider", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTPException: {str(exc.detail)}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"RequestValidationError: {str(exc.errors())}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"}
    )


@app.post("/events/", response_model=EventOut)
async def create_event(event: EventIn):
    logger.debug(f"Received request to create event: {event.json()}")
    event_obj = Event(
        coefficient=event.coefficient,
        deadline=event.deadline,
        status=event.status
    )
    await event_obj.save()
    logger.info(f"Event created with ID: {event_obj.id}")
    return EventOut(
        id=event_obj.id,
        coefficient=event_obj.coefficient,
        deadline=event_obj.deadline,
        status=event_obj.status
    )


@app.get("/events/", response_model=list[EventOut])
async def get_events():
    logger.debug("Received request to get all events")
    events = await Event.all()
    logger.info(f"Retrieved {len(events)} events")
    return [
        EventOut(
            id=event.id,
            coefficient=event.coefficient,
            deadline=event.deadline,
            status=event.status
        ) for event in events
    ]


@app.get("/actual_events/", response_model=list[EventBasicOut])
async def get_actual_events():
    logger.debug("Received request to get all events with active deadlines")
    current_time = datetime.utcnow()
    events = await Event.filter(deadline__gt=current_time, status=EventStatus.unfinished)
    logger.info(f"Retrieved {len(events)} active events")
    return [
        EventBasicOut(
            id=event.id,
            coefficient=event.coefficient
        ) for event in events
    ]


@app.get("/events/{event_id}", response_model=EventOut)
async def get_event(event_id: int):
    logger.debug(f"Received request to get event with ID: {event_id}")
    event = await Event.get(id=event_id)
    return EventOut(
        id=event.id,
        coefficient=event.coefficient,
        deadline=event.deadline,
        status=event.status
    )


@app.put("/events/{event_id}/status", response_model=EventOut)
async def update_event_status(event_id: int, status_update: StatusUpdate):
    logger.debug(f"Received request to update status of event with ID: {event_id} to {status_update.status}")
    event = await Event.get(id=event_id)
    event.status = status_update.status
    await event.save()
    logger.info(f"Event status updated for ID: {event_id}")
    await send_event_update(event_id, status_update.status)
    return EventOut(
        id=event.id,
        coefficient=event.coefficient,
        deadline=event.deadline,
        status=event.status
    )


async def send_event_update(event_id: int, status: EventStatus):
    message = json.dumps({"event_id": event_id, "status": status.value})
    await channel.default_exchange.publish(
        aio_pika.Message(body=message.encode()),
        routing_key="event_status_updates",
    )


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8001, log_level="debug", log_config=uvicorn_log_config)
