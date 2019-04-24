from flask import Flask
from flask_ask import Ask, statement, question, session
from network_visualization import visualize_topology
from self_healing import heal_my_network
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
   welcome_message = 'Hello there, what would you like to do?'
   return question(welcome_message)

'''
@ask.intent("YesIntent")
def share_headlines():
   hi_text = 'GREAT! Here it is'
   visualize_topology()

   return statement(hi_text)
'''

@ask.intent("Topology")
def share_headlines():
   hi_text = 'GREAT! Here is the topology'
   visualize_topology()
   return statement(hi_text)

@ask.intent("Healing")
def share_headlines():
   hi_text = 'Detected and resolved network issues'
   heal_my_network() 
   return statement(hi_text)



@ask.intent("NoIntent")
def no_intent():
   bye_text = 'I am not sure why you asked me to run then, but okay... bye'
   return statement(bye_text)


if __name__ == '__main__':
   app.run(debug=True)

