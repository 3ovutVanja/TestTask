from config import db_name, db_user, db_host, db_pass, db_port


TORTOISE_ORM = {
    "connections": {"default": f"mysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"},
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
