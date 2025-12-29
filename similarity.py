import pandas as pd
import numpy as np
from functools import lru_cache

all_player_df = pd.concat([pd.read_csv('all_player_stats_1.csv'), pd.read_csv('all_player_stats_2.csv')],axis=0)
all_player_df['year'] = ('20' + all_player_df['year'].str[5:].astype(str)).astype(int)
all_player_df['conf'] = all_player_df['conf'].str.replace(" Conference", "").str.strip()

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity

class StylePCAModel:
    def __init__(self, n_components=0.85):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=n_components)
        self.fitted = False
        
    def fit(self, X):
        X_scaled = self.scaler.fit_transform(X)
        X_pca = self.pca.fit_transform(X_scaled)
        self.fitted = True
        return X_pca
    
    def transform(self, X):
        assert self.fitted, "Model must be fitted first"
        X_scaled = self.scaler.transform(X)
        return self.pca.transform(X_scaled)
    
    def similarity(self, A, B):
        """
        Cosine similarity between rows of A and B
        """
        return cosine_similarity(A, B)


STYLE_COLS = [
    'off_style_rim_attack_pct',
    'off_style_attack_kick_pct',
    'off_style_dribble_jumper_pct',
    'off_style_mid_range_pct',
    'off_style_perimeter_cut_pct',
    'off_style_big_cut_roll_pct',
    'off_style_post_up_pct',
    'off_style_post_kick_pct',
    'off_style_pick_pop_pct',
    'off_style_high_low_pct',
    'off_style_reb_scramble_pct',
    'off_style_transition_pct'
]

STAT_COLS = [
    'off_ftr',
    'off_twoprimr',
    'off_threepr',
    'off_assist',
    'off_to',
    'off_orb',
    'def_orb',
    'def_blk',
    'def_stl',
    'off_usage'
]


def vector_from_dict(vec_dict, cols):
    return np.array([vec_dict[c] for c in cols], dtype=float)

def transform_team(self, team_vec):
    style_x = vector_from_dict(team_vec, STYLE_COLS).reshape(1, -1)
    stat_x  = vector_from_dict(team_vec, STAT_COLS).reshape(1, -1)

    style_z = self.style_model.transform(style_x)
    stat_z  = self.stat_model.transform(stat_x)

    return style_z, stat_z


class DualStylePCAModel:
    def __init__(
        self,
        style_components=0.85,
        stat_components=0.85,
        style_weight=0.7
    ):
        self.style_model = StylePCAModel(style_components)
        self.stat_model  = StylePCAModel(stat_components)
        self.style_weight = style_weight
        self.stat_weight  = 1 - style_weight
        
    def fit(self, df):
        self.style_model.fit(df[STYLE_COLS].values)
        self.stat_model.fit(df[STAT_COLS].values)
        
    def transform_player(self, row):
        style_z = self.style_model.transform(
            row[STYLE_COLS].values.reshape(1, -1)
        )
        stat_z = self.stat_model.transform(
            row[STAT_COLS].values.reshape(1, -1)
        )
        return style_z, stat_z
    
    # ✅ FIXED METHOD
    def transform_team(self, team_vec):
        style_x = vector_from_dict(team_vec, STYLE_COLS).reshape(1, -1)
        stat_x  = vector_from_dict(team_vec, STAT_COLS).reshape(1, -1)

        style_z = self.style_model.transform(style_x)
        stat_z  = self.stat_model.transform(stat_x)

        return style_z, stat_z
    
    def compatibility(self, player_row, team_vec):
        p_style, p_stat = self.transform_player(player_row)
        t_style, t_stat = self.transform_team(team_vec)
        
        style_sim = cosine_similarity(p_style, t_style)[0, 0]
        stat_sim  = cosine_similarity(p_stat, t_stat)[0, 0]
        
        score = (
            self.style_weight * style_sim
            + self.stat_weight  * stat_sim
        )
        
        return {
            "score": score,
            "style_sim": style_sim,
            "stat_sim": stat_sim
        }



def build_team_position_vector(
    df,
    team,
    start_year,
    end_year,
    pos_class,
    weight_col='off_poss'
):
    dff = (
        df
        .query("team == @team")
        .query("year >= @start_year and year <= @end_year")
        .query("posClass == @pos_class")
        .dropna(subset=STYLE_COLS + STAT_COLS)
    )
    
    if dff.empty:
        return None
    
    weights = dff[weight_col].values
    
    vec = {}
    for col in STYLE_COLS + STAT_COLS:
        vec[col] = np.average(dff[col].values, weights=weights)
        
    return vec



POWER_CONFERENCES = [
    "Atlantic Coast", "Big Ten", "Big 12", "Southeastern", "Pac-12", "Big East"
]

power_teams = (
    all_player_df
    .query("conf in @POWER_CONFERENCES")
    ['team']
    .unique()
)




def rank_teams_for_player(
    player_row,
    team_vectors,
    model
):
    rows = []
    
    for team, team_vec in team_vectors.items():
        res = model.compatibility(player_row, team_vec)
        rows.append({
            "team": team,
            **res
        })
        
    return (
        pd.DataFrame(rows)
        .sort_values("score", ascending=False)
        .reset_index(drop=True)
    )





@lru_cache(maxsize=256)
def batch_player_team_compatibility(
    players_df,
    teams,
    start_year,
    end_year,
    pos_class,
    model,
    min_poss=100
):
    # ---- build team vectors once ----
    team_vectors = {}
    for team in teams:
        vec = build_team_position_vector(
            all_player_df,
            team,
            start_year,
            end_year,
            pos_class
        )
        if vec is not None:
            team_vectors[team] = vec
    
    results = []
    
    for _, row in (
        players_df
        .query("off_poss >= @min_poss")
        .iterrows()
    ):
        for team, team_vec in team_vectors.items():
            res = model.compatibility(row, team_vec)
            
            results.append({
                "player": row["player_name"],
                "player_team": row["team"],
                "target_team": team,
                "score": res["score"],
                "style_sim": res["style_sim"],
                "stat_sim": res["stat_sim"]
            })
    
    return pd.DataFrame(results)





@lru_cache(maxsize=256)
def enter_position(pos):
    CURRENT_SEASON = 2026
    POS_CLASS = pos

    players_2026 = (
        all_player_df
        .query("year == @CURRENT_SEASON")
        .query("posClass == @POS_CLASS")
        .dropna(subset=STYLE_COLS + STAT_COLS)
    )

    model = DualStylePCAModel(style_weight=0.7)
    model.fit(players_2026)

    results = batch_player_team_compatibility(
        players_df=players_2026,
        teams=power_teams,
        start_year=2023,
        end_year=2026,
        pos_class=POS_CLASS,
        model=model
    )

    top_fits = (
        results
        .sort_values("score", ascending=False)
        .groupby("player")
        .head(5)
    )

    top_targets = (
        results
        .sort_values("score", ascending=False)
        .groupby("target_team")
        .head(5)
    )

    results = results.rename(columns={'score':'sim_score'})
    results.sort_values("sim_score", ascending=False).head(20)

    # results["sim_score"].hist(bins=50)
    results[['style_sim', 'stat_sim']].corr()
    results.columns = results.columns.str.replace('sim', 'similarity')

    print(results.sort_values(by='similarity_score', ascending=False)[:10].round(2).reset_index(drop=True))

    return results






@lru_cache(maxsize=256)
def most_similar_teams_for_player(
    player_row,
    team_vectors,
    model,
    top_n=10,
    exclude_team=True
):
    rows = []
    
    for team, team_vec in team_vectors.items():
        if exclude_team and team == player_row["team"]:
            continue
        
        res = model.compatibility(player_row, team_vec)
        
        rows.append({
            "team": team,
            "score": res["score"],
            "style_sim": res["style_sim"],
            "stat_sim": res["stat_sim"]
        })
    
    return (
        pd.DataFrame(rows)
        .sort_values("score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )








@lru_cache(maxsize=256)
def enter_player(player_name, year=2026, style_weight=0.7, top_n=10):
    # ---- pull player row first ----
    player_row_all = (
        all_player_df
        .query("player_name == @player_name and year == @year")
        .iloc[0]
    )

    # ---- derive position from player ----
    POS_CLASS = player_row_all["posClass"]
    print(POS_CLASS)



    # ---- filter players for PCA training ----
    players_pos = (
        all_player_df
        .query("year == @year")
        .query("posClass == @POS_CLASS")
        .dropna(subset=STYLE_COLS + STAT_COLS)
    )

    # optional stability filter
    players_pos = players_pos.query("off_poss >= 100")

    # ---- fit model ----
    model = DualStylePCAModel(style_weight=style_weight)
    model.fit(players_pos)

    # ---- isolate player row (same dataframe as PCA) ----
    player_row = (
        players_pos
        .loc[players_pos["player_name"] == player_name]
        .iloc[0]
    )

    # ---- build team vectors ----
    team_vectors = {}

    for team in power_teams:
        vec = build_team_position_vector(
            df=all_player_df,
            team=team,
            start_year=year-3,
            end_year=year,
            pos_class=POS_CLASS
        )
        if vec is not None:
            team_vectors[team] = vec

    # ---- return ranked teams ----
    return (
        most_similar_teams_for_player(
            player_row,
            team_vectors,
            model,
            top_n=top_n
        )
        .round(3)
    )






@lru_cache(maxsize=256)
def enter_team(
    team_name,
    pos_class,
    year=2026,
    style_weight=0.7,
    top_n=15,
    min_poss=100
):
    # ---- build team vector first ----
    team_vec = build_team_position_vector(
        df=all_player_df,
        team=team_name,
        start_year=year - 4,
        end_year=year,
        pos_class=pos_class
    )

    if team_vec is None:
        raise ValueError(
            f"No data available for {team_name}, posClass={pos_class}, years={year-3}-{year}"
        )

    # ---- build player pool ----
    players_pos = (
        all_player_df
        .query("year == @year")
        .query("posClass == @pos_class")
        .dropna(subset=STYLE_COLS + STAT_COLS)
    )

    if players_pos.empty:
        raise ValueError(
            f"No players found for posClass='{pos_class}' in year {year}"
        )

    players_pos = players_pos.query("off_poss >= @min_poss")

    # ---- fit PCA model on player pool ----
    model = DualStylePCAModel(style_weight=style_weight)
    model.fit(players_pos)

    # ---- rank players ----
    rows = []

    for _, row in players_pos.iterrows():
        res = model.compatibility(row, team_vec)

        rows.append({
            "player_name": row["player_name"],
            "player_team": row["team"],
            "score": res["score"],
            "style_sim": res["style_sim"],
            "stat_sim": res["stat_sim"]
        })

    out = (
        pd.DataFrame(rows)
        .sort_values("score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return out.round(3)



@lru_cache(maxsize=256)
def browse_compatibility(
    pos_class,
    year=2026,
    min_poss=150,
    top_players=40,
    top_n_per_player=3,
    style_weight=0.7
):
    """
    Explore the strongest player–team fits for a given position.

    This is an intentionally heavy operation meant for analysis,
    not instant UI responses.
    """

    players = (
        all_player_df
        .query("year == @year")
        .query("posClass == @pos_class")
        .query("off_poss >= @min_poss")
        .dropna(subset=STYLE_COLS + STAT_COLS)
        .sort_values("off_poss", ascending=False)
        .head(top_players)
        .copy()
    )

    if players.empty:
        return pd.DataFrame()

    model = DualStylePCAModel(style_weight=style_weight)
    model.fit(players)

    results = batch_player_team_compatibility(
        players_df=players,
        teams=power_teams,
        start_year=year - 4,
        end_year=year,
        pos_class=pos_class,
        model=model
    )

    return (
        results
        .sort_values("score", ascending=False)
        .groupby("player")
        .head(top_n_per_player)
        .reset_index(drop=True)
    )



@lru_cache(maxsize=256)
def get_matchup_detail(player, team, pos_class, year=2026, style_weight=0.7):
    # get player row
    player_row = (
        all_player_df
        .query("player_name == @player and year == @year")
        .iloc[0]
    )

    # build team vector
    team_vec = build_team_position_vector(
        df=all_player_df,
        team=team,
        start_year=year - 4,
        end_year=year,
        pos_class=pos_class
    )

    model = DualStylePCAModel(style_weight=style_weight)
    model.fit(
        all_player_df
        .query("year == @year and posClass == @pos_class")
        .dropna(subset=STYLE_COLS + STAT_COLS)
    )

    sims = model.compatibility(player_row, team_vec)

    return {
        "player_row": player_row,
        "team_vec": team_vec,
        "scores": sims
    }
