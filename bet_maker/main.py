from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from tortoise import Tortoise
from tortoise.transactions import atomic
from tortoise_conf import TORTOISE_ORM
import logging
from fastapi_utils.tasks import repeat_every
from typing import List
from fastapi.responses import JSONResponse
from logging_config import setup_logging, logging_config
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
from models import ActualEvents, Bet
import requests
import aio_pika
import asyncio
from typing import Optional
import json
import config
from schemas import EventOut, BetOut, BetCreate, BetStatus


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


async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        message_body = message.body
        message_str = message_body.decode('utf-8')
        message_data = json.loads(message_str)
        logger.info(f"Received message: {message_data}")
        event_id = message_data.get("event_id")
        new_status = message_data.get("status")
        if new_status != "незавершённое":
            event = await ActualEvents.filter(lp_id=event_id).first()
            if event:
                await event.delete()
                logger.info(f"Deleted event with lp_id: {event_id}")
            if new_status == "завершено выигрышем первой команды":
                new_status = BetStatus.won
            elif new_status == "завершено выигрышем второй команды":
                new_status = BetStatus.lost
            else:
                new_status = BetStatus.pending
            bets = await Bet.filter(lp_id=event_id).all()
            for bet in bets:
                bet.status = new_status
                await bet.save()
                logger.info(f"Updated bet ID {bet.id} with status {new_status}")


async def startup():
    global connection, channel
    connection = await aio_pika.connect_robust(f"amqp://{config.mq_user}:{config.mq_pwd}@{config.mq_host}/")
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)  # Ограничение количества сообщений, которые обрабатываются одновременно
    queue = await channel.declare_queue("event_status_updates", durable=True)
    await queue.consume(lambda message: asyncio.create_task(process_message(message)), no_ack=False)


async def shutdown():
    global connection
    if connection:
        await connection.close()
        print("Closed RabbitMQ connection")


@repeat_every(seconds=5)
async def get_actual_events():
    try:
        response = requests.get(f"http://{config.lp_host}:8001/actual_events/")
        response.raise_for_status()
        events = response.json()
        current_events = await ActualEvents.all()
        current_events_dict = {event.lp_id: event for event in current_events}
        received_ids = {event['id'] for event in events}
        ids_to_delete = [event.id for event in current_events if event.lp_id not in received_ids]
        if ids_to_delete:
            await ActualEvents.filter(id__in=ids_to_delete).delete()
            logger.info(f"Deleted {len(ids_to_delete)} events from the database")
        for event_data in events:
            lp_id = event_data['id']
            coefficient = event_data['coefficient']
            if lp_id in current_events_dict:
                pass
            else:
                new_event = ActualEvents(lp_id=lp_id, coefficient=coefficient)
                await new_event.save()
                logger.info(f"Added new event {lp_id} with coefficient: {coefficient}")
    except Exception as e:
        logger.error(f"Failed to update actual events: {str(e)}")
        raise e


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    await get_actual_events()
    await startup()
    logger.info(f'Database initiated')
    yield
    await shutdown()
    await Tortoise.close_connections()


app = FastAPI(title="Bet Maker", lifespan=lifespan)
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
    logger.error(f"HTTPException: {str(exc)}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"RequestValidationError: {str(exc)}")
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


@app.get("/events/", response_model=list[EventOut])
async def get_events():
    logger.debug("Received request to get all events")
    events = await ActualEvents.all()
    logger.info(f"Retrieved {len(events)} events")
    return [
        EventOut(
            lp_id=event.lp_id,
            coefficient=event.coefficient
        ) for event in events
    ]


@app.post("/bet", response_model=BetOut)
async def create_bet(bet_data: BetCreate):
    event = await ActualEvents.get_or_none(lp_id=bet_data.lp_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    bet = Bet(lp_id=bet_data.lp_id, amount=bet_data.amount)
    await bet.save()
    logger.info(f"Created bet with ID: {bet.id} for event ID: {bet.lp_id}")
    return BetOut(
        id=bet.id,
        lp_id=bet.lp_id,
        amount=float(bet.amount),
        status=bet.status
    )


@app.get("/bets", response_model=List[BetOut])
async def get_bets():
    logger.debug("Received request to get all bets")
    bets = await Bet.all()
    logger.info(f"Retrieved {len(bets)} bets")
    return [
        BetOut(
            id=bet.id,
            lp_id=bet.lp_id,
            amount=float(bet.amount),
            status=bet.status
        ) for bet in bets
    ]

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8002, log_level="debug", log_config=uvicorn_log_config)
