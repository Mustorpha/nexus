from dataclasses import dataclass
import sys
from typing import Dict, List, Optional, Union
from autogen import Agent, ConversableAgent, GroupChat
import logging


class GroupChatManagerWeb(ConversableAgent):
    """(In preview) A chat manager agent that can manage a group chat of multiple agents."""

    def __init__(
        self,
        groupchat: GroupChat,
        name: Optional[str] = "chat_manager",
        max_consecutive_auto_reply: Optional[int] = sys.maxsize,
        human_input_mode: Optional[str] = "NEVER",
        system_message: Optional[str] = "Group chat manager.",
        **kwargs,
    ):
        super().__init__(
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            system_message=system_message,
            **kwargs,
        )
        self.register_reply(Agent, GroupChatManagerWeb.run_chat, config=groupchat, reset_config=GroupChat.reset)
    async def run_chat(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[GroupChat] = None,
    ) -> Union[str, Dict, None]:
        """Run a group chat."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        speaker = sender
        groupchat = config
        for i in range(groupchat.max_round):
            if message["role"] != "function":
                message["name"] = speaker.name
            groupchat.messages.append(message)
            for agent in groupchat.agents:
                if agent != speaker:
                    self.send(message, agent, request_reply=False, silent=True)
            if i == groupchat.max_round - 1:
                break
            try:
                speaker = groupchat.select_speaker(speaker, self)
                reply = await speaker.a_generate_reply(sender=self)
            except KeyboardInterrupt:
                if groupchat.admin_name in groupchat.agent_names:
                    speaker = groupchat.agent_by_name(groupchat.admin_name)
                    reply = await speaker.a_generate_reply(sender=self)
                else:
                    raise
            if reply is None:
                break
            speaker.send(reply, self, request_reply=False)
            message = self.last_message(speaker)
        return True, None
