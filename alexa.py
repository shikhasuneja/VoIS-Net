from flask import Flask
from flask_ask import Ask, statement, question, session
from network_visualization import visualize_topology
import json, subprocess
import requests
import time

app = Flask(__name__)
ask = Ask(app, "/capstone")

@app.route("/")
def homepage():
   return "hi there, how ya doin?"

@ask.launch
def start_skill():
   welcome_message = 'Hello there, would you like to see the topology?'
   return question(welcome_message)


@ask.intent("YesIntent")
def share_headlines():
   hi_text = 'GREAT! Here it is'
   
   visualize_topology()


   return statement(hi_text)
   headlines = get_headlines()


@ask.intent("NoIntent")
def no_intent():
   bye_text = 'I am not sure why you asked me to run then, but okay... bye'
   return statement(bye_text)


if __name__ == '__main__':
   app.run(debug=True)

