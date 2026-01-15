from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table
import dash
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import numpy as np


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
all_player_df = pd.concat([pd.read_csv('all_player_stats_1.csv'), pd.read_csv('all_player_stats_2.csv'), pd.read_csv('all_player_stats_3.csv')],axis=0)

all_player_df = all_player_df.loc[all_player_df['off_poss']>350]

#print(all_player_df['year'])

all_player_df['year'] = ('20' + all_player_df['year'].str[5:].astype(str))

all_player_df['year'] = all_player_df['year'].str.replace('209', '2019').astype(int)
#print(all_player_df['year'].value_counts())
all_player_df['conf'] = all_player_df['conf'].str.replace(" Conference", "").str.strip()
all_player_df = all_player_df.loc[~all_player_df['posClass'].str.contains(r'\?')]
names = all_player_df['player_name'].str.split(', ', expand=True)

power_conf = all_player_df.loc[all_player_df['conf'].isin(['Big Ten', 'Big 12', 'Atlantic Coast', 'Southeastern', 'Pac-12', 'Big East']), 'team'].unique()

pos_map = {'PG':'Guard',
           's-PG':'Guard',
           'CG':'Guard',
           'WG':'Wing',
           'WF':'Wing',
           'S-PF':'Wing',
           'PF/C':'Big',
           'C':'Big'}

all_player_df['posClass_orig'] = all_player_df['posClass'].copy()
all_player_df['posClass'] = all_player_df['posClass'].map(pos_map)

all_player_df['net_rtg'] = all_player_df['off_rtg'] - all_player_df['def_rtg']

all_player_df['def_fc'] = all_player_df['def_fc'] * 2


#all_player_df['roster.height'].str.replace('0')

all_player_df['roster.height'] = (
    all_player_df['roster.height']
    .astype(str)                      # avoid .str errors
    .str.replace(r'0(?!$)', '', regex=True)
)


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

all_player_df['pctile_def_stl'] = all_player_df['def_stl'].rank(pct=True)
all_player_df['pctile_def_blk'] = all_player_df['def_blk'].rank(pct=True)
all_player_df['pctile_def_fc'] = all_player_df['def_fc'].rank(pct=True, ascending=False)
all_player_df['pctile_def_orb'] = all_player_df['def_orb'].rank(pct=True)

all_player_df['pctile_adj_rapm_margin'] = (all_player_df['pctile_off_adj_rapm'] + all_player_df['pctile_def_adj_rapm']) / 2#all_player_df['adj_rapm_margin'].rank(pct=True)
all_player_df['pctile_net_rtg'] = (all_player_df['pctile_off_rtg'] + all_player_df['pctile_def_rtg']) / 2# all_player_df['net_rtg'].rank(pct=True)
all_player_df['pctile_off_ft'] = all_player_df['off_ft'].rank(pct=True)


STAT_SECTIONS = {
    # ---------------- Efficiency ----------------
    "RAPM (Regularized Adj. +/-)": [
        "adj_rapm_margin",
        "off_adj_rapm",
        "def_adj_rapm",
    ],

    "Off / Def Rating (Individual Pts Produced Per 100 Poss)": [
        "net_rtg",
        "off_rtg",
        "def_rtg",
    ],

    # ---------------- Four Factors ----------------
    "Four Factors & Playmaking": [
        "off_efg",
        "off_to",
        "off_orb",
        "off_ftr",
        "off_assist",
    ],

    # ---------------- Defense ----------------
    "Defense": [
        "def_orb",
        "def_stl",
        "def_blk",
        "def_fc",
    ],

    # ---------------- Shooting ----------------
    "Shooting": [
        "off_threep",
        "off_twopmid",
        "off_twoprim",
        "off_ft",
    ],

    # ---------------- Shot Diet ----------------
    "Shot Diet": [
        "off_threepr",
        "off_twopmidr",
        "off_twoprimr",
        "off_ftr",
    ],
}



STAT_DISPLAY = {
    # ----- RAPM -----
    "adj_rapm_margin": {
        "label": "RAPM",
        "format": "{:.2f}",
    },
    "off_adj_rapm": {
        "label": "Off. RAPM",
        "format": "{:.2f}",
    },
    "def_adj_rapm": {
        "label": "Def. RAPM",
        "format": "{:.2f}",
    },

    # ----- Ratings -----
    "net_rtg": {
        "label": "Net Rtg",
        "format": "{:.1f}",
    },
    "off_rtg": {
        "label": "Off. Rtg",
        "format": "{:.1f}",
    },
    "def_rtg": {
        "label": "Def. Rtg",
        "format": "{:.1f}",
    },

    # ----- Four Factors -----
    "off_efg": {
        "label": "eFG%",
        "format": "{:.1%}",
    },
    "off_to": {
        "label": "TOV%",
        "format": "{:.1%}",
    },
    "off_orb": {
        "label": "ORB%",
        "format": "{:.1%}",
    },
    "off_ftr": {
        "label": "FTR",
        "format": "{:.1%}",
    },
    "off_assist": {
        "label": "AST%",
        "format": "{:.1%}",
    },

    # ----- Defense -----
    "def_orb": {
        "label": "DRB%",
        "format": "{:.1%}",
    },
    "def_stl": {
        "label": "STL%",
        "format": "{:.1%}",
    },
    "def_blk": {
        "label": "BLK%",
        "format": "{:.1%}",
    },
    "def_fc": {
        "label": "Fouls/100",
        "format": "{:.2f}",
    },

    # ----- Shooting -----
    "off_threep": {
        "label": "3P%",
        "format": "{:.1%}",
    },
    "off_twopmid": {
        "label": "Mid FG%",
        "format": "{:.1%}",
    },
    "off_twoprim": {
        "label": "Rim FG%",
        "format": "{:.1%}",
    },
    "off_ft": {
        "label": "FT%",
        "format": "{:.1%}",
    },

    # ----- Shot Diet -----
    "off_threepr": {
        "label": "3PA Rate",
        "format": "{:.1%}",
    },
    "off_twopmidr": {
        "label": "Mid rate",
        "format": "{:.1%}",
    },
    "off_twoprimr": {
        "label": "Rim rate",
        "format": "{:.1%}",
    },
    "off_ftr": {
        "label": "FT Rate",
        "format": "{:.1%}",
    },



}



# 'off_style_rim_attack_pct',
#     'off_style_attack_kick_pct',
#     'off_style_perimeter_cut_pct',
#     'off_style_dribble_jumper_pct',
#     'off_style_mid_range_pct',
#     'off_style_perimeter_sniper_pct',
#     'off_style_hits_cutter_pct',
#     'off_style_pnr_passer_pct',
#     'off_style_big_cut_roll_pct',
#     'off_style_pick_pop_pct',
#     'off_style_high_low_pct',
#     'off_style_post_up_pct',
#     'off_style_post_kick_pct',
#     'off_style_reb_scramble_pct',
#     'off_style_transition_pct',





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


GROUPS = {
    "Slash": [
        "Rim Attack",
        "Attack Kick",
        "Perimeter Cut"
    ],
    "Jumper": [
        "Dribble Jumper",
        "Mid Range",
        "Perimeter Sniper"
    ],
    "Pass": [
        "Pnr Passer",
        "Hits Cutter"
    ],
    "Screen": [
        "Big Cut/Roll",
        "Pick Pop"
    ],
    "Post": [
        "Post Up",
        "Post Kick",
        "High Low"
    ],
    "Misc": [
        "Transition",
        "Reb Scramble"
    ]
}

GROUPS2 = {
    "Shot Diet": [
        "FTR",
        "Rim Rate",
        "3P Rate",
        "Usage%"
    ],
    "Pass": [
        "AST%",
        "TOV%",
    ],
    "PHYSICALITY": [
        "ORB%",
        "DRB%",
        "BLK%",
        "STL%"
    ]
}

# categories = [
#             "FTR", "Rim Rate", "3P Rate",
#             "AST%", "TOV%", "ORB%",
#             "DRB%", "BLK%",
#             "STL%", "Usage%"
#         ]

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
    "Guard": (
        all_player_df
        .query("posClass == 'Guard' and year == @CURRENT_SEASON")["player_name"]
        .unique()
    ),
    "Wing": (
        all_player_df
        .query("posClass == 'Wing' and year == @CURRENT_SEASON")["player_name"]
        .unique()
    ),
    "Big": (
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
        return "Extremely strong"
    elif score >= 0.75:
        return "Very Strong"
    elif score >= 0.65:
        return "Strong"
    elif score >= 0.5:
        return "Somewhat Strong"
    elif score >= 0.35:
        return "Decent"
    elif score >= 0.0:
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
        margin=dict(t=50, b=10, l=10, r=10)
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

def year_range_picker(id_prefix, start_default=2022, end_default=2026):
    return dbc.Row(
        className="g-2 justify-content-center",
        children=[
            dbc.Col([
                html.P("Start", style={"marginBottom": "0px"}, className="hero-subtitle"),
                dcc.Dropdown(
                    id=f"{id_prefix}-start-year",
                    options=[
                        {"label": "2018-19", "value": 2019},
                        {"label": "2019-20", "value": 2020},
                        {"label": "2020–21", "value": 2021},
                        {"label": "2021–22", "value": 2022},
                        {"label": "2022–23", "value": 2023},
                        {"label": "2023–24", "value": 2024},
                        {"label": "2024–25", "value": 2025},
                        {"label": "2025–26", "value": 2026},
                    ],
                    value=start_default if start_default is not None else all_player_df['year'].min(),
                    clearable=False,
                    className="modern-dropdown compact-dropdown"
                )],
                xs=9, md=6
            ),
            dbc.Col([
                html.P("End", style={"marginBottom": "0px"}, className="hero-subtitle"),
                dcc.Dropdown(
                    id=f"{id_prefix}-end-year",
                    options=[
                        {"label": "2018-19", "value": 2019},
                        {"label": "2019-20", "value": 2020},
                        {"label": "2020–21", "value": 2021},
                        {"label": "2021–22", "value": 2022},
                        {"label": "2022–23", "value": 2023},
                        {"label": "2023–24", "value": 2024},
                        {"label": "2024–25", "value": 2025},
                        {"label": "2025–26", "value": 2026},
                    ],
                    value=end_default if end_default is not None else CURRENT_SEASON,
                    clearable=False,
                    className="modern-dropdown compact-dropdown"
                )],
                xs=9, md=6
            ),
        ], justify='center'
    )


def stat_tile(label, value, pct_raw):
    return html.Div(
        className="stat-tile",
        children=[
            html.Div(
                label,
                style={
                    "fontSize": "13px",
                    "letterSpacing": "0.04em",
                    "textTransform": "uppercase",
                    "color": "#6b7280",
                    "marginBottom": "3px",
                },
            ),

            html.Div(
                value,
                style={
                    "fontSize": "20px",
                    "fontWeight": "600",
                    "color": "#111827",
                },
            ),

            percentile_bar(pct_raw),

            html.Div(
                format_percentile(pct_raw),
                style={
                    "fontSize": "12px",
                    "color": "#6b7280",
                    "marginTop": "4px",
                },
            ),
        ],
        style={
            "background": "white",
            "borderRadius": "14px",
            "padding": "4px 3px",
            "boxShadow": "0 4px 12px rgba(0,0,0,0.12)",
            "textAlign": "center",
            "marginTop":"5px",
            "marginBottom":"5px"
            #"display": "flex",
            #"flexDirection": "column",
            #"alignItems": "center",   # 👈 ensures perfect centering
        }
    )





def format_stat_value(col, value):
    if value is None or pd.isna(value):
        return "—"

    cfg = STAT_DISPLAY.get(col)

    if cfg and "format" in cfg:
        try:
            return cfg["format"].format(value)
        except Exception:
            return str(value)

    # fallback
    return f"{value:.2f}"



def format_percentile(p):
    if p is None or pd.isna(p):
        return "—"

    # p is 0–1
    pct = int(round(p * 100))

    suffix = "th"
    if pct % 10 == 1 and pct != 11:
        suffix = "st"
    elif pct % 10 == 2 and pct != 12:
        suffix = "nd"
    elif pct % 10 == 3 and pct != 13:
        suffix = "rd"

    return f"{pct}{suffix} %ile"




# def stat_grid(tiles, cols=4):
#     return dbc.Row(
#         [
#             dbc.Col(tile, xs=6, md=12 // cols)
#             for tile in tiles
#         ],
#         className="g-3",
#     )


def stat_grid(tiles, cols=5):
    return dbc.Row(
        [
            dbc.Col(
                tile,
                xs=6,
                md=12 // cols,
                #className="d-flex justify-content-center"  # 👈 key
            )
            for tile in tiles
        ],
        #className="g-3 justify-content-center",  # 👈 key
        justify='center'
    )


def stat_section(title, tiles):
    return html.Div(
        [
            html.H6(
                title,
                className="mt-3 mb-2",
                style={
                    "textTransform": "uppercase",
                    "letterSpacing": "0.06em",
                    "fontSize": "13px",
                    "color": "#6b7280",
                    'textAlign': 'center'
                },
            ),
            stat_grid(tiles),
            html.Br()
        ]
    )




def build_matchup_stat_grid(player_row):
    sections = []

    for section_name, cols in STAT_SECTIONS.items():
        tiles = []

        for col in cols:
            value = player_row.get(col)
            pct_col = get_pctile_col(col)
            pct = player_row.get(pct_col)


            tiles.append(
                stat_tile(
                    label=STAT_DISPLAY.get(col, {}).get("label", format_stat_label(col)),
                    value=format_stat_value(col, value),
                    pct_raw=pct,
                )
            )

        sections.append(stat_section(section_name, tiles))

    return html.Div(sections)


def percentile_bar(p):
    """
    p: percentile in 0–1 range
    """
    if p is None or pd.isna(p):
        return html.Div(
            style={
                "height": "6px",
                "backgroundColor": "#e5e7eb",
                "borderRadius": "4px",
                "marginTop": "6px",
            }
        )

    pct = max(0, min(1, float(p))) * 100

    return html.Div(
        # ⬇️ OUTER CONTAINER (controls whitespace)
        style={
            "marginTop": "8px",
            "display": "flex",
            "justifyContent": "center",
        },
        children=html.Div(
            # ⬇️ BAR TRACK (narrower than tile)
            style={
                "width": "72%",          # 👈 key change
                "height": "6px",
                "backgroundColor": "#e5e7eb",
                "borderRadius": "4px",
                "overflow": "hidden",
            },
            children=html.Div(
                # ⬇️ FILLED BAR
                style={
                    "width": f"{pct:.0f}%",
                    "height": "100%",
                    "backgroundColor": "#6366f1",
                    "borderRadius": "4px",
                    "transition": "width 0.4s ease",
                }
            ),
        ),
    )



def get_pctile_col(col):
    """
    Maps stat column → percentile column.
    Handles numeric substitutions (e.g. threep → 3p).
    """
    special_map = {
        "off_threep": "pctile_off_3p",
        "off_twopmid": "pctile_off_2pmid",
        "off_twoprim": "pctile_off_2prim",

        "off_threepr": "pctile_off_3pr",
        "off_twopmidr": "pctile_off_2pmidr",
        "off_twoprimr": "pctile_off_2primr",
    }

    return special_map.get(col, f"pctile_{col}")




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
               dbc.NavbarBrand(
                    html.Div(
                        [
                            # ---------- Top row: title + pill ----------
                            html.Div(
                                [
                                    html.Span(
                                        "CBB Similarity",
                                        style={
                                            "fontWeight": 600,
                                            "fontSize": "24px",
                                            "lineHeight": "1",
                                        },
                                    ),
                                    html.Span(
                                        "BETA",
                                        style={
                                            "backgroundColor": "#a32fba",
                                            "color": "white",
                                            "fontSize": "10px",
                                            "fontWeight": 700,
                                            "padding": "3px 7px",
                                            "borderRadius": "999px",
                                            "letterSpacing": "0.06em",
                                            "lineHeight": "1",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "8px",
                                },
                            ),

                            # ---------- Bottom row: attribution ----------
                            html.A(
                                "Data from hoop-explorer.com thru Jan. 14",
                                href="https://hoop-explorer.com",
                                target="_blank",
                                className="external-link",
                                style={
                                    "fontSize": "10px",
                                    "color": "#9ca3af",     # subtle gray
                                    "marginTop": "4px",
                                    "lineHeight": "1.2",
                                    "textDecoration": "none",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                        },
                    )
                ),


                dbc.Nav(
                    [
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
                            html.Div(["Specific", html.Br(), "Pairs"]),
                            href="/matchup",
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
        html.Div(
            [
                html.H4(
                    "Player ↔ Team",
                    className="hero-title",
                    style={"margin": 0}  # 👈 remove default H4 margin
                ),
                html.Span(
                    "BETA",
                    style={
                        "backgroundColor": "#a32fba",
                        "color": "white",
                        "fontSize": "11px",
                        "fontWeight": 700,
                        "padding": "3px 8px",
                        "borderRadius": "999px",
                        "marginLeft": "8px",
                        "letterSpacing": "0.06em",
                        "lineHeight": "1",          # 👈 helps vertical centering
                    }
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",  # 👈 vertical alignment
                "justifyContent": "center",  # 👈 optional (centered header)
                "gap": "6px",
            }
        ),
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
                    #html.H2("Find Player–Team Fits", className="hero-title"),
                    html.Div(
                        [
                            html.H4(
                                "Enter Players",
                                className="hero-title",
                                style={"margin": 0}  # 👈 remove default H4 margin
                            ),
                            html.Span(
                                "BETA",
                                style={
                                    "backgroundColor": "#a32fba",
                                    "color": "white",
                                    "fontSize": "11px",
                                    "fontWeight": 700,
                                    "padding": "3px 8px",
                                    "borderRadius": "999px",
                                    "marginLeft": "8px",
                                    "letterSpacing": "0.06em",
                                    "lineHeight": "1",          # 👈 helps vertical centering
                                }
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",  # 👈 vertical alignment
                            "justifyContent": "center",  # 👈 optional (centered header)
                            "gap": "6px",
                        }
                    ),
                    html.P(
                        "Select a player to see compatible teams.",
                        className="hero-subtitle"
                    ),
                    html.P(
                        "Selected player is compared with players from power-conference teams with the same position.",
                        className="hero-subtitle"
                    ),

                    dcc.Dropdown(
                        id="player-name",
                        options=player_2026_options,
                        placeholder="Search for a player…",
                        clearable=False,
                        className="modern-dropdown"
                    ),
                    html.Br(),
                    dbc.Row(
                        dbc.Col(
                            dbc.Accordion([
                                            dbc.AccordionItem(
                                            title="Enter Years",
                                            children=[       
                                                html.P("Select years to take team data from. "
                                                    "Typically this should align with the current head coach's tenure for the team you're interested in.",
                                                    className="hero-subtitle"),
                                                year_range_picker('player')
                                            ]
                                        )],
                                        className="styled-accordion year-accordion",
                                        #style={'width': '40%'},
                                        flush=True,
                                        always_open=False,
                                        start_collapsed=True,
                                        style={"overflow": "visible"}
                            ),
                            xs=9, md=5, lg=4
                        ),
                         
                         justify='center'
                    )
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
                    #html.H2("Find Team–Player Fits", className="hero-title"),
                    html.Div(
                        [
                            html.H4(
                                "Enter Teams",
                                className="hero-title",
                                style={"margin": 0}  # 👈 remove default H4 margin
                            ),
                            html.Span(
                                "BETA",
                                style={
                                    "backgroundColor": "#a32fba",
                                    "color": "white",
                                    "fontSize": "11px",
                                    "fontWeight": 700,
                                    "padding": "3px 8px",
                                    "borderRadius": "999px",
                                    "marginLeft": "8px",
                                    "letterSpacing": "0.06em",
                                    "lineHeight": "1",          # 👈 helps vertical centering
                                }
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",  # 👈 vertical alignment
                            "justifyContent": "center",  # 👈 optional (centered header)
                            "gap": "6px",
                        }
                    ),
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
                    html.Br(),                       
                    dbc.Row(
                        dbc.Col(
                            dbc.Accordion([
                                            dbc.AccordionItem(
                                            title="Enter Years",
                                            children=[       
                                                html.P("Select years to take team data from. "
                                                    "Typically this should align with the current head coach's tenure for the team you're interested in.",
                                                    className="hero-subtitle"),
                                                year_range_picker('team')
                                            ]
                                        )],
                                        className="styled-accordion year-accordion",
                                        #style={'width': '40%'},
                                        flush=True,
                                        always_open=False,
                                        start_collapsed=True
                            ),
                            xs=9, md=5, lg=4
                        ),
                         
                         justify='center'
                    )
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
    return html.Div([html.Div(
        className="page-center",
        children=[
            html.Div(
                className="hero-box",
                children=[
                    html.Div(
                        [
                            html.H4(
                                "Player ↔ Team",
                                className="hero-title",
                                style={"margin": 0}  # 👈 remove default H4 margin
                            ),
                            html.Span(
                                "BETA",
                                style={
                                    "backgroundColor": "#a32fba",
                                    "color": "white",
                                    "fontSize": "11px",
                                    "fontWeight": 700,
                                    "padding": "3px 8px",
                                    "borderRadius": "999px",
                                    "marginLeft": "8px",
                                    "letterSpacing": "0.06em",
                                    "lineHeight": "1",          # 👈 helps vertical centering
                                }
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",  # 👈 vertical alignment
                            "justifyContent": "center",  # 👈 optional (centered header)
                            "gap": "6px",
                        }
                    ),
                    # html.Span(
                    #     "BETA",
                    #     style={
                    #         "backgroundColor": "#a32fba",
                    #         "color":'white',
                    #         "fontSize": "11px",
                    #         "fontWeight": 700,
                    #         "padding": "3px 8px",
                    #         "borderRadius": "999px",
                    #         "marginLeft": "8px",
                    #         "verticalAlign": "middle",
                    #         "letterSpacing": "0.06em",
                    #     }
                    # ),
                    # html.H4("Player ↔ Team", className="hero-title"),
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
                                    className="modern-dropdown",
                                    value = all_player_df['player_name'].sample().iloc[0]
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
                                    className="modern-dropdown",
                                    value = all_player_df['team'].sample().iloc[0]
                                ),
                                xs=12, md=5, lg=4
                            ),
                        ]
                    ),
                    html.Br(),
                    dbc.Row(
                        dbc.Col(
                            dbc.Accordion([
                                            dbc.AccordionItem(
                                            title="Enter Years",
                                            children=[       
                                                html.P("Select years to take team data from. "
                                                    "Typically this should align with the current head coach's tenure for the team you're interested in.",
                                                    className="hero-subtitle"),
                                                year_range_picker('matchup')
                                            ]
                                        )],
                                        className="styled-accordion year-accordion",
                                        #style={'width': '40%'},
                                        flush=True,
                                        always_open=False,
                                        start_collapsed=True
                            ),
                            xs=9, md=5, lg=4
                        ),
                         
                         justify='center'
                    )
                ],
            ),

            html.Hr(className="mt-3 mb-4", style={"opacity": 0.15}),

            html.Div(id="matchup-summary", className="mb-3"),
    ]),

    html.Div([

        dbc.Row(
            dbc.Col(
                dbc.Tabs(
                        [
                            dbc.Tab(label="Style", tab_id="style"),
                            dbc.Tab(label="Stats", tab_id="stats"),
                        ],
                        id="matchup-tabs",
                        active_tab="style"
                    ),
                    xs=12,   # mobile
                    md=12,   # tablet
                    lg=10,    # desktop
                    xl=6    # wide screens
                    ),
                    justify='center'),
            dbc.Row(
               dbc.Col(
                    dcc.Graph(
                        id="matchup-bar-chart",
                        config={"displayModeBar": False}
                    ),
                    xs=12,   # mobile
                    md=12,   # tablet
                    lg=10,    # desktop
                    xl=6    # wide screens
                ),
                justify="center"
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Accordion(
                        [
                            dbc.AccordionItem(
                                title="Player Stat Summary (25-26)",
                                children=[
                                    html.P(
                                        [
                                            "Statistical Profile via ",
                                            html.A(
                                                "hoop-explorer.com",
                                                href="https://hoop-explorer.com",
                                                target="_blank",
                                                className="external-link",
                                            ),
                                        ],
                                        className="hero-subtitle",
                                        style={"textAlign": "center"},
                                    ),

                                    html.Div(
                                        id="matchup-stat-grid",
                                        children=html.Div(
                                            "Select a matchup to view detailed stats.",
                                            className="text-muted",
                                            style={"textAlign": "center", "padding": "16px"},
                                        ),
                                    ),

                                    html.P(
                                        [
                                            "Stats explained:",
                                            html.A(
                                                "hoop-explorer.blogspot.com",
                                                href="https://hoop-explorer.blogspot.com/2022/03/using-linq-to-build-advanced-filters-on.html",
                                                target="_blank",
                                                className="external-link",
                                            ),
                                        ],
                                        className="hero-subtitle",
                                        style={"textAlign": "center"},
                                    ),

                                    html.P(
                                        [
                                            "Basketball reference glossary:",
                                            html.A(
                                                "basketball-reference.com/glossary",
                                                href="https://www.basketball-reference.com/about/glossary.html",
                                                target="_blank",
                                                className="external-link",
                                            ),
                                        ],
                                        className="hero-subtitle",
                                        style={"textAlign": "center"},
                                    ),
                                    
                                ],
                            )
                        ],
                        className="styled-accordion profile-accordion",   # 👈 reuse exact styling
                        flush=True,
                        always_open=False,
                        start_collapsed=True,
                        style={"overflow": "visible"},
                    ),
                    xs=12,   # mobile
                    md=12,   # tablet
                    lg=10,    # desktop
                    xl=6    # wide screens
                ),
                justify="center",
                className="mb-3",
            ),

        ]
    )
    ])




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
        # html.P("Similarity scores are based on PCA embeddings of style and stat profiles. Scores are between -1 and 1 and can be interpreted as:"),
        # html.Div(
        #     [
        #         html.Strong("Similarity Scores"),
        #         html.Ul([
        #             html.Li(".9 - 1 → Extremely similar"),
        #             html.Li(".7 - .9 → Very similar"),
        #             html.Li(".5 - .7 → Somewhat similar"),
        #             html.Li(".2 - .5 → Some small similarities"),
        #             html.Li("<.2 → Not similar"),
        #         ]),
        #     ],
        # ),
        # html.P("An example using Nick Townsend (wing) and UConn: similarity scores are drawn from UConn's wings over the desired subset of seasons and Nick Townsend in the 2025-26 season..."),
        html.H5("How Similarity Is Calculated"),

        html.P(
            "Similarity scores measure how closely a player’s offensive style and statistical tendencies "
            "match a team’s historical usage at the same position."
        ),

        html.P("For a given matchup:"),

        html.Ul(
            [
                html.Li(
                    "The player profile comes from the current season (2025-26)."
                ),
                html.Li(
                    "The team profile is built by a weighted average of players at the same position group "
                    "(Guard, Wing, or Big) within that team’s system over the selected seasons."
                ),
                html.Li(
                    "All statistics are pace-adjusted and weighted by possessions, so higher-usage players "
                    "have more influence on the team profile."
                ),
            ]
        ),

        html.P(
            "To compare these profiles, the app uses Principal Component Analysis (PCA) to reduce "
            "several correlated stats and play-type frequencies into a smaller set of underlying "
            "dimensions that capture the main patterns in how players and teams operate."
        ),

        html.P(
            "Similarity is then calculated using cosine similarity between a player’s PCA representation "
            "and a team’s PCA representation for that position."
        ),

        html.P(
            "The final similarity score is a weighted combination of:"
        ),

        html.Ul(
            [
                html.Li("70% - Style Similarity (how actions and play types are used)"),
                html.Li(
                    "30% - Statistical Similarity (efficiency, shot diet, playmaking, and defensive indicators)"
                ),
            ]
        ),

        html.H5("Interpreting the Scores"),

        html.P(
            "The resulting similarity scores range from –1 to 1, and can be loosely interpreted as:"
        ),
        html.Div(
            [
                #html.Strong("Similarity Scores"),
                html.Ul([
                    html.Li(".9 - 1 → Extremely similar"),
                    html.Li(".7 - .9 → Very similar"),
                    html.Li(".5 - .7 → Somewhat similar"),
                    html.Li(".2 - .5 → Some small similarities"),
                    html.Li("<.2 → Not similar"),
                ]),
            ],
        ),

        # html.P(
        #     [
        #         html.Em("Example: "),
        #         "Using Nick Townsend (Wing) and UConn, Nick Townsend’s 2025–26 profile is compared against "
        #         "how UConn has historically used wings within its offensive system over the selected "
        #         "seasons. The resulting similarity score reflects how closely his style and statistical "
        #         "tendencies align with what UConn typically asks of that position."
        #     ]
        # ),

        html.H5("Learn More"),

        html.Ul(
            [
                html.Li(
                    [
                        "Principal Component Analysis (PCA): ",
                        html.A(
                            "https://en.wikipedia.org/wiki/Principal_component_analysis",
                            href="https://en.wikipedia.org/wiki/Principal_component_analysis",
                            target="_blank",
                            className="external-link",
                        ),
                    ]
                ),
                html.Li(
                    [
                        "Cosine Similarity: ",
                        html.A(
                            "https://en.wikipedia.org/wiki/Cosine_similarity",
                            href="https://en.wikipedia.org/wiki/Cosine_similarity",
                            target="_blank",
                            className="external-link",
                        ),
                    ]
                ),
                html.Li(
                    [
                        "Hoop Explorer methodology: ",
                        html.A(
                            "https://hoop-explorer.blogspot.com",
                            href="https://hoop-explorer.blogspot.com",
                            target="_blank",
                            className="external-link",
                        ),
                    ]
                ),
            ]
        ),

        html.Br(),
        html.H5("Styles"),
        html.A(
                "Play type details from hoop-explorer.com",
                href="https://hoop-explorer.blogspot.com",
                target="_blank",
                className="external-link",
            ),
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
                    html.Li("Perimeter sniper"),
                ]),
            ],
        ),
        html.Div(
            [
                html.Strong("Passing"),
                html.Ul([
                    html.Li("Pick-and-roll passer"),
                    html.Li("Hits cutter"),
                ]),
            ],
        ),
        html.Div(
            [
                html.Strong("Screen plays"),
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
        html.H5("Position groups"),
        html.P("Position groups are Guard, Wing, and Big. Comparisons are position-specific."),
        html.P("Position groups are defined from hoop-explorer.com's 8 detailed positions:"),
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
        # html.A(
        #     "Hoop-Explorer.com",
        #     href="https://hoop-explorer.com",
        #     target="_blank",   # open in new tab
        #     className="external-link"
        # ),

        html.Hr(style={"opacity": 0.3}),

        html.P(
            [
                "Report errors or suggestions: ",
                html.A(
                    "cbbbythenumbers@gmail.com",
                    href="mailto:cbbbythenumbers@gmail.com",
                    className="external-link",
                ),
            ],
            style={
                "fontSize": "14px",
                "color": "#374151",
            }
        ),
        html.P(
            [
                "Built by Smur",
            ],
            style={
                "fontSize": "14px",
                "color": "#374151",
                "marginTop":"4px"
            }
        )

        
    ])

def browse_layout():
    return html.Div(
        className="page-center",
        children=[
            html.Div(
                className="hero-box",
                children=[
                    html.Div(
                        [
                            html.H4(
                                "Similarity Browser",
                                className="hero-title",
                                style={"margin": 0}  # 👈 remove default H4 margin
                            ),
                            html.Span(
                                "BETA",
                                style={
                                    "backgroundColor": "#a32fba",
                                    "color": "white",
                                    "fontSize": "11px",
                                    "fontWeight": 700,
                                    "padding": "3px 8px",
                                    "borderRadius": "999px",
                                    "marginLeft": "8px",
                                    "letterSpacing": "0.06em",
                                    "lineHeight": "1",          # 👈 helps vertical centering
                                }
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",  # 👈 vertical alignment
                            "justifyContent": "center",  # 👈 optional (centered header)
                            "gap": "6px",
                        }
                    ),

                    html.P(
                        "Explore the strongest player–team similarities across college basketball. "
                        "Includes players from the 25-26 season and team stats from the 22-26 seasons among players with the target position.",
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
        html.Br()
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
    if pathname in (None, "/", ""):
        return team_layout()   # 👈 default landing page
    elif pathname == "/browse":
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
        return player_layout()


# @app.callback(
#     Output("url", "pathname"),
#     Input("selected-matchup", "data"),
#     prevent_initial_call=True
# )
# def go_to_matchup(_):
#     return "/matchup"


import dash
from dash import no_update
from dash.exceptions import PreventUpdate

@app.callback(
    Output("url", "pathname"),
    Output("selected-matchup", "data", allow_duplicate=True),
    Input("selected-matchup", "data"),
    State("url", "pathname"),
    prevent_initial_call=True
)
def go_to_matchup(data, pathname):
    if not isinstance(data, dict):
        raise PreventUpdate

    # Only auto-navigate when explicitly requested
    if not data.get("auto_nav", False):
        raise PreventUpdate

    # Clear the flag so refreshes don't keep redirecting
    cleared = {**data, "auto_nav": False}

    # If already on matchup, don't change URL
    if pathname == "/matchup":
        return no_update, cleared

    return "/matchup", cleared





#####
##### Enter Player
#####

@app.callback(
    Output("player-results", "children"),
    Input("player-name", "value"),
    Input('player-start-year', 'value'),
    Input('player-end-year', 'value')
)
def update_player_results(player_name, start_year, end_year):
    if not player_name:
        return html.Div("This may take up to 1-2 minutes.")

    df = enter_player(player_name, start_year=start_year, end_year=end_year)

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
    State("player-start-year", "value"),
    State("player-end-year", "value"),
    prevent_initial_call=True
)
def select_team_for_player(selected_rows, table_data, player_name, start_year, end_year):
    if not selected_rows:
        raise PreventUpdate

    row = table_data[selected_rows[0]]

    # infer position from player
    extra_info = (
        all_player_df
        .query("player_name == @player_name")
        .sort_values("year", ascending=False)
        [["posClass", 'roster.height', 'roster.year_class', 'roster.origin']]
    )

    return {
        "player": player_name,
        "team": row["team"],
        "posClass": extra_info['posClass'].iloc[0],
        "start_year": start_year,
        "end_year": end_year,
        "auto_nav": True,
        #'roster.height':extra_info['roster.height'].iloc[0],
        #'roster.year_class':extra_info['roster.year_class'].iloc[0],
        #'roster.origin':extra_info['roster.origin'].iloc[0]
    }




#####
##### Enter Team
#####
@app.callback(
    Output("team-results", "children"),
    Input("team-name", "value"),
    Input("team-pos", "value"),
    Input('team-start-year', 'value'),
    Input('team-end-year', 'value')
)
def update_team_results(team_name, pos_class, start_year, end_year):
    if not team_name or not pos_class:
        return html.Div("This may take 30 seconds or more.")
    

    df = enter_team(team_name, pos_class, start_year=start_year, end_year=end_year)
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
    State("team-start-year", "value"),
    State("team-end-year", "value"),
    prevent_initial_call=True
)
def select_player_for_team(selected_rows, table_data, team_name, pos_class, start_year, end_year):
    if not selected_rows:
        raise PreventUpdate

    row = table_data[selected_rows[0]]

    return {
        "player": row["player_name"],
        "team": team_name,
        "posClass": pos_class,
        "start_year": start_year,
        "end_year": end_year,
        "auto_nav": True,
        #"roster.height": row['roster.height'],
        #"roster.year_class": row['roster.year_class'],
        #"roster.year_class": row['roster.year_class']
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
        "posClass": pos_class,
        "auto_nav": True,
        #"roster.height": row['roster.height'],
        #"roster.year_class": row['roster.year_class'],
        #"roster.year_class": row['roster.year_class']
    }


#####
##### Matchup
#####

@app.callback(
    Output("matchup-summary", "children"),
    Input("selected-matchup", "data"),
    Input('matchup-start-year', 'value'),
    Input('matchup-end-year', 'value')
)
def update_matchup_summary(data, start_year, end_year):
    if not data:
        return html.Div("Select a player–team pairing to view details.")

    detail = get_matchup_detail(
        player=data["player"],
        team=data["team"],
        pos_class=data["posClass"],
        start_year=start_year,
        end_year=end_year
    )

    s = detail["scores"]
    roster = detail["roster"]

    label = fit_label(s["score"])

    return dbc.Card(
        dbc.CardBody([
            # ---- Header ----
            html.Div(
                [
                    html.H4(
                        f'{data["player"]} ({data["posClass"]}) ↔ {data["team"]}',
                        className="mb-1",
                        style={"textAlign": "center"}
                    ),
                    # html.Div(
                    #     f'Position: {data["posClass"]}',
                    #     className="text-muted",
                    #     style={"textAlign": "center"}
                    # ),
                    html.Div(
                        f'{roster["team_og"]} | {roster["pos_og"]} | {roster["height"]} | {roster["year_class"]} | {roster["origin"]}',
                        className="text-muted",
                        style={"textAlign": "center"}
                    ),
                    html.Div(
                        f"Comparison is against players at the same position ({data["posClass"]}) within the team’s system.",
                        className="text-muted",
                        style={
                            "textAlign": "center",
                            "fontSize": "14px",
                            "marginTop": "6px",
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
                    height=145,
                    font_size=28
                ),
                config={"displayModeBar": False},
                style={"marginTop": "20px"}
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
                                height=135,
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
    Input("matchup-tabs", "active_tab"),
    Input('matchup-start-year', 'value'),
    Input('matchup-end-year', 'value')
)
def update_matchup_chart(data, tab, start_year, end_year):
    if not data:
        return go.Figure()

    detail = get_matchup_detail(
        player=data["player"],
        team=data["team"],
        pos_class=data["posClass"],
        start_year=start_year,
        end_year=end_year
    )

    player_row = detail["player_row"]
    team_vec   = detail["team_vec"]

    if tab == "style":
        cols = STYLE_COLS
        y_labels = [
            c.replace("off_style_", "")
            .replace("_pct", "")
            .replace("_", " ")
            .replace('dribble jumper', 'off-dribble')
            .replace('perimeter sniper', '3P sniper')
            .replace('pick pop', 'Pick & Pop')
            .replace('pnr passer', 'P&R Passer')
            .replace('big cut roll', 'Big Cut/Roll')
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
        f"position ({pos}) from the entered seasons ({start_year}-{end_year})"
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
            x=0.15,
            xanchor="left",
            y=0.97
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
                standoff=10,
            ),
            domain=[0.32, 1]
        )

        categories = [
            "Rim Attack", "Attack Kick", "Perimeter Cut",
            "Dribble Jumper", "Mid Range", "Perimeter Sniper",
            "Pnr Passer", "Hits Cutter",
            "Big Cut/Roll", "Pick Pop",
            "Post Up", "Post Kick", "High Low",
            "Transition", "Reb Scramble"
        ]

        cat_index = {c: i for i, c in enumerate(categories)}

        annotations = []

        for label, stats in GROUPS.items():
            idxs = [cat_index[s] for s in stats if s in cat_index]
            y_center = sum(idxs) / len(idxs)

            annotations.append(
                dict(
                    x=-0.12,                # push left of axis
                    y=y_center,
                    xref="paper",
                    yref="y",
                    text=label.upper(),
                    showarrow=False,
                    textangle=-90,
                    font=dict(
                        size=12,
                        color="#888",
                        family="Inter, sans-serif"
                    ),
                    align="center"
                )
            )

        fig.update_layout(annotations=annotations)

        shapes = []

        running = 0
        for stats in GROUPS.values():
            running += len(stats)
            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    yref="y",
                    x0=-0.1,
                    x1=0.32,
                    y0=running - 0.5,
                    y1=running - 0.5,
                    line=dict(color="#e0e0e0", width=1)
                )
            )

        fig.update_layout(shapes=shapes)

        fig.update_yaxes(
            tickfont=dict(
                family="Inter, sans-serif",
                size=13,
                color="#777"
            ),
            ticklabelposition="outside",
            ticks=""
        )


    ### STATS TAB    
    else:
        xaxis_cfg = dict(
            title=dict(
                text="Value",
                font=dict(size=13),
                standoff=10,
            ),
            tickformat=".0%" ,
            domain=[0.32, 1]
        )

        categories = [
            "FTR", "Rim Rate", "3P Rate", "Usage%"
            "AST%", "TOV%",
            "ORB%", "DRB%", "BLK%", "STL%"
        ]

        cat_index = {c: i for i, c in enumerate(categories)}

        annotations = []

        for label, stats in GROUPS2.items():
            idxs = [cat_index[s] for s in stats if s in cat_index]
            y_center = sum(idxs) / len(idxs)

            annotations.append(
                dict(
                    x=-0.12,                # push left of axis
                    y=y_center+0.56,
                    xref="paper",
                    yref="y",
                    text=label.upper(),
                    showarrow=False,
                    textangle=-90,
                    font=dict(
                        size=13,
                        color="#888",
                        family="Inter, sans-serif"
                    ),
                    align="center"
                )
            )

        fig.update_layout(annotations=annotations)

        shapes = []

        running = 0
        for stats in GROUPS2.values():
            running += len(stats)
            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    yref="y",
                    x0=-0.1,
                    x1=0.32,
                    y0=running - 0.5,
                    y1=running - 0.5,
                    line=dict(color="#e0e0e0", width=1)
                )
            )

        fig.update_layout(shapes=shapes)

        fig.update_yaxes(
            tickfont=dict(
                family="Inter, sans-serif",
                size=12,
                color="#777"
            ),
            ticklabelposition="outside",
            ticks=""
        )



    fig.update_layout(
        barmode="group",
        height=450,

        # ⬇️ This is what actually prevents overlap
        yaxis=dict(
            #automargin=True,
            ticks="outside",
            domain=[0.0, 0.88]   # 👈 reserve top 18% for title/subtitle
        ),

        xaxis=xaxis_cfg,

        margin=dict(
            l=100,
            r=50,
            t=80,   # keep generous top margin
            b=30
        ),

        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.1,              # 👈 pushes legend below chart
            xanchor="center",
            yanchor="top",
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=14)
        ),
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

    fig.update_layout(height=750, autosize=False)



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
    State("selected-matchup", "data"),
    prevent_initial_call=True
)
def update_matchup_from_dropdowns(player, team, existing):
    # --- guard against half-filled dropdowns ---
    if not player or not team:
        raise PreventUpdate

    # --- infer position ---
    extra_info = (
        all_player_df
        .query("player_name == @player")
        .sort_values("year", ascending=False)
        [["posClass", 'roster.height', 'roster.year_class', 'roster.origin']]
    )

    # --- defaults if no existing matchup yet ---
    start_year = 2022
    end_year = CURRENT_SEASON

    if isinstance(existing, dict):
        start_year = existing.get("start_year", start_year)
        end_year = existing.get("end_year", end_year)

    return {
        "player": player,
        "team": team,
        "posClass": extra_info["posClass"].iloc[0],
        "start_year": start_year,
        "end_year": end_year,
    }




@app.callback(
    Output("matchup-stat-grid", "children"),
    Input("selected-matchup", "data"),
    Input("matchup-start-year", "value"),
    Input("matchup-end-year", "value"),
)
def update_matchup_stat_grid(data, start_year, end_year):
    if not data:
        return html.Div(
            "Select a player–team pairing to view detailed stats.",
            className="text-muted",
            style={"textAlign": "center", "padding": "16px"},
        )

    detail = get_matchup_detail(
        player=data["player"],
        team=data["team"],
        pos_class=data["posClass"],
        start_year=start_year,
        end_year=end_year,
    )

    player_row = detail["player_row"]

    return build_matchup_stat_grid(player_row)





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



@app.callback(
    Output("matchup-start-year", "value"),
    Output("matchup-end-year", "value"),
    Input("selected-matchup", "data"),
)
def sync_matchup_years(data):
    if not data:
        raise PreventUpdate

    return (
        data.get("start_year", 2022),
        data.get("end_year", CURRENT_SEASON)
    )




if __name__ == "__main__":
    app.run_server(debug=True)
