"""
Demonstrates how to use the `ChatInterface` to create two bots that chat with each
other.
"""
from django.conf import settings

import panel as pn
import openai

pn.extension()


async def callback(
    contents: str,
    user: str,
    instance: pn.chat.ChatInterface,
):
    if user in ["User", "Happy Bot"]:
        callback_user = "Nerd Bot"
        callback_avatar = ""
    elif user == "Nerd Bot":
        callback_user = "Happy Bot"
        callback_avatar = ""

    prompt = f"Think profoundly about {contents}, then ask a question."
    response = await aclient.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        max_tokens=250,
        temperature=0.1,
    )
    message = ""
    async for chunk in response:
        part = chunk.choices[0].delta.content
        if part is not None:
            message += part
            yield {"user": callback_user, "avatar": callback_avatar, "object": message}

    if len(instance.objects) % 6 == 0:  # stop at every 6 messages
        instance.send(
            "That's it for now! Thanks for chatting!", user="System", respond=False
        )
        return
    instance.respond()

aclient = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
chat_interface = pn.chat.ChatInterface(callback=callback)
chat_interface.send(
    "Enter a topic for the bots to discuss! Beware the token usage!",
    user="System",
    respond=False,
)
chat_interface.servable()

