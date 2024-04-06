import autogen
from autogen import Agent, ConversableAgent
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import asyncio
import json
try:
    from termcolor import colored
except ImportError:
    def colored(x, *args, **kwargs):
        return x



class UserProxyWebAgent(autogen.UserProxyAgent):
    def __init__(self, websocket, *args, **kwargs):
        super(UserProxyWebAgent, self).__init__(*args, **kwargs)
        self._reply_func_list = []
        self.register_reply([Agent, None], ConversableAgent.generate_oai_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], UserProxyWebAgent.a_check_termination_and_human_reply)
        self.websocket = websocket
        self.recur = False

    async def a_check_termination_and_human_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Check if the conversation should be terminated, and if human reply is provided."""
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        reply = ""
        no_human_input_msg = ""
        if self.human_input_mode == "ALWAYS":
            reply = await self.a_get_human_input(
                f"Provide feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
            )
            no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
            reply = reply if reply or not self._is_termination_msg(message) else "exit"
        else:
            if self._consecutive_auto_reply_counter[sender] >= self._max_consecutive_auto_reply_dict[sender]:
                if self.human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    terminate = self._is_termination_msg(message)
                    reply = await self.a_get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "
                        if terminate
                        else f"Please give feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to stop the conversation: "
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    reply = reply if reply or not terminate else "exit"
            elif self._is_termination_msg(message):
                if self.human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    reply = await self.a_get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    reply = reply or "exit"

        if no_human_input_msg:
            print(colored(f"\n>>>>>>>> {no_human_input_msg}", "red"), flush=True)

        if reply == "exit":
            self._consecutive_auto_reply_counter[sender] = 0
            return True, None

        if reply or self._max_consecutive_auto_reply_dict[sender] == 0:
            self._consecutive_auto_reply_counter[sender] = 0
            return True, reply

        self._consecutive_auto_reply_counter[sender] += 1
        if self.human_input_mode != "NEVER":
            print(colored("\n>>>>>>>> USING AUTO REPLY...", "red"), flush=True)

        return False, None

    async def a_get_human_input(self, prompt: str) -> str:
        last_message = self.last_message()
        if last_message["content"]:
            content = last_message["content"]
            role = last_message.get("role", "admin")
            response = {
               "type": "send_message",
               "author": "admin",
               "message": content
               }
            await self.websocket.channel_layer.group_send(self.websocket.room_group_name, response)
            self.recur = True
            reply = await self.websocket.autogen_chat.client_sent_queue.get()
            if reply and reply == "END":
                return "exit"
            return reply
        else:
            return
