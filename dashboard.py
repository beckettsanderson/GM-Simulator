# import libraries
from dash import Dash, dcc, html, Input, Output, State, dash_table, ctx
import dash
import dash_daq as daq
import pandas as pd
import plotly.graph_objects as go
import team_projections as tp
import data_cleaning as dc
import warnings
import scraping as sc

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

# Set salary to NFL salary adjusted to the number of players being chosen
SALARY = 150

# Download player data and features data
PLAYERS = '2022_players.csv'
FEATURES = 'position_features.csv'


def read_csv(file):
    """
    Reads in a csv file and returns a dataframe

    Parameters
    ----------
    file : csv file
        file containing some data

    Returns
    -------
    df : dataframe
        dataframe holding data from the file
    """
    df = pd.read_csv(file)
    df = dc.remove_empty(df)
    return df


# Reads in the player data, cleans the positions and salaries
player_df = read_csv(PLAYERS)

# clean data
player_df = dc.condense_positions(player_df)
player_df = dc.convert_salaries(player_df)

# Adds a column to the dashboard to add or drop a gives player
player_df.insert(loc=0, column='Status', value='ADD')

# Adds a dropdown to select the position of the players you want to see
dropdown = sc.scrape_column_names()
dropdown = [x for x in dropdown if x['value'] in list(player_df.columns)
            and x['value'] not in dc.initial_player_view(player_df).columns]

# read csv for radar chart
features_df = read_csv(FEATURES)

# read in data for teams
team_df = pd.DataFrame(columns=dc.initial_player_view(player_df).columns)
team_df.drop('Status', axis=1)

# Define the dashboard and layout
app = Dash(__name__)

# Define the dashboard layout
app.layout = html.Div(
    children=[

        html.Div([

            # Creates a header and subheader for the dashboard
            html.H1('NFL General Manager Simulator',
                    style={'text-align': 'center', 'font-family': 'Freshman', 'font-size': '300%'}),

            html.H3("Draft a Team", style={'text-align': 'center', 'font-size': '210%'}),

            # Generates an LED display to show the remaining salary
            # Display salary
            daq.LEDDisplay(
                id='salary_display',
                label={'label': 'Salary'},
                value=SALARY,
                color="#92e0d3",
                backgroundColor="#1e2130",
                size=20
                ,
            ),

            html.H3("Player Statistics", style={'text-align': 'center', 'font-size': '210%'}),

            # Creates the datatable or players and stats on the dashboard
            dash_table.DataTable(
                id='datatable-interactivity',
                columns=[
                    {"name": i, "id": i, 'deletable': False, 'selectable': False} for i in
                    dc.initial_player_view(player_df).columns if i != 'id'
                ],
                data=player_df.to_dict('records'),
                style_data={
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                fill_width=False,

                # change color depending on if they're on the team
                style_data_conditional=(
                        [
                            {
                                'if': {
                                    'column_id': 'Status',
                                    'filter_query': '{Status} contains "ADD"'
                                },
                                'backgroundColor': 'green',
                                'color': 'white',
                            }
                        ] +
                        [
                            {
                                'if': {
                                    'column_id': 'Status',
                                    'filter_query': '{Status} contains "REMOVE"'
                                },
                                'backgroundColor': 'red',
                                'color': 'white',
                            }
                        ]
                ),
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                page_action="native",
                page_current=0,
                page_size=15,
            ),
            html.Div([
                # dropdown of player positions so user can filter players by position
                dcc.Dropdown(
                    options=['ALL', 'QB', 'RB', 'WR', 'OL', 'TE', 'DL', 'LB', 'CB', 'S', 'K', 'P'],
                    value='ALL',
                    id="pos_dropdown",
                    style={"width": '100%'}

                ),
                # dropdown of player stats so user can filter what stats they want to see
                dcc.Dropdown(
                    options=dropdown,
                    multi=True,
                    placeholder="Select Statistics",
                    style={"width": '100%'},
                    id="stat_dropdown",

                ),
            ], style=dict(display='flex')),

            html.Br(),
            html.Div(id='datatable-interactivity-container'),

            # Radar chart and football field vis
            html.Div([dcc.Graph(id='radar', style={'display': 'inline-block'}),
                      dcc.Graph(id="scatter-plot", style={'display': 'inline-block'})]),

            # input to see stats of player by their ID
            dcc.Input(id="id_input", type="number", placeholder=0),

            # input to see stats of another player by their ID (for comparison)
            dcc.Input(id="opp_input", type="number", placeholder=0),

            # Submit button to refresh radar chart based on which players are being examined
            html.Button(id='id_button', type='submit', children='Submit'),
        ]),

        html.Div([

            html.H2("Team Statistics", style={'text-align': 'center'}),

            # data table for selected team
            dash_table.DataTable(
                id='team_datatable',
                columns=[
                    {"name": i, "id": i, 'deletable': False, 'selectable': False} for i in
                    dc.initial_player_view(team_df).columns if i != 'id'
                ],
                data=team_df.to_dict('records'),
                style_data={
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                fill_width=False,
                style_data_conditional=(
                        [
                            {
                                'if': {
                                    'column_id': 'Status',
                                    'filter_query': '{Status} contains "ADD"'
                                },
                                'backgroundColor': 'green',
                                'color': 'white',
                            }
                        ] +
                        [
                            {
                                'if': {
                                    'column_id': 'Status',
                                    'filter_query': '{Status} contains "REMOVE"'
                                },
                                'backgroundColor': 'red',
                                'color': 'white',
                            }
                        ]
                ),
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                page_action="native",
                page_current=0,
                page_size=15,
            ),
        ]),
        html.Br(),

        # Creates the submit button to view the predicted number of wins for a team
        html.Div([

            # button to submit team
            html.Button('Submit Team', id='button',
                        style={'height': '40px', 'text-allign': 'center', 'width': '300px',
                               'margin': 'auto', 'padding': '10px'}),
        ], style=dict(display='flex')),

        # Displays the number of wins for the team in an LED box
        html.Div([

            html.H2("Team Comparisons", style={'text-align': 'center'}),

            # Show the number of wins in your season
            daq.LEDDisplay(
                id='wins_display',
                label={'label': 'Wins in Your Season (out of 16 games)!'},
                value=0,
                color="#92e0d3",
                backgroundColor="#1e2130",
                size=20,
            ),
        ])

    ])


# Callback for making modifications to the data table in the dashboard
@app.callback(
    Output("datatable-interactivity", "data"),
    Output("datatable-interactivity", "columns"),
    Input("pos_dropdown", "value"),
    Input('team_datatable', 'data'),
    Input("stat_dropdown", "value"),
    prevent_initial_call=True
)
def modify_table(dropdown_val, team_data, dropdown_lst):
    """
    Catch all function for modifying data table (since we can have one callback per output).
    """
    triggered_id = ctx.triggered_id
    # if dropdown changed, call position function
    if triggered_id == 'pos_dropdown':
        return mod_pos(dropdown_val)
    # if team changed, call modify button function
    elif triggered_id == 'team_datatable':
        return modify_button(dropdown_val)
    elif triggered_id == "stat_dropdown":
        if dropdown_val != "ALL":
            return mod_stat(dropdown_lst, dropdown_val)
        else:
            return mod_stat(dropdown_lst)


def mod_stat(lst, *args):
    """
    Modifies stats and returns a dictionary of the data and a dictionary of the columns
    """
    # create new dataframe copies
    pos_df = player_df.copy()
    temp_df = player_df.copy()

    # check if it is sorted by position
    if args:
        # sort by position
        alt_df = pos_df[pos_df.Pos == args[0]]
        alt_df = dc.remove_empty(alt_df)

        # new dataframe with columns selected
        new_stats = player_df[lst]

        # combine dataframes
        new_df = pd.concat([alt_df, new_stats], axis=1)

        # return dataframe as dictonary
        data = new_df.to_dict('records')
        columns = [
            {"name": i, "id": i, "deletable": False, "selectable": False} for i in new_df.columns
        ]
        return data, columns
    else:
        # keep global stats
        main_stats = pos_df[['Status', 'Player', 'Pos', 'Team', 'Age', 'No.', 'Cap Hit']]

        # new dataframe with columns selected
        new_stats = temp_df[lst]

        # combine dataframes
        new_df = pd.concat([main_stats, new_stats], axis=1)

        # return dataframe as dictionary
        data = new_df.to_dict('records')
        columns = [
            {"name": i, "id": i, "deletable": False, "selectable": False} for i in new_df.columns
        ]
        return data, columns


def mod_pos(value):
    """
    Adjust the displayed table data to the selected position filter
    """

    pos_df = player_df.copy()

    if value == 'ALL':
        # get the data for all players and set up the initial view
        pos_df = dc.initial_player_view(pos_df)

        # update the data and columns based on the position
        data = pos_df.to_dict('records')
        columns = [
            {"name": i, "id": i, "deletable": False, "selectable": False} for i in pos_df.columns
        ]
        return data, columns

    else:
        # get the players and data for only the selected position
        alt_df = pos_df[pos_df.Pos == value]
        alt_df = dc.remove_empty(alt_df)

        # update the data and columns based on the position
        data = alt_df.to_dict('records')
        columns = [
            {"name": i, "id": i, "deletable": False, "selectable": False} for i in alt_df.columns
        ]
        return data, columns


def modify_button(pos):
    """
    Change status button for all players in our team to 'REMOVE'
    """
    # get team player ids
    global team_df, player_df
    ids = team_df.loc[:, 'id']

    # set all ids to add, then change to 'REMOVE' by our team ids
    player_df['Status'] = 'ADD'
    for id in ids:
        player_df.loc[id, 'Status'] = 'REMOVE'

    # keep current datatable the same based on filtered position
    if pos != 'ALL':
        data = player_df[player_df.Pos == pos].to_dict('records')
    else:
        data = player_df.to_dict('records')
    return data, dash.no_update


@app.callback(
    Output("radar", "figure"),
    State("id_input", "value"),
    State("opp_input", "value"),
    Input("id_button", "n_clicks"),
    Input("pos_dropdown", "value")
)
def update_radar(id_input, opp_input, n_clicks, pos_dropdown):
    """
    Updates the radar chart as needed
    :param id_input: the ID of the player whose stats the user wants to examine
    :param opp_input: the ID of the second player whose stats the user wants to examine
    :param n_clicks: number of times the button has been clicked. Updates when n_clicks has changed
    :param pos_dropdown: the position the user is filtering by
    :return: a radar chart comparing the statistics between two players
    """
    global player_df

    # if n_clicks greater than zero, plot players onto radar chart
    if n_clicks:

        # create a list of features to be graphed, specifically the features which pertain to the position selected
        position_list = features_df[features_df.position == pos_dropdown].features_list.iloc[0].split(', ')
        position_df = player_df[player_df["Pos"] == pos_dropdown]

        # for every feature in the position, take the values, and acquire the maximum, and append to ranges. Ranges is
        # an upper bound value of the radar chart
        for feature in position_list:
            position_df[feature] = position_df[feature].astype(str)
            position_df[feature] = position_df[feature].str.rstrip("%").astype(float) / 100
        max_df = position_df[position_list].max()
        ranges = []
        for feature in position_list:
            ranges.append(max_df[feature])

        # get stats and name of the selected player
        select_df = player_df[player_df["id"] == id_input]
        name1 = select_df.loc[id_input, 'Player']

        # for every feature, get the values from that player
        for feature in position_list:
            select_df[feature] = select_df[feature].astype(str)
            select_df[feature] = select_df[feature].str.rstrip("%").astype(float) / 100
        select_df = select_df.apply(pd.to_numeric, errors='ignore')
        select_df = select_df[position_list]
        # set r to a list of stats of the selected player
        r = select_df.values.tolist()[0]

        # scale the values in relation to the maximum value, so for low number stats there is visible difference
        # between the two players
        for rng in range(len(ranges)):
            r[rng] = r[rng] / ranges[rng]

        # apply same steps to the opposing selected player
        # gets stats of the selected player
        select2 = player_df[player_df["id"] == opp_input]
        name2 = select2.loc[opp_input, 'Player']
        # for every feature, get the values from that player
        for feature in position_list:
            select2[feature] = select2[feature].astype(str)
            select2[feature] = select2[feature].str.rstrip("%").astype(float) / 100
        select2 = select2.apply(pd.to_numeric, errors='ignore')
        select2 = select2[position_list]
        # set r2 to a list of stats of the selected player
        r2 = select2.values.tolist()[0]

        # scale the values in relation to the maximum value, so for low number stats there is visible difference
        # between the two players
        for rng in range(len(ranges)):
            r2[rng] = r2[rng] / ranges[rng]

        # create scatter plot, and plot the values of the first player
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            theta=position_list,
            r=r,
            fill='toself',
            name=name1
        ))
        # plot the values of the second player
        fig.add_trace(go.Scatterpolar(
            theta=position_list,
            r=r2,
            fill='toself',
            name=name2
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True
                ),
            ),
            showlegend=False
        )

    # if n_clicks is zero, plot a blank radar chart to halt errors
    else:
        fig = go.Figure(
            data=go.Scatterpolar(
                r=[0, 0, 0, 0, 0],
                theta=['', '', '', '', ''],
                fill='toself',
            )
        )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    showticklabels=False
                ),
            ),
            showlegend=False,
            title_text='SELECT PLAYERS TO COMPARE'
        )

    return fig


@app.callback(
    Output('team_datatable', 'data'),
    Output('salary_display', 'value'),
    Input('datatable-interactivity', "active_cell"),
    Input('salary_display', 'value'),
    Input('team_datatable', 'active_cell')
)
def add_players(cell, salary, team_cell):
    """
    Function to add players to the team
    Does not allow to break salary cap
    Updates the team_df on the dashboard
    """

    # check if change was in table or team table
    if ctx.triggered_id == 'team_datatable':
        cell = team_cell

    # check if user clicked status column
    if cell and cell['column_id'] == 'Status':
        # get player data
        row_id = cell['row_id']
        status = player_df.loc[row_id, 'Status']
        sel_player = player_df.loc[row_id].to_frame().T
        player_sal = float(sel_player['Cap Hit'].values[0].replace('$', '').replace('m', ''))

        # check if we're adding or removing a player, update table and salaries
        global team_df
        salaries = sum([float(x.replace('$', '').replace('m', '')) for x in list(team_df['Cap Hit'].values)])
        if status == 'ADD':
            if SALARY - salaries - player_sal < 0:
                pass
            else:
                team_df = pd.concat([team_df, sel_player], axis=0)
                salary = SALARY - salaries - player_sal
        elif status == 'REMOVE':
            team_df.drop(row_id, axis=0, inplace=True)
            salary = SALARY + player_sal - salaries

        # set all team_df players to remove
        team_df['Status'] = 'REMOVE'

        return team_df.to_dict('records'), round(salary, 1)

    else:
        return dash.no_update, dash.no_update


@app.callback(
    Output("scatter-plot", "figure"),
    Input("team_datatable", "data")
)
def update_bar_chart(data):
    """
    :param data: the data of the team the user has selected
    :return: a bar chart which shows the players the user has selected, where the color indicates if they have selected
    enough players
    """
    # create a new dictionary which contains the number of players per position that properly assembles a team
    pos_range = {}
    for i in dc.POS_COUNTS.values():
        for key, value in i.items():
            pos_range[key] = value

    # pos_loc dictionary contains the coordinates of where each player should be placed
    pos_loc = {
        'QB': [5.5, 8],
        'RB': [[6, 7.5]],
        'WR': [[9, 9], [10, 9], [2, 9]],
        'OL': [[3.5, 9], [4.5, 9], [5.5, 9], [6.5, 9], [7.5, 9]],
        'TE': [8, 9],
        'DL': [[3.5, 11], [4.5, 11], [6.5, 11], [7.5, 11], [5.5, 11]],
        'LB': [[4, 12], [7, 12], [5.5, 12]],
        'CB': [[9.5, 11], [2, 11]],
        'S': [[3.5, 14], [7.5, 14]],
        'K': [1, 5],
        'P': [1, 4]
    }
    # create new lists which will contain the coordinates, colors, labels, symbol shape of each player
    x_list = []
    y_list = []
    color_list = []
    label_list = []
    symbols = []
    counter_list = []

    # create new list which contains a list of the number of players per position (positions can repeat)
    position_count = []
    for player in data:
        position_count.append(player["Pos"])

    # get number of players per position
    for key, value in pos_loc.items():
        player_count = position_count.count(key)
        # if player count is less than the max value of the range, and a count of a defensive position, remove a coord
        if player_count == (len(pos_loc[key]) - 1) and key in ["DL", "LB", "CB", "S"]:
            pos_loc[key].pop(len(pos_loc[key]) - 1)

        # if number of players for position less than acceptable range, have the color yellow
        if player_count < min(pos_range[key]):
            color = "yellow"
        # if greater than acceptable range, have color red
        elif player_count > max(pos_range[key]):
            color = "red"
        # if in range set to cyan
        else:
            color = "cyan"

        # if the number of sets of coordinates is 2 and the first element is not a 2D list (or list), then do not
        # iterate through coordinates! Add x coords, y coords, etc.
        if type(value[0]) != list and len(value) == 2:
            color_list.append(color)
            x_list.append(value[0])
            y_list.append(value[1])
            label_list.append(key)
            # iterate through keys in POS_COUNTS and assign a shape based on if the position is offense, defense, or
            # none
            for side, values in dc.POS_COUNTS.items():
                for pos_key in values.keys():
                    if key == pos_key:
                        if side == "Offense":
                            symbols.append("x")
                        elif side == "Defense":
                            symbols.append("circle-open")
                        else:
                            symbols.append("square")

        # if you iterate through multiple coordinates in a 2d list, do the same as above for each set of coords
        else:
            for coord in value:
                color_list.append(color)
                x_list.append(coord[0])
                y_list.append(coord[1])
                label_list.append(key)
                for side, values in dc.POS_COUNTS.items():
                    for pos_key in values.keys():
                        if key == pos_key:
                            if side == "Offense":
                                symbols.append("x")
                            elif side == "Defense":
                                symbols.append("circle-open")
                            else:
                                symbols.append("square")

    # remove numbers from x-axis
    layout = go.Layout(
        xaxis=go.XAxis(
            showticklabels=False),
    )

    # create a scatter plot
    fig = go.Figure(data=go.Scatter(
        x=x_list,
        y=y_list,
        mode='markers',
        marker=dict(color=color_list,
                    symbol=symbols),
        hovertemplate='<br><b>%{text}</b>\n' + '<extra></extra>',
        text=label_list,
        showlegend=False
    ), layout=layout)

    # add line of scrimmage to football field
    fig.add_shape(type="line",
                  x0=1,
                  y0=10,
                  x1=10,
                  y1=10,
                  line=dict(
                      color="White",
                      width=2,
                  ))

    # add perimeter lines for special teams players
    fig.add_shape(type="line",
                  x0=0,
                  y0=6,
                  x1=2,
                  y1=6)
    fig.add_shape(type="line",
                  x0=2,
                  y0=6,
                  x1=2,
                  y1=2)

    # update layout and axis
    fig.update_layout(showlegend=False, plot_bgcolor='rgb(0,204,0)',
                      title="Your current team! Hover over players to examine their position!",
                      xaxis_title="Yellow = Add More Players, Red = Remove Players, Cyan = All Good!")

    fig.update_yaxes(visible=False)

    return fig


@app.callback(
    Output('wins_display', 'value'),
    Input('team_datatable', 'data'),
    Input('button', 'n_clicks'),
    prevent_initial_call=True
)
def update_machinelearning(team_dict, n_clicks):
    """ Button press to calculate the wins with the selected team"""
    triggered_id = ctx.triggered_id
    team_data = pd.DataFrame.from_dict(team_dict)

    # if dropdown changed, call position function
    if triggered_id == 'button':
        return min(max(tp.analyze_team(team_data), 0), 16)


# Run the Dash server
app.run_server(debug=True)
