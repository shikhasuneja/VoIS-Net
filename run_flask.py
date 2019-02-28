from flask import *
import os

app = Flask(__name__)
'''
#<img src="C:\\Users\\nidhu250\\sem3\\midterm\\image1.png">
@app.route('/',methods=['GET','POST'])
def index():
    return send_file('image1.png', mimetype='image/gif')
'''

@app.route('/',methods=['GET','POST'])
def index(): 
    response='''
    <!DOCTYPE html>
    <html>
        <head>
            <title> Plot</title>
            <meta content='5; url=http://172.16.3.15' http-equiv='refresh'>
        </head>
        <body>
            <img src="/static/topology.png">
        </body>
    </html>'''
    
    return(response)


def main():
    app.debug=True
    app.run(host='172.16.3.15',port=80,threaded=True)

    
main()
