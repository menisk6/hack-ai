import copy
import re
from typing import Any, Dict, List

from langchain.chains.base import Chain
from langchain.llms import BaseLLM
from langchain_core.prompts import ChatPromptTemplate

from deepinfra import ChatDeepInfra

llm = ChatDeepInfra(temperature=0.7)

class HelpGPT(Chain):
    """Controller model for the Sales Agent."""

    salesperson_name: str = "Роман"
    salesperson_role: str = "Интеллектуальный помощник технической поддержки"
    company_name: str = "RuTube"
    company_business: str = "RuTube - российский онлайн-сервис для хостинга и просмотра видео"
    conversation_type: str = "чат мессенджера"
    knowladge_base: str = '''Пользователь: Здравствуйте! Можно уточнить причины Правил https://rutube.ru/info/taboo_agreement/ по которым удаляются ролики? что за нарушение правил RUTUBE
{salesperson_name}: "Добрый день!
Что нельзя публиковать на RUTUBE:
- Чужой контент без разрешения автора или правообладателя. Например, музыку, видео и изображения из общего доступа, записи концертов, фильмов, аудиокниги, фрагменты новостных сюжетов из ТВ-эфиров, видео популярных блогеров, трансляции спортивных событий.
- Рекламу трансцендентных услуг. Например, рекламу гаданий, услуг ясновидящих, экстрасенсов и т. д.
- Откровенно сексуальный контент. Например, танцы в откровенных костюмах, рекламу интим-товаров или сексуальных услуг. 
- Рекламу букмекеров, проведение ставок и пропаганду любых азартных игр. 
- Рекламу или продвижение финансовых пирамид и сетевого маркетинга (MLM), преподнесение их в качестве надёжного источника заработка.  
- Нецензурную брань, оскорбления, подстрекательства к незаконным действиям. 
- Контент, который нацелен только на перенаправление зрителей на другие сайты. 
- Контент иностранных агентов или о них без специальной маркировки.
Больше информации есть по ссылкам: 
https://rutube.ru/info/taboo_agreement/
https://rutube.ru/info/socially_important/
https://rutube.ru/info/adverguide/
https://rutube.ru/info/content/'''
    # current_conversation_stage: str = "1"
    # conversation_stage: str = "Введение. Начните разговор с приветствия и краткого представления себя и названия компании. Поинтересуйтесь, в чём проблема пользователя"

    # conversation_stage_dict: dict = {
    #     "1": "Введение. Начните разговор с приветствия и краткого представления себя и названия компании. Поинтересуйтесь, в чём проблема пользователя",
    #     "2": "Уточнения. Уточните у пользователя что именно у него случилось",
    #     "3": "Решение. Решите проблему пользователя опираясь на используемую базу знаний",
    #     "4": "Итог. Поинтересуйтесь у пользователя, помогли ли вы решить его проблему",
    #     "5": "Оператор. Если пользователь требует связать его с человеком (оператором), вежливо ответь чтобы немного подождал"
    # }

    analyzer_history: list = []
    analyzer_history_template: list = [("system", """Ты - помощник, который разделяет вопрос и ответ на определённую заранее известную категорию.
Вот перечисление категорий:
1. МОДЕРАЦИЯ
2. МОНЕТИЗАЦИЯ
3. УПРАВЛЕНИЕ АККАУНТОМ
4. ДОСТУП К RUTUBE
5. ПРЕДЛОЖЕНИЯ
6. ВИДЕО
7. ТРАНСЛЯЦИЯ
8. СОТРУДНИЧЕСТВО ПРОДВИЖЕНИЕ РЕКЛАМА
9. ПОИСК
10. БЛАГОТВОРИТЕЛЬНОСТЬ ДОНАТЫ 
11. ОТСУТСТВУЕТ

Твоя основная задача: Написать название одной из данных категорий, в зависимости от вопроса и ответа которые тебе будут переданы.
Ты можешь писать только названия категорий так, как они написаны выше, больше ничего другого писать нельзя.
Если вопрос и ответ не попадает от определённую категорию, относи его в категорию ОТСУТСТВУЕТ""")]

#     analyzer_system_postprompt_template: list = [("system", """Отвечайте только цифрой от 1 до 5, чтобы лучше понять, на каком этапе следует продолжить разговор.
# Ответ должен состоять только из одной цифры, без слов.
# Если истории разговоров нет, выведите 1.
# Больше ничего не отвечайте и ничего не добавляйте к своему ответу.

# Текущая стадия разговора:
# """)]

    conversation_history: list = []
    conversation_history_template: list = [("system", """Никогда не забывайте, что ваше имя {salesperson_name}, вы мужчина. Вы работаете {salesperson_role}. Вы работаете в компании под названием {company_name}. Бизнес {company_name} заключается в следующем: {company_business}.
Вы впервые связываетесь в {conversation_type} с одним пользователем с целью ответить на его вопрос и попытаться решить проблему используя базу знаний.

Все, что написано дальше вы не можете сообщать собеседнику.
Вы всегда очень вежливы и говорите только на русском языке! Делайте свои ответы короткими и максимально похожими на эталонные ответы из базы знаний.
Составляй списки с ответами только если они есть в базе знаний.
Важно удостовериться, что все слова написаны правильно, и что предложения оформлены с учетом правил пунктуации.
Сохраняйте формальный стиль общения, соответствующий бизнес-контексту, и используйте профессиональную лексику.
Вы должны ответить в соответствии с историей предыдущего разговора и информацией из базы знаний.

Вот несколько эталонных примеров ответов на вопрос:
Пользователь: Что сделать, чтобы использовать в видео материалы, которые распространяются по свободной лицензии?
{salesperson_name}: Вам необходимо предоставить ссылку на страницу, где указаны однозначные условия такой лицензии на использование этого материала.                                                                                        

Пользователь: Что может делать Модератор комментариев в cтудии?
{salesperson_name}: Пользователь с ролью "Модератор комментариев" может размещать и модерировать комментарии от имени канала, ставить реакции и управлять комментариями других пользователей в разделе "Комментарии": https://studio.rutube.ru/comments.

Примеры того, что вам нельзя писать:
{salesperson_name}: Я не знаю как Вам помочь
{salesperson_name}: Вы можете посмотреть решение в интернете
""")]

    conversation_system_postprompt_template: list = [("system", """Отвечай только на русском языке.
Пиши только русскими буквами.

Обязательно ответь на следующий вопрос использую данный диалог как базу знаний:
{knowladge_base}                                                                                                           
""")]
# Текущая стадия разговора:
# {conversation_stage}

    @property
    def input_keys(self) -> List[str]:
        return []

    @property
    def output_keys(self) -> List[str]:
        return []

    # def retrieve_conversation_stage(self, key):
    #     return self.conversation_stage_dict.get(key, '1')

    def seed_agent(self):
        # self.current_conversation_stage = self.retrieve_conversation_stage('1')
        self.analyzer_history = copy.deepcopy(self.analyzer_history_template)
        # self.analyzer_history.append(("user", "Привет"))
        self.conversation_history = copy.deepcopy(self.conversation_history_template)
        # self.conversation_history.append(("user", "Привет"))

    def human_step(self, human_message):
        # self.analyzer_history.append(("user", human_message))
        self.conversation_history.append(("user", human_message))

    def ai_step(self, topics, API = False):
        # print(topics)
        if topics[0]["distance"] > 1:
            if API:
                self.conversation_history.append(("assistant", 'Извините, в моей базе нет ответа на Ваш запрос'))
            else:
                self.conversation_history.pop()
            return "Извините, в моей базе нет ответа на Ваш запрос"
            
        else:
            self.knowladge_base = r"\n\n".join([("Вопрос: " + faq["Вопрос"] + r"\n" + "Ответ: " + faq["Ответ"]) for faq in topics])
            # print(self.knowladge_base)
            return self._call(topics, API)
        

    def analyse_stage(self):
        print("История:  ", self.conversation_history)
        messages = self.analyzer_history + [('user'), r"\n".join([item['role'] + ": " + item["content"] for item in self.conversation_history[-1:-3]])]
        template = ChatPromptTemplate.from_messages(messages)
        messages = template.format_messages()

        response = llm.invoke(messages)
        self.conversation_history.pop()
        self.conversation_history.pop()
        # print(response.content)
        return response.content 

        # self.current_conversation_stage = self.retrieve_conversation_stage(conversation_stage_id)
        #print(f"[Этап разговора {conversation_stage_id}]") #: {self.current_conversation_stage}")

    def _call(self, topics: List[Any], API = False) -> None:
        messages = self.conversation_history + self.conversation_system_postprompt_template
        template = ChatPromptTemplate.from_messages(messages)
        messages = template.format_messages(
            salesperson_name = self.salesperson_name,
            salesperson_role = self.salesperson_role,
            company_name = self.company_name,
            company_business = self.company_business,
            knowladge_base = self.knowladge_base,
            conversation_type = self.conversation_type,
        )

        response = llm.invoke(messages)
        # print(response.content)
        ai_message = (response.content).split('\n')[0]
        if API:
            self.conversation_history.append(("assistant", ai_message))
        else:
            self.conversation_history.pop()
        # self.analyzer_history.append(("user", ai_message))
        

        return ai_message

    @classmethod
    def from_llm(
        cls, llm: BaseLLM, verbose: bool = False, **kwargs
    ) -> "HelpGPT":
        """Initialize the HelpGPT Controller."""

        return cls(
            verbose = verbose,
            **kwargs,
        )