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

power_conf = all_player_df.loc[all_player_df['conf'].isin(['Big Ten', 'Big 12', 'Atlantic Coast', 'Southwest', 'Pac-12', 'Big East']), 'team'].unique()

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
# LOAD PRECOMPUTED BROWSE TABLES
# -------------------------------------------------
BROWSE_TABLES = {
    "Guard": pd.read_parquet("assets//browse_guards.parquet"),
    "Wing":  pd.read_parquet("assets//browse_wings.parquet"),
    "Big":   pd.read_parquet("assets//browse_bigs.parquet"),
}

TEAM_CONF_LOOKUP = (
    all_player_df
    .groupby("team", as_index=True)["conf"]
    .first()
)

for pos, df in BROWSE_TABLES.items():
    df = df.copy()

    # --- add conferences ---
    df["player_conf"] = df["player_team"].map(TEAM_CONF_LOOKUP)
    df["target_conf"] = df["target_team"].map(TEAM_CONF_LOOKUP)

    # --- optional safety ---
    df["player_conf"] = df["player_conf"].fillna("Unknown")
    df["target_conf"] = df["target_conf"].fillna("Unknown")

    # --- rounding consistency ---
    BROWSE_TABLES[pos] = df.round(3)



# -------------------------------------------------
# BROWSE FILTER OPTIONS (derived once)
# -------------------------------------------------
ALL_BROWSE = pd.concat(BROWSE_TABLES.values(), ignore_index=True)

PLAYER_OPTIONS = sorted(ALL_BROWSE["player"].unique())
PLAYER_TEAM_OPTIONS = sorted(ALL_BROWSE["player_team"].unique())
TARGET_TEAM_OPTIONS = sorted(ALL_BROWSE["target_team"].unique())

PLAYER_CONF_OPTIONS = sorted(
    all_player_df.set_index("team").loc[PLAYER_TEAM_OPTIONS]["conf"].unique()
)

TARGET_CONF_OPTIONS = sorted(
    all_player_df.set_index("team").loc[TARGET_TEAM_OPTIONS]["conf"].unique()
)

# optional: ensure consistent rounding
for k, df in BROWSE_TABLES.items():
    BROWSE_TABLES[k] = df.round(3)


PLAYER_OPTIONS_BY_POS = {
    "Guard": sorted(
        all_player_df
        .query("posClass == 'Guard' and year == @CURRENT_SEASON")["player_name"]
        .unique()
    ),
    "Wing": sorted(
        all_player_df
        .query("posClass == 'Wing' and year == @CURRENT_SEASON")["player_name"]
        .unique()
    ),
    "Big": sorted(
        all_player_df
        .query("posClass == 'Big' and year == @CURRENT_SEASON")["player_name"]
        .unique()
    ),
}

PLAYER_OPTIONS_BY_POS = {
    pos: sorted(df["player"].unique())
    for pos, df in BROWSE_TABLES.items()
}

PLAYER_TEAM_OPTIONS_BY_POS = {
    pos: sorted(df["player_team"].unique())
    for pos, df in BROWSE_TABLES.items()
}

TARGET_TEAM_OPTIONS_BY_POS = {
    pos: sorted(df["target_team"].unique())
    for pos, df in BROWSE_TABLES.items()
}

PLAYER_CONF_OPTIONS_BY_POS = {
    pos: sorted(df["player_conf"].unique())
    for pos, df in BROWSE_TABLES.items()
}

TARGET_CONF_OPTIONS_BY_POS = {
    pos: sorted(df["target_conf"].unique())
    for pos, df in BROWSE_TABLES.items()
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
                dbc.NavbarBrand("CBB Similarity", className="fw-bold"),

                dbc.Nav(
                    [
                        dbc.NavLink(
                            html.Div(["Similarity", html.Br(), "Details"]),
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
        dbc.Row([
                dbc.Col(
                    [
                    dcc.Dropdown(
                        id="pos-position",
                        options=[{"label": p, "value": p}
                                for p in ['PG', 's-PG', 'CG', 'WG', 'WF', 'S-PF', 'PF/C', 'C']],#sorted(all_player_df["posClass"].unique())],
                        placeholder="Select position",
                        style={"boxShadow": "0 6px 18px rgba(0,0,0,0.14)"},
                    )],
                    # xs=6, md=3, lg=2,
                    # className="mt-2 mt-md-0"
                )
            ],
            justify="center",
            className="g-3"),
        html.Br(),
        dbc.Spinner(dcc.Loading(id="position-table"))
    ])

def player_layout():
    return html.Div(
        className="page-center",
        children=[
            html.Div(
                className="hero-box",
                children=[
                    html.H2("Find Player–Team Fits", className="hero-title"),
                    html.P(
                        "Select a player to see compatible teams.",
                        className="hero-subtitle"
                    ),
                    html.P(
                        "Selected player is compared with players from power-conference teams with the same position from 2022-2026.",
                        className="hero-subtitle"
                    ),

                    dcc.Dropdown(
                        id="player-name",
                        options=player_2026_options,
                        placeholder="Search for a player…",
                        clearable=False,
                        className="modern-dropdown"
                    ),
                ],
            ),

            html.Hr(className="mt-3 mb-4", style={"opacity": 0.15}),

            html.Div(
                className="results-wrapper",
                children=[
                    dbc.Spinner(dcc.Loading(id="player-results"))
                ]
            )
        ]
    )



def team_layout():
    return html.Div(
        className="page-center",
        children=[
            html.Div(
                className="hero-box",
                children=[
                    html.H2("Find Team–Player Fits", className="hero-title"),
                    html.P(
                        "Select a team and position to see compatible players.",
                        className="hero-subtitle"
                    ),
                    html.P(
                        "Players on the selected team among the selected position are compared with all current players (2025-26) in the selected position.",
                        className="hero-subtitle"
                    ),

                    dbc.Row(
                        className="g-3 justify-content-center",
                        children=[
                            dbc.Col(
                                dcc.Dropdown(
                                    id="team-name",
                                    options=[
                                        {"label": t, "value": t}
                                        for t in sorted(power_conf)
                                    ],
                                    placeholder="Select team…",
                                    className="modern-dropdown",
                                ),
                                xs=12, md=6
                            ),

                            dbc.Col(
                                dcc.Dropdown(
                                    id="team-pos",
                                    options=POSITION_OPTIONS,
                                    placeholder="Select position…",
                                    className="modern-dropdown",
                                ),
                                xs=12, md=6
                            ),
                        ]
                    ),
                ],
            ),

            html.Hr(className="mt-3 mb-4", style={"opacity": 0.15}),

            html.Div(
                className="results-wrapper",
                children=[
                    dbc.Spinner(dcc.Loading(id="team-results"))
                ]
            )
        ]
    )



def matchup_layout():
    return html.Div(
        className="page-center",
        children=[
            html.Div(
                className="hero-box hero-box-compact",
                children=[
                    html.H4("Player ↔ Team", className="hero-title-sm"),
                    html.P(
                        "Select a player and team to see similarity details. "
                        "This may take up to 30 seconds.",
                        className="hero-subtitle"
                    ),

                    dbc.Row(
                        className="g-2 justify-content-center",
                        children=[
                            dbc.Col(
                                dcc.Dropdown(
                                    id="matchup-player",
                                    options=player_2026_options,
                                    placeholder="Player (2026)…",
                                    clearable=False,
                                    className="modern-dropdown compact-dropdown",
                                ),
                                xs=12, md=5, lg=4
                            ),

                            dbc.Col(
                                dcc.Dropdown(
                                    id="matchup-team",
                                    options=[
                                        {"label": t, "value": t}
                                        for t in sorted(all_player_df["team"].unique())
                                    ],
                                    placeholder="Team…",
                                    clearable=False,
                                    className="modern-dropdown compact-dropdown",
                                ),
                                xs=12, md=5, lg=4
                            ),
                        ]
                    ),
                ],
            ),

            html.Hr(className="mt-3 mb-4", style={"opacity": 0.15}),

            html.Div(id="matchup-summary", className="mb-3"),

            dbc.Tabs(
                [
                    dbc.Tab(label="Style", tab_id="style"),
                    dbc.Tab(label="Stats", tab_id="stats"),
                ],
                id="matchup-tabs",
                active_tab="style"
            ),

            dcc.Graph(id="matchup-bar-chart"),
        ]
    )




def about_layout():
    return html.Div([
        html.H4("About This Tool"),
        html.Hr(style={"opacity": 0.3}),
        html.P(["This app uses data from ", 
                html.A(
                    "hoop-explorer.com",
                    href="https://hoop-explorer.com",
                    target="_blank",   # open in new tab
                    className="external-link"
                ),
                " to evaluates stylistic and statistical similarity between college basketball players and team systems."]),
        html.P("Similarity scores are based on PCA embeddings of style and stat profiles. Scores are between -1 and 1 and can be interpreted as:"),
        html.Div(
            [
                html.Strong("Similarity Scores"),
                html.Ul([
                    html.Li(".9 - 1 → Extremely similar"),
                    html.Li(".7 - .9 → Very similar"),
                    html.Li(".5 - .7 → Somewhat similar"),
                    html.Li(".2 - .5 → Some small similarities"),
                    html.Li(">.2 → Not similar"),
                ]),
            ],
        ),
        html.P("An example using Nick Townsend (wing) and UConn: similarity scores are drawn from UConn's wings over the desired subset of seasons and Nick Townsend in the 2025-26 season..."),
        html.Br(),
        html.H5("Styles"),
        html.P("Styles are the percentage of possessions for a player or team with a specific action or play type. By default, style similarity makes up 70% of the overall similarity score. The styles are:"),
        html.Div(
            [
                html.Strong("Slashing"),
                html.Ul([
                    html.Li("Rim attack"),
                    html.Li("Attack & kick"),
                    html.Li("Perimeter cut"),
                ]),
            ],
        ),
        html.Div(
            [
                html.Strong("Jumper"),
                html.Ul([
                    html.Li("Dribble pull-up"),
                    html.Li("Mid-range"),
                ]),
            ],
        ),
        html.Div(
            [
                html.Strong("Screens"),
                html.Ul([
                    html.Li("Big cut/roll"),
                    html.Li("Pick & pop"),
                ]),
            ],
        ),
        html.Div(
            [
                html.Strong("Post"),
                html.Ul([
                    html.Li("Post-up"),
                    html.Li("Post kick"),
                    html.Li("High-low"),
                ]),
            ],
        ),
        html.Div(
            [
                html.Strong("Misc."),
                html.Ul([
                    html.Li("Transition"),
                    html.Li("Rebound putback/scramble"),
                ]),
            ],
        ),
        html.Br(),
        html.H5("Stats"),
        html.P("Stats are all pace-adjusted and represent characteristics in play styles and abilities. By default, style similarity makes up 30% of the overall similarity scores. The stats used are:"),
        html.Div(
            [
                html.Strong("Shot Diet & Volume"),
                html.Ul([
                    html.Li("Free throw rate"),
                    html.Li("Rim rate"),
                    html.Li("3P att. rate"),
                    html.Li("Usage rate"),
                ]),
            ],
        ),
        html.Div(
            [
                html.Strong("Playmaking"),
                html.Ul([
                    html.Li("Assist rate"),
                    html.Li("Turnover rate"),
                ]),
            ],
        ),
        html.Div(
            [
                html.Strong("Physicality/Athleticism"),
                html.Ul([
                    html.Li("Offensive rebound rate"),
                    html.Li("Defensive rebound rate"),
                    html.Li("Block rate"),
                    html.Li("Steal rate"),
                ]),
            ],
        ),
        html.Br(),
        html.H5("Positions"),
        html.P("Positions are Guard, Wing, and Big. Comparisons are position-specific."),
        html.P("Positions defined from hoop-explorer.com's 8 detailed positions:"),
        html.Div(
            [
                html.Strong("Guard"),
                html.Ul([
                    html.Li("Pure PG"),
                    html.Li("Scoring PG"),
                    html.Li("Combo G"),
                ]),
            ],
            className="mb-3"
        ),

        html.Div(
            [
                html.Strong("Wing"),
                html.Ul([
                    html.Li("Wing Guard"),
                    html.Li("Wing Forward"),
                    html.Li("Stretch Forward"),
                ]),
            ],
            className="mb-3"
        ),

        html.Div(
            [
                html.Strong("Big"),
                html.Ul([
                    html.Li("Power Forward / Center"),
                    html.Li("Center"),
                ]),
            ]
        ),
        html.A(
            "Hoop-Explorer.com",
            href="https://hoop-explorer.com",
            target="_blank",   # open in new tab
            className="external-link"
        ),
        
    ])

def browse_layout():
    return html.Div(
        className="page-center",
        children=[
            html.Div(
                className="hero-box",
                children=[
                    html.H2("Similarity Browser", className="hero-title"),

                    html.P(
                        "Explore the strongest player–team similarities across college basketball.",
                        className="hero-subtitle"
                    ),

                    dcc.Dropdown(
                        id="browse-pos",
                        options=POSITION_OPTIONS,
                        placeholder="Select a position…",
                        clearable=False,
                        className="modern-dropdown"
                    ),

                    html.Div(
                        dbc.Button(
                            "RUN ANALYSIS",
                            id="browse-run",
                            n_clicks=0,
                            className="robot-button"
                        ),
                        style={"marginTop": "16px"}
                    ),
                ],
            ),

            html.Div(
                id="browse-filters-wrapper",
                style={"display": "none"},
                children=[

                    # ---------- FILTER ACCORDION ----------
                    dbc.Accordion(
                                        [
                                            dbc.AccordionItem(
                            title="Filters",
                            children=[
                                # ================= PLAYER FILTERS =================
                                html.Div(
                                    [
                                        html.Div(
                                            "PLAYER FILTERS",
                                            className="filter-group-header"
                                        ),

                                        dbc.Row(
                                            className="g-2",
                                            children=[
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="filter-player",
                                                        placeholder="Player",
                                                        className="modern-dropdown compact-dropdown",
                                                        multi=True
                                                    ),
                                                    xs=12, md=4
                                                ),
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="filter-player-team",
                                                        options=[{"label": t, "value": t} for t in PLAYER_TEAM_OPTIONS],
                                                        placeholder="Player Team",
                                                        className="modern-dropdown compact-dropdown",
                                                        multi=True
                                                    ),
                                                    xs=12, md=4
                                                ),
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="filter-player-conf",
                                                        options=[{"label": c, "value": c} for c in PLAYER_CONF_OPTIONS],
                                                        placeholder="Player Conference",
                                                        className="modern-dropdown compact-dropdown",
                                                        multi=True
                                                    ),
                                                    xs=12, md=4
                                                ),
                                            ],
                                        ),
                                    ],
                                    className="mb-4"
                                ),

                                # ================= TARGET FILTERS =================
                                html.Div(
                                    [
                                        html.Div(
                                            "TARGET FILTERS",
                                            className="filter-group-header"
                                        ),

                                        dbc.Row(
                                            className="g-2",
                                            children=[
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="filter-target-team",
                                                        options=[{"label": t, "value": t} for t in TARGET_TEAM_OPTIONS],
                                                        placeholder="Target Team",
                                                        className="modern-dropdown compact-dropdown",
                                                        multi=True
                                                    ),
                                                    xs=12, md=6
                                                ),
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="filter-target-conf",
                                                        options=[{"label": c, "value": c} for c in TARGET_CONF_OPTIONS],
                                                        placeholder="Target Conference",
                                                        className="modern-dropdown compact-dropdown",
                                                        multi=True
                                                    ),
                                                    xs=12, md=6
                                                ),
                                            ],
                                        ),
                                    ]
                                ),
                            ],
                        )

                        ],
                        start_collapsed=True,
                        flush=True,
                        className="mt-3"
                    ),

            ]),

            html.Hr(className="mt-3 mb-4", style={"opacity": 0.15}),

            html.Div(
                className="results-wrapper",
                children=[
                    dbc.Spinner(html.Div(id="browse-results"))
                ]
            )
        ]
    )





# -------------------------------------------------
# APP LAYOUT
# -------------------------------------------------
app.layout = html.Div(
    style={
        "backgroundColor": "#f8fafc",   # 👈 modern off-white
        "minHeight": "100vh"
    },
    children=[
        dcc.Location(id="url"),
        dcc.Store(id="selected-matchup", storage_type="session"),
        html.Div(id="navbar"),
        html.Div(id="page-content", style={"padding": "24px"}),
    ]
)


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
        return html.Div("This may take up to 1-2 minutes.")

    df = enter_player(player_name)

    return dash_table.DataTable(
        id="player-teams-table",
        data=df.to_dict("records"),
        columns=[
            {"name": "Team", "id": "team"},
            {
                "name": "Similarity Score",
                "id": "score",
                "type": "numeric",
                "format": {"specifier": ".3f"}
            },
            {
                "name": "Style Sim.",
                "id": "style_sim",
                "type": "numeric",
                "format": {"specifier": ".3f"}
            },
            {
                "name": "Stat Sim.",
                "id": "stat_sim",
                "type": "numeric",
                "format": {"specifier": ".3f"}
            },
        ],
        sort_action="native",
        row_selectable="single",
        page_size=10,
        style_table={
            "overflowX": "auto",
            "border": "none",
        },

        # --- Cells ---
        style_cell={
            "padding": "12px 14px",
            "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont",
            "fontSize": "14px",
            "color": "#1f2937",
            "backgroundColor": "white",
            "border": "none",
            "whiteSpace": "nowrap",
        },

        # --- Header ---
        style_header={
            "backgroundColor": "#f3f4f6",
            "color": "#374151",
            "fontWeight": "600",
            "fontSize": "13px",
            "textTransform": "uppercase",
            "letterSpacing": "0.04em",
            "borderBottom": "1px solid #e5e7eb",
            "padding": "10px 14px",
        },

        # --- Rows ---
        style_data_conditional=[
            # subtle zebra striping
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#f8fafc",
            },

            # hover effect (robotic / modern)
            {
                "if": {"state": "active"},
                "backgroundColor": "#e8eef6",
                "border": "none",
            },

            # numeric columns slightly bolder
            {
                "if": {"column_id": ["score", "style_sim", "stat_sim"]},
                "fontWeight": "500",
                "color": "#111827",
            },

            # emphasize similarity score most
            {
                "if": {"column_id": "score"},
                "fontWeight": "600",
            },
        ],
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
        return html.Div("This may take 30 seconds or more.")

    df = enter_team(team_name, pos_class)
    #print(df)

    return dash_table.DataTable(
        id="team-players-table",
        data=df.to_dict("records"),
        columns=[
            {"name": "Player", "id": "player_name"},
            {"name": "Player Team", "id": "player_team"},
            {
                "name": "Similarity Score",
                "id": "score",
                "type": "numeric",
                "format": {"specifier": ".3f"}
            },
            {
                "name": "Style Sim.",
                "id": "style_sim",
                "type": "numeric",
                "format": {"specifier": ".3f"}
            },
            {
                "name": "Stat Sim.",
                "id": "stat_sim",
                "type": "numeric",
                "format": {"specifier": ".3f"}
            },
        ],
        sort_action="native",
        row_selectable="single",
        page_size=10,
        style_table={
            "overflowX": "auto",
            "border": "none",
        },

        # --- Cells ---
        style_cell={
            "padding": "12px 14px",
            "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont",
            "fontSize": "14px",
            "color": "#1f2937",
            "backgroundColor": "white",
            "border": "none",
            "whiteSpace": "nowrap",
        },

        # --- Header ---
        style_header={
            "backgroundColor": "#f3f4f6",
            "color": "#374151",
            "fontWeight": "600",
            "fontSize": "13px",
            "textTransform": "uppercase",
            "letterSpacing": "0.04em",
            "borderBottom": "1px solid #e5e7eb",
            "padding": "10px 14px",
        },

        # --- Rows ---
        style_data_conditional=[
            # subtle zebra striping
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#f8fafc",
            },

            # hover effect (robotic / modern)
            {
                "if": {"state": "active"},
                "backgroundColor": "#e8eef6",
                "border": "none",
            },

            # numeric columns slightly bolder
            {
                "if": {"column_id": ["score", "style_sim", "stat_sim"]},
                "fontWeight": "500",
                "color": "#111827",
            },

            # emphasize similarity score most
            {
                "if": {"column_id": "score"},
                "fontWeight": "600",
            },
        ],
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

# @app.callback(
#     Output("browse-results", "children"),
#     Input("browse-run", "n_clicks"),
#     State("browse-pos", "value"),
#     prevent_initial_call=True
# )
# def run_browse(n_clicks, pos_class):
#     if not pos_class:
#         return html.Div("Select a position to run the analysis.")

#     df = browse_compatibility(pos_class)

#     if df.empty:
#         return html.Div("No results found for this position.")

#     return dash_table.DataTable(
#         id="browse-table",
#         data=df.to_dict("records"),
#         columns=[
#             {"name": "Player", "id": "player"},
#             {"name": "Player Team", "id": "player_team"},
#             {"name": "Target Team", "id": "target_team"},
#             {
#                 "name": "Similarity Score",
#                 "id": "score",
#                 "type": "numeric",
#                 "format": {"specifier": ".3f"}
#             },
#             {
#                 "name": "Style Sim.",
#                 "id": "style_sim",
#                 "type": "numeric",
#                 "format": {"specifier": ".3f"}
#             },
#             {
#                 "name": "Stat Sim.",
#                 "id": "stat_sim",
#                 "type": "numeric",
#                 "format": {"specifier": ".3f"}
#             },
#         ],
#         sort_action="native",
#         page_size=20,
#         row_selectable="single",
#         # --- Container ---
#         style_table={
#             "overflowX": "auto",
#             "border": "none",
#         },

#         # --- Cells ---
#         style_cell={
#             "padding": "12px 14px",
#             "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont",
#             "fontSize": "14px",
#             "color": "#1f2937",
#             "backgroundColor": "white",
#             "border": "none",
#             "whiteSpace": "nowrap",
#         },

#         # --- Header ---
#         style_header={
#             "backgroundColor": "#f3f4f6",
#             "color": "#374151",
#             "fontWeight": "600",
#             "fontSize": "13px",
#             "textTransform": "uppercase",
#             "letterSpacing": "0.04em",
#             "borderBottom": "1px solid #e5e7eb",
#             "padding": "10px 14px",
#         },

#         # --- Rows ---
#         style_data_conditional=[
#             # subtle zebra striping
#             {
#                 "if": {"row_index": "odd"},
#                 "backgroundColor": "#f8fafc",
#             },

#             # hover effect (robotic / modern)
#             {
#                 "if": {"state": "active"},
#                 "backgroundColor": "#e8eef6",
#                 "border": "none",
#             },

#             # numeric columns slightly bolder
#             {
#                 "if": {"column_id": ["score", "style_sim", "stat_sim"]},
#                 "fontWeight": "500",
#                 "color": "#111827",
#             },

#             # emphasize similarity score most
#             {
#                 "if": {"column_id": "score"},
#                 "fontWeight": "600",
#             },
#         ],
#         style_as_list_view=True,
#     )

@app.callback(
    Output("browse-results", "children"),
    Input("browse-run", "n_clicks"),
    Input("filter-player", "value"),
    Input("filter-player-team", "value"),
    Input("filter-player-conf", "value"),
    Input("filter-target-team", "value"),
    Input("filter-target-conf", "value"),
    State("browse-pos", "value"),
    prevent_initial_call=True
)
def run_browse(
        n_clicks,
        f_player,
        f_player_team,
        f_player_conf,
        f_target_team,
        f_target_conf,
        pos_class,
    ):
        if not pos_class:
            return html.Div("Select a position to run the analysis.")

        df = BROWSE_TABLES[pos_class].copy()

        # --- apply filters ---
        if f_player:
            df = df[df["player"].isin(f_player)]

        if f_player_team:
            df = df[df["player_team"].isin(f_player_team)]

        if f_player_conf:
            df = df[df["player_conf"].isin(f_player_conf)]

        if f_target_team:
            df = df[df["target_team"].isin(f_target_team)]

        if f_target_conf:
            df = df[df["target_conf"].isin(f_target_conf)]

        if df.empty:
            return html.Div("No results match the selected filters.")

        return dash_table.DataTable(
            id="browse-table",
            data=df.to_dict("records"),
            columns=[
                {"name": "Player", "id": "player"},
                {"name": "Player Team", "id": "player_team"},
                {"name": "Target Team", "id": "target_team"},
                {"name": "Similarity Score", "id": "score", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "Style Sim.", "id": "style_sim", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "Stat Sim.", "id": "stat_sim", "type": "numeric", "format": {"specifier": ".3f"}},
            ],
            sort_action="native",
            page_size=20,
            row_selectable="single",
            style_as_list_view=True,
            style_table={
            "overflowX": "auto",
            "border": "none",
        },

        # --- Cells ---
        style_cell={
            "padding": "12px 14px",
            "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont",
            "fontSize": "14px",
            "color": "#1f2937",
            "backgroundColor": "white",
            "border": "none",
            "whiteSpace": "nowrap",
        },

        # --- Header ---
        style_header={
            "backgroundColor": "#f3f4f6",
            "color": "#374151",
            "fontWeight": "600",
            "fontSize": "13px",
            "textTransform": "uppercase",
            "letterSpacing": "0.04em",
            "borderBottom": "1px solid #e5e7eb",
            "padding": "10px 14px",
        },

        # --- Rows ---
        style_data_conditional=[
            # subtle zebra striping
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#f8fafc",
            },

            # hover effect (robotic / modern)
            {
                "if": {"state": "active"},
                "backgroundColor": "#e8eef6",
                "border": "none",
            },

            # numeric columns slightly bolder
            {
                "if": {"column_id": ["score", "style_sim", "stat_sim"]},
                "fontWeight": "500",
                "color": "#111827",
            },

            # emphasize similarity score most
            {
                "if": {"column_id": "score"},
                "fontWeight": "600",
            },
        ],
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

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',      # Inside the axes
        paper_bgcolor='rgba(0,0,0,0)'  # Outside the axes
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


@app.callback(
    Output("browse-filters-wrapper", "style"),
    Input("browse-run", "n_clicks"),
    prevent_initial_call=True
)
def show_filters_after_run(n_clicks):
    return {"display": "block"}


# @app.callback(
#     Output("filter-player", "options"),
#     Input("browse-pos", "value"),
# )
# def update_player_filter_options(pos_class):
#     if not pos_class:
#         return []

#     return [
#         {"label": p, "value": p}
#         for p in PLAYER_OPTIONS_BY_POS[pos_class]
#     ]



@app.callback(
    Output("filter-player", "options"),
    Output("filter-player-team", "options"),
    Output("filter-player-conf", "options"),
    Output("filter-target-team", "options"),
    Output("filter-target-conf", "options"),
    Input("browse-run", "n_clicks"),
    State("browse-pos", "value"),
    prevent_initial_call=True
)
def populate_filters(_, pos):
    if not pos:
        raise PreventUpdate

    return (
        [{"label": p, "value": p} for p in PLAYER_OPTIONS_BY_POS[pos]],
        [{"label": t, "value": t} for t in PLAYER_TEAM_OPTIONS_BY_POS[pos]],
        [{"label": c, "value": c} for c in PLAYER_CONF_OPTIONS_BY_POS[pos]],
        [{"label": t, "value": t} for t in TARGET_TEAM_OPTIONS_BY_POS[pos]],
        [{"label": c, "value": c} for c in TARGET_CONF_OPTIONS_BY_POS[pos]],
    )







if __name__ == "__main__":
    app.run_server(debug=True)
