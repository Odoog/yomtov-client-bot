import logging
from threading import Timer
from types import SimpleNamespace

from bot import Bot
from data_access_layer.repository import Repository
from global_transferable_entities.user import User
import sched, time


class UpdateDatabaseDaemon:

    def __init__(self,
                 bot: Bot):
        self._bot = bot
        self._interval = 120
        self._timer = Timer(self._interval, self.execute_daemon_action)

    def start_daemon(self):
        self._timer.start()

    def execute_daemon_action(self):
        self.update_info()
        self._timer = Timer(self._interval, self.execute_daemon_action)
        self._timer.start()

    def update_info(self):
        logging.info("UpdateDatabaseDaemon: updating info circle")
        user_ids = Repository.get_all_user_ids_with_received_order()
        for user_id in user_ids:
            user = User(user_id, "")
            user.change_stage("NewUser")

            update = SimpleNamespace()
            update.message = SimpleNamespace()
            update.message.chat = SimpleNamespace()
            update.effective_chat = SimpleNamespace()
            update.effective_chat.id = user_id
            update.message.chat.username = ""
            update.message.text = "dd"

            self._bot.process_message(update)
