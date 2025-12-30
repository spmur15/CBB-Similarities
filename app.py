from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table
import dash
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go



from similarity import (
    enter_player,
    enter_team,
    enter_position,
    browse_compatibility,
    get_matchup_detail, 
    STYLE_COLS, 
    STAT_COLS
)


POSITION_ORDER = [
    'PG', 's-PG', 'CG', 'WG', 'WF', 'S-PF', 'PF/C', 'C'
]

POSITION_LABELS = {
    "PG": "Pure PG",
    "s-PG": "Scoring PG",
    "CG": "Combo Guard",
    "WG": "Wing Guard",
    "WF": "Wing Forward",
    "S-PF": "Stretch Forward",
    "PF/C": "PF/C",
    "C": "Center",
}

POSITION_ORDER = [
    'Guard', 'Wing', 'Big'
]

POSITION_LABELS = {
    "Guard": "Guard",
    "Wing": "Wing",
    "Big": "Big"
}

POSITION_OPTIONS = [
    {"label": POSITION_LABELS[p], "value": p}
    for p in POSITION_ORDER
]



# -------------------------------------------------
# LOAD DATA (placeholder – adjust as needed)
# -------------------------------------------------
all_player_df = pd.concat([pd.read_csv('all_player_stats_1.csv'), pd.read_csv('all_player_stats_2.csv')],axis=0)

all_player_df = all_player_df.loc[all_player_df['off_poss']>350]

all_player_df['year'] = ('20' + all_player_df['year'].str[5:].astype(str)).astype(int)
all_player_df['conf'] = all_player_df['conf'].str.replace(" Conference", "").str.strip()
all_player_df = all_player_df.loc[~all_player_df['posClass'].str.contains('\?')]
names = all_player_df['player_name'].str.split(', ', expand=True)

power_conf = all_player_df.loc[all_player_df['conf'].isin(['Big Ten', 'Big 12', 'Atlantic Coast', 'Southwest', 'Pac-12', 'Big East']), 'team']

pos_map = {'PG':'Guard',
           's-PG':'Guard',
           'CG':'Guard',
           'WG':'Wing',
           'WF':'Wing',
           'S-PF':'Wing',
           'PF/C':'Big',
           'C':'Big'}

all_player_df['posClass'] = all_player_df['posClass'].map(pos_map)

CURRENT_SEASON = 2026

players_2026 = (
    all_player_df
    .query("year == @CURRENT_SEASON")
    #.sort_values("player_name")
)

player_2026_options = [
    {"label": p, "value": p}
    for p in players_2026["player_name"].unique()
]

STAT_LABEL_MAP = {
    "off_ftr": "FTR",
    "off_twoprimr": "Rim Rate",
    "off_threepr": "3PAr",
    "off_assist": "AST%",
    "off_to":"TOV%",
    "off_orb": "ORB%",
    "def_orb": "DRB%",
    "def_blk": "BLK%",
    "def_stl": "STL%",
    "off_usage": "Usage%",
}


# -------------------------------------------------
# APP SETUP (MUST COME FIRST)
# -------------------------------------------------
app = Dash(
    __name__,
    title = 'CBB Similarity',
    external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css"
    ],
    suppress_callback_exceptions=True
)

server = app.server



# -------------------------------------------------
# Helpers
# -------------------------------------------------
def fit_label(score):
    if score >= 0.90:
        return "Very strong"
    elif score >= 0.75:
        return "Strong"
    elif score >= 0.60:
        return "Somewhat strong"
    elif score >= 0.45:
        return "Decent"
    elif score >= 0.3:
        return "Somewhat poor"
    else:
        return "Poor"


def similarity_gauge(value, title, height=180, font_size=28):
    return go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={
                "font": {"size": font_size},
                "valueformat": ".3f"
            },
            title={"text": title,
                   "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, 1]},
                "bar": {"color": "#969696",
                        "line":{"width": 1.5},
                        "thickness":0.25},
                'threshold': {
                    #'line': {'color': "#818181", 'width': 4},
                    'thickness': 0.7,
                    "line":{"width": 1.5},
                    'value': value},
                "steps": [
                    {"range": [0, 0.33], "color": "#f8d7da"},
                    {"range": [0.33, 0.67], "color": "#fff3cd"},
                    {"range": [0.67, 0.9], "color": "#d1ecf1"},
                    {"range": [0.9, 1.0], "color": "#d4edda"},
                ],
            },
        )
    ).update_layout(
        height=height,
        margin=dict(t=40, b=10, l=10, r=10)
    )

def pretty_label(col):
    """
    off_style_attack_kick_pct -> Attack Kick
    """
    label = col

    # remove prefixes
    label = label.replace("off_style_", "")
    label = label.replace("off_", "")
    label = label.replace("_pct", "")

    # underscores → spaces, Title Case
    label = label.replace("_", " ").title()

    return label

def pretty_style_label(col):
    return (
        col
        .replace("off_style_", "")
        .replace("_pct", "")
        .replace("_", " ")
        .title()
    )

def format_stat_label(col):

    key = col.lower()
    #print(key)
    if key in STAT_LABEL_MAP:
        return STAT_LABEL_MAP[key]

    # fallback: clean + title-case
    return (
        col
        .replace("off_", "")
        .replace("def_", "")
        .replace("_", " ")
        .title()
    )



# -------------------------------------------------
# NAVBAR
# -------------------------------------------------

def nav_label(mobile_top, mobile_bottom=None, desktop=None):
    return html.Span([
        # Mobile (stacked)
        html.Span(
            [
                html.Div(mobile_top),
                html.Div(mobile_bottom) if mobile_bottom else None
            ],
            className="d-inline d-md-none text-c",
            style={"lineHeight": "1.1", "fontSize": "12px"}
        ),

        # Desktop (single line)
        html.Span(
            desktop or mobile_top,
            className="d-none d-md-inline"
        )
    ])


def navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("CBB Player-Team Similarity", className="fw-bold"),

                dbc.Nav(
                    [
                        dbc.NavLink(
                            html.Div(["Similarity", html.Br(), "Pairs"]),
                            href="/matchup",
                            active="exact",
                            className="nav-item-stack"
                        ),
                        dbc.NavLink(
                            html.Div(["Enter", html.Br(), "Teams"]),
                            href="/team",
                            active="exact",
                            className="nav-item-stack"
                        ),
                        dbc.NavLink(
                            html.Div(["Enter", html.Br(), "Players"]),
                            href="/player",
                            active="exact",
                            className="nav-item-stack"
                        ),
                        dbc.NavLink(
                            html.Div(["Browse", html.Br(), "Pairs"]),
                            href="/browse",
                            active="exact",
                            className="nav-item-stack"
                        ),
                        dbc.NavLink(
                            html.I(className="bi bi-info-circle"),
                            href="/about",
                            active="exact",
                            className="nav-item-icon"
                        ),
                    ],
                    className="mobile-nav",
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
    )


# -------------------------------------------------
# PAGE LAYOUTS
# -------------------------------------------------
def position_layout():
    return html.Div([
        html.H4("Position Explorer"),
        html.Hr(style={"opacity": 0.3}),
        dcc.Dropdown(
            id="pos-position",
            options=[{"label": p, "value": p}
                     for p in ['PG', 's-PG', 'CG', 'WG', 'WF', 'S-PF', 'PF/C', 'C']],#sorted(all_player_df["posClass"].unique())],
            placeholder="Select position"
        ),
        html.Br(),
        dbc.Spinner(dcc.Loading(id="position-table"))
    ])

def player_layout():
    return html.Div([
        html.H4("Player → Teams"),
        html.Hr(style={"opacity": 0.3}),
        dcc.Dropdown(
            id="player-name",
            options=player_2026_options,
            placeholder="Select player",
            clearable=False,
            style={"boxShadow": "0 6px 18px rgba(0,0,0,0.14)"},
        ),

        html.Br(),

        dbc.Spinner(dcc.Loading(id="player-results"))
    ])


def team_layout():
    return html.Div([
        html.H4("Team → Players"),
        html.Hr(style={"opacity": 0.3}),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Team", className="fw-bold"),
                        dcc.Dropdown(
                            id="team-name",
                            options=[
                                {"label": t, "value": t}
                                for t in sorted(power_conf)
                            ],
                            placeholder="Select team",
                            style={"boxShadow": "0 6px 18px rgba(0,0,0,0.14)"},
                        ),
                    ],
                    xs=12, md=5, lg=4
                ),

                dbc.Col(
                    [
                        html.Label("Position", className="fw-bold"),
                        dcc.Dropdown(
                            id="team-pos",
                            options=POSITION_OPTIONS,
                            placeholder="Select position",
                            style={"boxShadow": "0 6px 18px rgba(0,0,0,0.14)"},
                        ),
                    ],
                    xs=12, md=5, lg=4,
                    className="mt-2 mt-md-0"  # 👈 spacing only when stacked
                ),
            ],
            justify="center",
            className="g-3"
        ),

        html.Br(),

        dbc.Spinner(dcc.Loading(id="team-results"))
    ])


def matchup_layout():
    return html.Div([
        html.H4("Player ↔ Team"),
        html.Div("Select a player and team to see similarity details. This may take up to 30 seconds."),
        html.Hr(style={"opacity": 0.3}),
        dbc.Row(
            [ 
                dbc.Col([
                    html.Label("Player", className="fw-bold"),
                    dcc.Dropdown(
                        id="matchup-player",
                        options=player_2026_options,
                        placeholder="Select player (2026)",
                        clearable=False,
                        style={"boxShadow": "0 6px 18px rgba(0,0,0,0.14)"},
                    )],
                    xs=12, md=5, lg=4
                ),
                dbc.Col([
                    html.Label("Team", className="fw-bold"),
                    dcc.Dropdown(
                        id="matchup-team",
                        options=[
                            {"label": t, "value": t}
                            for t in sorted(all_player_df["team"].unique())
                        ],
                        placeholder="Select team",
                        clearable=False
                    )],
                    xs=12, md=5, lg=4
                ),
            ],
            justify="center",
            className="g-3"  # responsive gap
        ),

        html.Br(),

        html.Div(id="matchup-summary", className="mb-3"),

        dbc.Tabs(
            [
                dbc.Tab(label="Style", tab_id="style"),
                dbc.Tab(label="Stats", tab_id="stats"),
            ],
            id="matchup-tabs",
            active_tab="style"
        ),

        dcc.Graph(id="matchup-bar-chart")
    ])



def about_layout():
    return html.Div([
        html.H4("About This Tool"),
        html.Hr(style={"opacity": 0.3}),
        html.P("This app evaluates stylistic and statistical similarity between college basketball players and team systems."),
        html.P("Scores are based on position-specific PCA embeddings of style and stat profiles."),
        html.P("Data source: Hoop-Explorer.com")
        
    ])

def browse_layout():
    return html.Div([
        html.H4("Similarity Browser"),
        html.Hr(style={"opacity": 0.3}),

        html.P(
            "Explore the strongest player–team similarities across college basketball. "
            "This analysis may take up to 1-2 minutes to run.",
            className="text-muted"
        ),

        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id="browse-pos",
                    options=POSITION_OPTIONS,
                    placeholder="Select position",
                    style={"boxShadow": "0 6px 18px rgba(0,0,0,0.14)"},
                ),
                xs=12, md=5, lg=4
            ),
            html.Br(),

            dbc.Col(
                dbc.Button(
                    "Run Analysis",
                    id="browse-run",
                    color="primary",
                    n_clicks=0,
                    className="mt-2 mt-md-0"
                ),
                width="auto"
            ),
        ], align="center"),

        html.Br(),

        dbc.Spinner(
            html.Div(id="browse-results"),
            color="primary"
        )
    ])


# -------------------------------------------------
# APP LAYOUT
# -------------------------------------------------
app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Store(id="selected-matchup", storage_type="session"),
    html.Div(id="navbar"),
    html.Div(id="page-content", style={"padding": "16px"}),
    html.Br(),
    html.Hr(style={"opacity": 0.3}),
    html.Br()
])

# -------------------------------------------------
# CALLBACKS
# -------------------------------------------------



#####
##### App Set Up
#####
@app.callback(
    Output("navbar", "children"),
    Input("url", "pathname")
)
def render_navbar(_):
    return navbar()

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def route_page(pathname):
    if pathname == "/browse":
        return browse_layout()
    elif pathname == "/player":
        return player_layout()
    elif pathname == "/team":
        return team_layout()
    elif pathname == "/matchup":
        return matchup_layout()
    elif pathname == "/about":
        return about_layout()
    else:
        return team_layout()  # default

@app.callback(
    Output("url", "pathname"),
    Input("selected-matchup", "data"),
    prevent_initial_call=True
)
def go_to_matchup(_):
    return "/matchup"




#####
##### Enter Player
#####

@app.callback(
    Output("player-results", "children"),
    Input("player-name", "value")
)
def update_player_results(player_name):
    if not player_name:
        return html.Div("Select a player to see similar teams. This may take up to 1-2 minutes.")

    df = enter_player(player_name)

    return dash_table.DataTable(
        id="player-teams-table",
        data=df.to_dict("records"),
        columns=[
            {"name": "Team", "id": "team"},
            {"name": "Score", "id": "score", "type": "numeric", "format": {"specifier": ".3f"}},
            {"name": "Style", "id": "style_sim", "type": "numeric", "format": {"specifier": ".3f"}},
            {"name": "Stats", "id": "stat_sim", "type": "numeric", "format": {"specifier": ".3f"}},
        ],
        sort_action="native",
        row_selectable="single",
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={
            "padding": "8px",
            "fontFamily": "sans-serif",
            "fontSize": "14px"
        },
        # style_header={
        #     "fontWeight": "bold",
        #     "backgroundColor": "#f8f9fa"
        # },
        style_as_list_view=True,
        style_data={
        'color': 'black',
        'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#cfd9e8',
            }
        ],
        style_header={
            'backgroundColor': '#c3d2e6',
            'color': 'black',
            'fontWeight': 'bold'
        },
    )

@app.callback(
    Output("selected-matchup", "data"),
    Input("player-teams-table", "selected_rows"),
    State("player-teams-table", "data"),
    State("player-name", "value"),
    prevent_initial_call=True
)
def select_team_for_player(selected_rows, table_data, player_name):
    if not selected_rows:
        raise PreventUpdate

    row = table_data[selected_rows[0]]

    # infer position from player
    pos_class = (
        all_player_df
        .query("player_name == @player_name")
        .sort_values("year", ascending=False)
        .iloc[0]["posClass"]
    )

    return {
        "player": player_name,
        "team": row["team"],
        "posClass": pos_class
    }




#####
##### Enter Team
#####
@app.callback(
    Output("team-results", "children"),
    Input("team-name", "value"),
    Input("team-pos", "value")
)
def update_team_results(team_name, pos_class):
    if not team_name or not pos_class:
        return html.Div("Select a team and position to see similar players. This may take up to 30 seconds.")

    df = enter_team(team_name, pos_class)

    return dash_table.DataTable(
        id="team-players-table",
        data=df.to_dict("records"),
        columns=[
            {"name": "Player", "id": "player_name"},
            {"name": "Current Team", "id": "player_team"},
            {"name": "Score", "id": "score", "type": "numeric", "format": {"specifier": ".3f"}},
            {"name": "Style", "id": "style_sim", "type": "numeric", "format": {"specifier": ".3f"}},
            {"name": "Stats", "id": "stat_sim", "type": "numeric", "format": {"specifier": ".3f"}},
        ],
        sort_action="native",
        row_selectable="single",
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={
            "padding": "8px",
            "fontFamily": "sans-serif",
            "fontSize": "14px"
        },
        # style_header={
        #     "fontWeight": "bold",
        #     "backgroundColor": "#f8f9fa"
        # },
        style_as_list_view=True,
        style_data={
        'color': 'black',
        'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#cfd9e8',
            }
        ],
        style_header={
            'backgroundColor': '#c3d2e6',
            'color': 'black',
            'fontWeight': 'bold'
        },
    )

@app.callback(
    Output("selected-matchup", "data", allow_duplicate=True),
    Input("team-players-table", "selected_rows"),
    State("team-players-table", "data"),
    State("team-name", "value"),
    State("team-pos", "value"),
    prevent_initial_call=True
)
def select_player_for_team(selected_rows, table_data, team_name, pos_class):
    if not selected_rows:
        raise PreventUpdate

    row = table_data[selected_rows[0]]

    return {
        "player": row["player_name"],
        "team": team_name,
        "posClass": pos_class
    }



#####
##### Enter Position
#####

@app.callback(
    Output("browse-results", "children"),
    Input("browse-run", "n_clicks"),
    State("browse-pos", "value"),
    prevent_initial_call=True
)
def run_browse(n_clicks, pos_class):
    if not pos_class:
        return html.Div("Select a position before running the analysis.")

    df = browse_compatibility(pos_class)

    if df.empty:
        return html.Div("No results found for this position.")

    return dash_table.DataTable(
        id="browse-table",
        data=df.to_dict("records"),
        columns=[
            {"name": "Player", "id": "player"},
            {"name": "Player Team", "id": "player_team"},
            {"name": "Target Team", "id": "target_team"},
            {"name": "Score", "id": "score", "type": "numeric",
             "format": {"specifier": ".3f"}},
            {"name": "Style", "id": "style_sim", "type": "numeric",
             "format": {"specifier": ".3f"}},
            {"name": "Stats", "id": "stat_sim", "type": "numeric",
             "format": {"specifier": ".3f"}},
        ],
        sort_action="native",
        page_size=20,
        row_selectable="single",
        style_table={"overflowX": "auto"},
        style_cell={
            "padding": "8px",
            "fontFamily": "sans-serif",
            "fontSize": "14px"
        },
        
        style_data={
        'color': 'black',
        'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#cfd9e8',
            }
        ],
        style_header={
            'backgroundColor': '#c3d2e6',
            'color': 'black',
            'fontWeight': 'bold'
        },
        style_as_list_view=True,
    )

@app.callback(
    Output("selected-matchup", "data", allow_duplicate=True),
    Input("browse-table", "selected_rows"),
    State("browse-table", "data"),
    State("browse-pos", "value"),
    prevent_initial_call=True
)
def select_from_browse(selected_rows, table_data, pos_class):
    if not selected_rows:
        raise PreventUpdate

    row = table_data[selected_rows[0]]

    return {
        "player": row["player"],
        "team": row["target_team"],
        "posClass": pos_class
    }


#####
##### Matchup
#####

@app.callback(
    Output("matchup-summary", "children"),
    Input("selected-matchup", "data")
)
def update_matchup_summary(data):
    if not data:
        return html.Div("Select a player–team pairing to view details.")

    detail = get_matchup_detail(
        player=data["player"],
        team=data["team"],
        pos_class=data["posClass"]
    )

    s = detail["scores"]

    label = fit_label(s["score"])

    return dbc.Card(
        dbc.CardBody([
            # ---- Header ----
            html.Div(
                [
                    html.H4(
                        f'{data["player"]} ↔ {data["team"]}',
                        className="mb-1",
                        style={"textAlign": "center"}
                    ),
                    html.Div(
                        f'Position: {data["posClass"]}',
                        className="text-muted",
                        style={"textAlign": "center"}
                    ),
                    html.Div(
                        "Comparison is against players at the same position within the team’s system.",
                        className="text-muted",
                        style={
                            "textAlign": "center",
                            "fontSize": "13px",
                            "marginTop": "4px",
                            "marginBottom": "0px"
                        }
                    ),
                ],
                className="mb-3",
                style={
                            "textAlign": "center",
                            "marginTop": "0px",
                            "marginBottom": "0px"
                        }
            ),
            
            #html.Br(),

            # ---- Overall gauge ----
            dcc.Graph(
                figure=similarity_gauge(
                    s["score"],
                    f"Overall Similarity - {label}",
                    height=160,
                    font_size=30
                ),
                config={"displayModeBar": False},
                style={"marginTop": "40px"}
            ),
            html.Br(),

            # ---- Style + Stat gauges ----
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            figure=similarity_gauge(
                                s["style_sim"],
                                "Style Sim.",
                                height=135,
                                font_size=22
                            ),
                            config={"displayModeBar": False}
                        ),
                        width=6
                    ),
                    dbc.Col(
                        dcc.Graph(
                            figure=similarity_gauge(
                                s["stat_sim"],
                                "Stat Sim.",
                                height=140,
                                font_size=24
                            ),
                            config={"displayModeBar": False}
                        ),
                        width=6
                    ),
                ]
            ),
        ]),
        style={
            "borderRadius": "16px",
            "boxShadow": "0 6px 18px rgba(0,0,0,0.14)",
            "padding": "8px"
        },
    )


@app.callback(
    Output("matchup-bar-chart", "figure"),
    Input("selected-matchup", "data"),
    Input("matchup-tabs", "active_tab")
)
def update_matchup_chart(data, tab):
    if not data:
        return go.Figure()

    detail = get_matchup_detail(
        player=data["player"],
        team=data["team"],
        pos_class=data["posClass"]
    )

    player_row = detail["player_row"]
    team_vec   = detail["team_vec"]

    if tab == "style":
        cols = STYLE_COLS
        y_labels = [
            c.replace("off_style_", "")
            .replace("_pct", "")
            .replace("_", " ")
            .title()
            for c in cols
        ]
        title = "Offensive Style Profile"

    else:
        cols = STAT_COLS
        y_labels = [format_stat_label(c) for c in cols]
        title = "Statistical Tendencies"


    player_vals = player_row[cols].values
    team_vals = [team_vec[c] for c in cols]

    pos = data["posClass"]

    subtitle_text = (
        f"Team styles & stats are taken among players<br>from the team with the target<br>"
        f"position ({pos}) from 2022–2026."
    )

    



    fig = go.Figure()

    pretty_cols = [pretty_label(c) for c in cols]

    y_pos = list(range(len(cols)))
    #y_labels = [pretty_style_label(c) for c in cols]

    fig.add_bar(
        y=y_labels,
        x=player_vals,
        orientation="h",
        name=data["player"],
        marker_color="#93BAD5"
    )

    fig.add_bar(
        y=y_labels,
        x=team_vals,
        orientation="h",
        name=data["team"],
        marker_color="#DF9693"
    )

    fig.update_yaxes(
        tickmode="array",
        tickvals=y_pos,
        ticktext=y_labels,
        autorange="reversed"  # keeps top-to-bottom order
    )




    fig.update_layout(
        title=dict(
            text=title,
            x=0,
            xanchor="left",
            font=dict(
                size=20,
                color="#2c3e50",
                family="system-ui"
            ),
        ),

        title_subtitle=dict(
            text=subtitle_text.replace("—", "<br>"),
            font=dict(
                size=13,
                color="#6c757d"
            ),
        ),

        margin=dict(l=20, r=20, t=90, b=30),

        legend=dict(
            orientation="h",
            x=0,
            xanchor="left",
            y=1.02
        ),

        barmode="group",
    )

    # --- X-axis formatting (conditional) ---
    if tab == "style":
        xaxis_cfg = dict(
            tickformat=".0%",          # or ".1%" if you want decimals
            title=dict(
                text="% of possessions",
                font=dict(size=13),
                standoff=10
            )
        )
    else:
        xaxis_cfg = dict(
            title=dict(
                text="Value",
                font=dict(size=13),
                standoff=10
            ),
            tickformat=".0%" 
        )



    fig.update_layout(
        barmode="group",
        height=450,

        # ⬇️ This is what actually prevents overlap
        yaxis=dict(
            automargin=True,
            ticks="outside",
            domain=[0.0, 0.88]   # 👈 reserve top 18% for title/subtitle
        ),

        xaxis=xaxis_cfg,

        margin=dict(
            l=20,
            r=20,
            t=80,   # keep generous top margin
            b=30
        ),

        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.18,              # 👈 pushes legend below chart
            xanchor="center",
            yanchor="top",
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=14)
        ),

        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    fig.update_yaxes(
        showline=True,
        linecolor="#818181",
        linewidth=1,
        showgrid=False,        # no horizontal grid
        ticks="outside",
        autorange="reversed"
    )

    fig.update_xaxes(
        showline=False,
        linecolor="#d0d0d0",
        linewidth=1,
        showgrid=True,                     # vertical gridlines
        gridcolor="rgba(0,0,0,0.08)",      # very light grey
        gridwidth=1,

        zeroline=False,
    )



   

        





    return fig


@app.callback(
    Output("matchup-player", "value"),
    Output("matchup-team", "value"),
    Input("selected-matchup", "data"),
)
def populate_matchup_dropdowns(data):
    if not data:
        return None, None

    return data["player"], data["team"]


@app.callback(
    Output("selected-matchup", "data", allow_duplicate=True),
    Input("matchup-player", "value"),
    Input("matchup-team", "value"),
    prevent_initial_call=True
)
def update_matchup_from_dropdowns(player, team):
    if not player or not team:
        raise PreventUpdate

    pos_class = (
        all_player_df
        .query("player_name == @player")
        .sort_values("year", ascending=False)
        .iloc[0]["posClass"]
    )

    return {
        "player": player,
        "team": team,
        "posClass": pos_class
    }






if __name__ == "__main__":
    app.run_server(debug=True)
