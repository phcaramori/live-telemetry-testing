import datetime
import random
import pandas
from dash import Dash, dcc, html, Input, Output, callback
from threading import Thread
import time
import plotly.express as px

"""
Look at websocket-test-live.py. It seems to be a better alternative to this.

The way this works is a separate thread is assigned to get new values and store them to a global variable. 
This is done on a set interval. Completely separate to this, each client has its OWN set interval, which, when 
triggered, makes it request a new graph/page from the server. AFAIK, there is no way to "push" this update from the
server to the device, meaning all devices will be slightly out of sync, but always by less than the update value, which
can be very low (<1 s). The frequency at which data is received and stored CAN BE DIFFERENT. 

Basically:
- other thread updates data on its own and on its separate frequency, living its own life
- Browser 'CLIENT_SIDE_REFRESH_RATE' runs out, so it sends "data-collect-interval" to the script.  
- Script receives this and replies with "shared-data-update", sending the new data to the client. POST over.
- Client recieves this and makes a new POST request, "shared-data-update". 
- TWO Callbacks on the script pick this up, and send TWO SEPERATE responses, one to update text, another to update graphs.
Every cycle, 3 post requests are made.
Now, this may be bad for bandwith, since every datapoint, like all of them, 
"""


# CONSTANTS:
MAX_NUM_DATAPOINTS = 30 # Number of max datapoints before graph begins sliding left
CLIENT_SIDE_REFRESH_RATE = 1000 # How often the client rendering refreshes in ms.
SERVER_SIDE_REFRESH_RATE = 1000 # How often the server refreshes (in this example, generates new data) in ms.
#-----------

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css'] #External CSS

app = Dash(__name__)
app.layout = html.Div( #This controls the HTML code displayed on the website
    html.Div([
        html.H4('🎉COLUMBIA FSAE🎉'),
        html.Div(id='live-update-text'),
        dcc.Graph(id='live-update-graph'),
        dcc.Interval( #defines interval
            id='data-collect-interval',
            interval=CLIENT_SIDE_REFRESH_RATE, # in milliseconds of CLIENT-SIDE refresh
            n_intervals=0 #variable that stores num of intervals passed
        ),
        dcc.Store(id='shared-data-update')
    ])
)

# Background thread for server-side updates
randArr = []
countArr = []
count = 0

def update_data_in_background():
    global randArr, countArr, count
    while True:
        randArr.append(random.random())
        countArr.append(count)
        count += 1
        time.sleep(SERVER_SIDE_REFRESH_RATE/1000)  # Update data every 1 seconds

# Start the background thread
thread = Thread(target=update_data_in_background)
thread.daemon = True
thread.start()
#multi-threaded since background updates must run separately. Main thread is not non-blocking since it
#is constantly listening to client callbacks.



# Callback to store data in dcc.Store so it's available to all clients
@app.callback(
    Output('shared-data-update', 'data'),
    Input('data-collect-interval', 'n_intervals')
)
def update_shared_data(n):
    # Ensure that this function doesn't modify the data, just return it
    global randArr, countArr
    # Return the current state of the arrays
    return {
        'randArr': randArr,
        'countArr': countArr
    }

#Callback to update the text display
@app.callback(
    Output('live-update-text', 'children'),
    Input('shared-data-update', 'data')
)
def update_text(n):
    return f'Latest Count: {countArr[-1]}, Latest Random Val: {randArr[-1]}'

# Callback to update the graph
@app.callback(
    Output('live-update-graph', 'figure'),
    Input('shared-data-update', 'data')
)
def update_graph(n):
    data = random.random() # Collect some data
    dataframe = pandas.DataFrame({
        'Random Val': randArr,
        'Count': countArr,
    })
    graph = px.line(dataframe, x='Count', y='Random Val') #Create line graph
    # Display only last 'MAX_NUM_DATAPOINTS' points of data
    if len(countArr) > MAX_NUM_DATAPOINTS:
        graph.update_layout(
            xaxis=dict(range=[countArr[-MAX_NUM_DATAPOINTS], countArr[-1]])
        )

    return graph

if __name__ == '__main__':
    app.run(debug=False)