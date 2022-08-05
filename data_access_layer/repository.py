import logging
from typing import List

from data_access_layer.database import Database
from global_transferable_entities.user import User
from models.good import Good


class Repository(Database):

    @staticmethod
    def get_all_goods():
        goods_from_database = Database._run("select * from goods")
        return [Good(*good) for good in goods_from_database]

    @staticmethod
    def get_all_user_ids_with_received_order() -> List[str]:
        data = Database._run("select chat_id from users where status = 'order_completed'")
        Database._run("update users set status = 'getting_review' where status = 'order_completed'")
        return (row['chat_id'] for row in data)