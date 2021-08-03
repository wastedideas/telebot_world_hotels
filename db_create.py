import peewee
from peewee_models import *

try:
    db.connect()
    UserModel.create_table()
except peewee.InternalError as er:
    print(str(er))
