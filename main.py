import json
import logging
import os
import random

from telegram import ParseMode

from daemon.update_db_daemon import UpdateDatabaseDaemon
from data_access_layer.database import Database
from data_access_layer.repository import Repository
from global_transferable_entities.user import User
from site_worker.worker import Worker
from state_constructor_parts.action import ActionChangeUserVariable, ActionChangeUserVariableToInput, ActionChangeStage, \
    Action, PrerequisiteAction
from bot import Bot
from message_parts.message import Message, MessageKeyboard, MessageKeyboardButton, MessagePicture
from global_transferable_entities.scope import Scope
from state_constructor_parts.stage import Stage
from data_access_layer.google_tables import SheetsClient, LocalBrandSheetClient
from statistics_entities.custom_stats import UserStatsCyclesFinishCount, UserStatsCyclesStartCount
from statistics_entities.stage_stats import StageStatsVisitCount
from statistics_entities.user_stats import UserStatsVisitCount, UserStatsCurrentStage

if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    # filename='log.txt')
    logging.info("Program started")

    # --- Helper methods ---

    def generate_order_information(_, __):
        information = "Номер заказа: [00000]. Назовите его упаковщику по адресу [адрес пункта, который выбрал клиент – без города, только улица и дом, офис, притом после точек не должно быть пробелов, чтобы знаки лишние не ставить, например: Ул.Фролова, д.1]"
        return information

    def generate_after_order_question(_, __):

        question_ridge_models = [
            # "Подарок упакован! Скажите, понравилась ли вам услуга (это важно): [ССЫЛКА]",
            # "Подарок упакован! Вам понравилась услуга? Поделитесь мнением: [ССЫЛКА]",
            # "Подарок упакован! Хотим узнать ваше мнение об услуге :) [ССЫЛКА]",
            "Подарок упакован! Ответьте, пожалуйста, на вопрос (это важно). [ВОПРОС]. И будем рады, если поделитесь общим впечатлением!",
            "Подарок упакован! Хотим узнать ваше мнение :) [ВОПРОС]",
            "Подарок упакован! Скажите, пожалуйста, [ВОПРОС] И будем рады, если поделитесь общим впечатлением, это важно для нас :)"
        ]

        question_ridge_models_probabilities = [33, 33, 33]

        question_options = [
            "Какие у вас впечатления от упакованного подарка? Будет здорово, если поделитесь фото",
            "Мы стараемся делать упаковочную бумагу плотной, прочной и красивой — как бы вы оценили результат? :)",
            "Что вы думаете о работе упаковщика? Нам важно знать, за что его стоит похвалить или сделать замечание.",
            "Мы расширяем ассортимент. Может, у вас есть пожелания по дизайну упаковочной бумаги?",
            "Что вы думаете о дизайне упаковки, о рисунке?",
            "Мы за приветливость и дружелюбие :) Скажите, приятно ли вам было общаться с упаковщиком?",
            "Что вы думаете о скорости упаковки подарка?",
            "Работаем над скоростью обслуживания. Скажите, долго ли вы ждали очереди? Что вы думаете о скорости работы упаковщика?"
        ]

        question_options_probabilities = [20, 20, 20, 10, 10, 10, 5, 5]

        question_chosen_ridge = random.choices(question_ridge_models, question_ridge_models_probabilities)[0]
        question_chosen_option = random.choices(question_options, question_options_probabilities)[0]

        generated_question = question_chosen_ridge.replace("[ВОПРОС]", question_chosen_option)
        return generated_question


    # --- State constructor ---

    Stage.set_common_statistics([StageStatsVisitCount()])
    User.set_common_statistics([UserStatsVisitCount(),
                                UserStatsCurrentStage()])

    _scope = Scope([

        Stage(name="NewUser",
              user_input_actions=[ActionChangeStage("AfterOrderQuestion")]),

        Stage(name="AfterOrderQuestion",
              message=Message(
                  text=lambda _, __: generate_after_order_question(_, __)),
              user_input_actions=lambda _, __: random.choices(
                  [[ActionChangeStage("QuestionAnsweredFinish")],
                   [ActionChangeStage("QuestionAnsweredOneMoreQuestion")]],
                  weights=[30, 70])[0]),

        Stage(name="QuestionAnsweredFinish",
              message=Message(
                  text="Спасибо, что помогаете нам стать лучше! "
                       "Уверены, человек, для которого вы подготовили подарок, "
                       "будет счастлив его получить :) "
                       "Прекрасного вам дня!"
              )),

        Stage(name="QuestionAnsweredOneMoreQuestion",
              message=Message(
                  text="Если ваш близкий человек или знакомый будет искать сервис по упаковке, "
                       "вы порекомендуете нас?",
                  keyboard=MessageKeyboard(
                      buttons=[
                          MessageKeyboardButton(
                              text="Да",
                              actions=[ActionChangeStage("QuestionAnsweredOneMoreQuestionPositive")]),
                          MessageKeyboardButton(
                              text="Нет",
                              actions=[ActionChangeStage("QuestionAnsweredOneMoreQuestionNegative")])
                      ],
                      is_non_keyboard_input_allowed=False))
              ),

        Stage(name="QuestionAnsweredOneMoreQuestionPositive",
              message=Message(
                  text="Спасибо! Уверены, человек, для которого вы подготовили подарок, "
                       "будет счастлив его получить :) Прекрасного вам дня!")),

        Stage(name="QuestionAnsweredOneMoreQuestionNegative",
              message=Message(
                  text="Почему? Нам важно это знать, чтобы стать лучше"),
              user_input_actions=[ActionChangeStage("QuestionAnsweredOneMoreQuestionPositive")])

    ], main_stage_name="MainMenu")
    logging.info("Program started")

    # SheetsClient(os.environ['sheets_token']).synchronize()
    # LocalBrandSheetClient(os.environ['local_brand_sheet_token']).synchronize()

    # worker = Worker()
    # worker.generate_goods_files()

    bot = Bot(os.environ['telegram_token'], _scope)

    databaseDaemon = UpdateDatabaseDaemon(bot)
    databaseDaemon.start_daemon()

    if os.environ['startup_mode'] == "webhook":
        logging.info("Starting using webhook")
        bot.start_webhook(port=8443,
                          server_ip=os.environ['server_ip'],
                          sertificate_path=os.environ['certificate_path'],
                          key_path=os.environ['key_path'])
    else:
        logging.info("Starting using polling")

        bot.start_polling(poll_interval=2,
                          poll_timeout=1)
