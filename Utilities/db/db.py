# db
from os.path import isfile
from sqlite3 import connect
import asyncio
import asqlite
import re

# custom utilities and setup
from Utilities import log

log = log.Logger("db")

DB_PATH = "./Data/database.db"
BUILD_PATH = "./Utilities/db/build.sql"


def regexp(expr, item):
    if expr == "" or expr == None:
        return True
    if item == "":
        return False
    print(item, expr)
    reg = re.compile(expr)
    return reg.search(item) is not None


async def build():
    async with asqlite.connect(DB_PATH) as connection:
        async with connection.cursor() as cursor:
            if isfile(BUILD_PATH):
                with open(BUILD_PATH, "r", encoding="utf-8") as script:
                    await cursor.executescript(script.read())

                    await log.info("Database built.")


async def commit():
    async with asqlite.connect(DB_PATH) as connection:
        await connection.commit()

        await log.info("Committed to database.")


async def close():
    async with asqlite.connect(DB_PATH) as connection:
        await connection.close()

        await log.info("Closed database connection.")


async def field(command, *values):
    async with asqlite.connect(DB_PATH) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(command, tuple(values))

            if (fetch := await cursor.fetchone()) is not None:
                return fetch[0]


async def insert_getid(command, *values):
    async with asqlite.connect(DB_PATH) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(command, tuple(values))

            await cursor.execute("select last_insert_rowid()")

            if (fetch := await cursor.fetchone()) is not None:
                return fetch[0]


async def record(command, *values):
    async with asqlite.connect(DB_PATH) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(command, tuple(values))

            return await cursor.fetchone()


async def records(command, *values):
    async with asqlite.connect(DB_PATH) as connection:
        await connection._post(
            lambda: connection._conn.create_function(
                "regexp", 2, regexp, deterministic=True
            )
        )
        async with connection.cursor() as cursor:
            await cursor.execute(command, tuple(values))

            return await cursor.fetchall()


async def column(command, *values):
    async with asqlite.connect(DB_PATH) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(command, tuple(values))

            return [item[0] for item in await cursor.fetchall()]


async def execute(command, *values):
    async with asqlite.connect(DB_PATH) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(command, tuple(values))


async def multiexec(command, valueset):
    async with asqlite.connect(DB_PATH) as connection:
        async with connection.cursor() as cursor:
            await cursor.executemany(command, valueset)
