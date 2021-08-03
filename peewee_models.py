import os
from peewee import *
from playhouse.db_url import connect

db = connect(os.environ.get('DATABASE_URL'), 'sqlite:///chat_users.db')


class UserModel(Model):
    RU = 'ru_RU'
    EN = 'en_EN'
    LANGUAGE = (
        (RU, 'ru'),
        (EN, 'en'),
    )
    chat_id = IntegerField(null=False)
    language = CharField(max_length=5, choices=LANGUAGE, default='ru_RU')
    sort_order = CharField(max_length=30, null=True)
    country = CharField(max_length=100, null=True)
    city = CharField(max_length=10000, null=True)
    number_of_hotels = CharField(max_length=2, null=True)
    check_in = CharField(max_length=10, null=True)
    check_out = CharField(max_length=10, null=True)
    min_price = CharField(max_length=10, null=True)
    max_price = CharField(max_length=10, null=True)

    def get_language_display(self):
        return dict(self.LANGUAGE)[str(self.language)]

    class Meta:
        database = db
