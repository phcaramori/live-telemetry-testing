import random
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
from flask import Flask
from flask_socketio import SocketIO, emit
import threading

#co-authored by a lot of chat-gpt so beware

"""
Very similar to live.py, but uses a websocket server instead of the default dash HTTP connections 

Basically:
- other thread updates data on its own and on its separate frequency, living its own life
- Browser 'CLIENT_SIDE_REFRESH_RATE' runs out, so it sends "data-collect-interval" to the script.  
- Script receives this and immediately replies with two separate responses, one to update text and another to update graphs.
Every cycle, 2 POST requests are made. Unlike the example on live.py, the datapoints are NOT sent back to the script.
"""

# CONSTANTS:
MAX_NUM_DATAPOINTS = 30 # Number of max datapoints before graph begins sliding left
CLIENT_SIDE_REFRESH_RATE = 1000 # How often the client rendering refreshes in ms.
SERVER_SIDE_REFRESH_RATE = 1000 # How often the server refreshes (in this example, generates new data) in ms.
#-----------

server = Flask(__name__)
app = Dash(__name__, server=server)
# Initialize SocketIO for Flask
socketio = SocketIO(server)

# Create Flask-SocketIO route that handles new data being sent to the client
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

app.layout = html.Div([
    html.H4('🎉COLUMBIA FSAE🎉'),
    html.Div(id='live-update-text'),
    dcc.Graph(id='live-update-graph'),
    dcc.Interval(id='data-collect-interval', interval=CLIENT_SIDE_REFRESH_RATE, n_intervals=0)
])

#actual data is stored in these variables:
randArr = []
countArr = []
count = 0

# Background data collection process
def background_data_collection():
    global count
    while True:
        randArr.append(random.random())
        countArr.append(count)
        count += 1
        socketio.sleep(SERVER_SIDE_REFRESH_RATE / 1000)  # Simulates data arriving every x seconds
        # Emit only the new data to all connected clients
        socketio.emit('data_update', {'random_val': randArr[-1], 'count': countArr[-1]})



# Dash callback for updating text
@app.callback(
    Output('live-update-text', 'children'),
    [Input('data-collect-interval', 'n_intervals')]
)
def update_text(n):
    return f'Latest Count: {countArr[-1]}, Latest Random Val: {randArr[-1]}'

# Dash callback for updating graph(s)
@app.callback(
    Output('live-update-graph', 'figure'),
    [Input('data-collect-interval', 'n_intervals')]
)
def update_graph_live(n):
    dataframe = pd.DataFrame({
        'Random Val': randArr,
        'Count': countArr,
    })
    graph = px.line(dataframe, x='Count', y='Random Val')
    if len(countArr) > MAX_NUM_DATAPOINTS:
        graph.update_layout(
            xaxis=dict(range=[countArr[-MAX_NUM_DATAPOINTS], countArr[-1]])
        )
    return graph

# Start the background data collection in a separate thread
if __name__ == '__main__':
    data_thread = threading.Thread(target=background_data_collection)
    data_thread.daemon = True
    data_thread.start()
    socketio.run(server, debug=True, allow_unsafe_werkzeug=True)