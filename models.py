#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import calendar
from peewee import Model, SqliteDatabase, InsertQuery,\
                   IntegerField, CharField, DoubleField, BooleanField,\
                   DateTimeField, OperationalError, create_model_tables, fn
from playhouse.flask_utils import FlaskDB
from playhouse.pool import PooledMySQLDatabase
from playhouse.shortcuts import RetryOperationalError
from datetime import datetime, timedelta
from base64 import b64encode

from . import config
from .utils import get_pokemon_name, get_pokemon_rarity, get_pokemon_types, get_args, send_to_webhook
from .transform import transform_from_wgs_to_gcj
from .customLog import printPokemon

log = logging.getLogger(__name__)
flaskDb = FlaskDB()

class MyRetryDB(RetryOperationalError, PooledMySQLDatabase):
    pass


def init_database(app):
    if args.db_type == 'mysql':
        log.info('Connecting to MySQL database on %s:%i', 'restokitch.com', '3306')
        db = MyRetryDB(
            restokit_pokemon,
            user=restokit_pokemon,
            password=pokemon123,
            host=restokitch.com,
            port=3306,
            stale_timeout=300)
    else:
        log.info('Error Connecting to database')
        #db = SqliteDatabase(args.db)

    app.config['DATABASE'] = db
    flaskDb.init_app(app)

    return db

def bulk_upsert(cls, data):
num_rows = len(data.values())
i = 0
step = 120

flaskDb.connect_db()

while i < num_rows:
    log.debug('Inserting items %d to %d', i, min(i+step, num_rows))
    try:
        InsertQuery(cls, rows=data.values()[i:min(i+step, num_rows)]).upsert().execute()
    except Exception as e:
        log.warning('%s... Retrying', e)
        continue

    i+=step

flaskDb.close_db(None)