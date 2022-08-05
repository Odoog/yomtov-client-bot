import json
import logging
from datetime import datetime, timedelta
from typing import List

from data_access_layer.database import Database
from data_access_layer.repository import Repository
from models.good import Good
import pygsheets


class LocalBrandSheetClient:

    def __init__(self, table_key):
        self.client = pygsheets.authorize(service_file='data_access_layer/account_credentials.json')
        self.sheet = self.client.open_by_key(table_key)
        self.db_sheet = self.sheet.worksheet_by_title('Список')

    def synchronize(self):
        values = self.db_sheet.get_all_values(returnas='matrix')
        Database._run("delete from local_brands where 1")
        for key, row in enumerate(values[1:]):
            if row[0] == "" or row[0] is None:
                break
            Database._run("insert into local_brands (id, nickname, phone, good_link, category) values (?, ?, ?, ?, ?)",
                          [key,
                           row[0].split("/")[-1],
                           row[1],
                           row[2],
                           row[3]])


class SheetsClient:

    def __init__(self, table_key):
        self.client = pygsheets.authorize(service_file='data_access_layer/account_credentials.json')
        self.sheet = self.client.open_by_key(table_key)
        self.db_sheet = self.sheet.worksheet_by_title('База товаров')
        self.attributes_sheet = self.sheet.worksheet_by_title('Атрибуты')
        self.metrics_sheet = self.sheet.worksheet_by_title('Метрики')
        self.filters_sheet = self.sheet.worksheet_by_title('Фильтры')

    def back_synchronize(self):
        self.attributes_sheet.update_row(21, [row["rating"] for row in Database._run("select rating from categories")], 1)
        self.attributes_sheet.update_row(19, [row["name"] for row in Database._run("select name from categories")], 1)

        self.filters_sheet.update_row(2, [[row["age"], row["sex"], row["age2"], row["spend"], "'" + row["reason"], row["relative"], row["likes_count"], row["dislikes_count"]] for row in Database._run("select * from filters_rating order by id")], 0)

        self.metrics_sheet.update_row(1, [[str(Database._run("select count(*) as count from users")[0]["count"])]], 1)
        users_added_last_day = len([user for user in Repository.get_all_users() if
                                    0 <= (int(datetime.today().timestamp()) - user.get_variable("added_date")) // 60 // 60 // 24 <= 1])
        users_added_last_week = len([user for user in Repository.get_all_users() if
                                     0 <= (int(datetime.today().timestamp()) - user.get_variable("added_date")) // 60 // 60 // 24 // 7 <= 1])
        self.metrics_sheet.update_row(2, [[str(users_added_last_day), str(users_added_last_week)]], 1)

    def synchronize(self):
        try:
            values = self.db_sheet.get_all_values(returnas='matrix')
            Database._run("delete from goods where 1")
            for key, row in enumerate(values[1:]):
                if row[0] == "" or row[0] is None:
                    break
                logging.info("Добавляю в систему товар {} с ценой {}".format(row[0], row[8]))
                Database._run("insert into goods ( \
                              id, name, brand, is_local_brand, is_universal, category, shop, good_link, good_picture_link, \
                              price, budget, reason, is_universal_reason, receiver, receiver_sex, receiver_age, \
                              receiver_relative, rating) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                              [key,
                               row[0],
                               row[1],
                               row[2] == "TRUE",
                               row[3] == "TRUE",
                               row[4],
                               row[5].replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0],
                               row[5],
                               row[6],
                               int("".join(filter(str.isdigit, row[7]))), # Цены часто в таблице в формате 1\xa0611, поэтому убираем все лишнее.
                               row[8],
                               row[9],
                               row[10] == "TRUE",
                               row[11],
                               row[12],
                               row[13],
                               row[14],
                               int(row[16] if row[16] != '' else 0)])

                if len(Database._run("select * from categories where name = ?", (row[4],))) == 0:
                    Database._run("insert into categories(name, rating) values (?, 0)", (row[4],))
        except Exception:
            logging.info("Произошла ошибка в функции synchronize")