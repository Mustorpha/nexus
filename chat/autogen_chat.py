from django.conf import settings

from .user_proxy_webagent import UserProxyWebAgent
from .groupchatweb import GroupChatManagerWeb

import asyncio
import json
import autogen

config_list = [
    {
        "model": "gpt-3.5-turbo",
        "api_key": settings.OPENAI_KEY,
    }
]
llm_config = {
    "model":"gpt-3.5-turbo",
    "temperature": 0,
    "config_list": config_list,
    "cache_seed": None,
}

class AutogenChat():
    def __init__(self, websocket=None):
        self.websocket = websocket
        self.client_sent_queue = asyncio.Queue()

        self.researcher = autogen.AssistantAgent(
            name="Researcher",
            system_message="You are a researcher for a team, you will make research base on the discussion in your team.",
            llm_config=llm_config
        )
        self.researcher.register_reply(
            [autogen.Agent, None],
            reply_func=self.print_messages,
            config={"callback": None},
        )

        self.advisor = autogen.AssistantAgent(
            name="Advisor",
            system_message="You are an advisor for a team, you will make suggestion for the team base on the discussion in your team.",
            llm_config=llm_config
        )
        self.advisor.register_reply(
            [autogen.Agent, None],
            reply_func=self.print_messages,
            config={"callback": None},
        )

        self.Admin = UserProxyWebAgent( 
            name="admin",
            human_input_mode="ALWAYS",
            system_message="""You are the admin of a team, you will interact wisely with your members to solve the user's problem""",
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config=False,
            websocket=websocket
        )

    async def print_messages(self, recipient, messages, sender, config):
        if "callback" in config and config["callback"] is not None:
            callback = config["callback"]
            callback(sender, recipient, messages[-1])
        message = messages[-1].get("content")
        author = messages[-1].get("name", "Assistant")
        response = {
            "type": "send_message",
            "author": author,
            "message": message
            }
        await self.websocket.channel_layer.group_send(self.websocket.room_group_name, response)
        return False, None     

    async def start(self, message):
        self.groupchat = autogen.GroupChat(agents=[self.Admin, self.researcher, self.advisor], messages=[], max_round=10)
        self.manager = GroupChatManagerWeb(groupchat=self.groupchat, 
            llm_config=llm_config,
            human_input_mode="ALWAYS" )
        await self.Admin.a_initiate_chat(
            self.manager,
            message=message
        )

