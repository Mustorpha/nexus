from django.shortcuts import render
from bokeh.embed import components
from .bokeh_app import chat_interface

# Generate the script and div for the Bokeh application
script, div = components(chat_interface.get_root())

# Create your views here.

def chat(request):
    return render(request, "chat/bokeh_app.html", {'script': script, 'div': div})
