import pandas as pd
import numpy as np
import data_cleaning as dc
import warnings

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

warnings.simplefilter(action='ignore', category=FutureWarning)

PLAYERS = '2022_players.csv'
TEAMS = '2000_to_2022_teams.csv'
AGG_TEAMS = 'agg_teams.csv'
ALL_PLAYERS = '2000_to_2022_players.csv'

# pd.set_option('display.max_columns', None)
AVERAGED_STATS = ['ANY/A', 'AY/A', 'Cmp%', 'Int%', 'Kic_KOAvg', 'Kic_Y/Rt', 'Lng', 'NY/A', 'Pts/G', 'Pun_Lng',
                  'Pun_Y/P', 'Pun_Y/R', 'Rus_Y/A', 'Sco_Lng', 'Sk%', 'TD%', 'Y/A', 'Y/C', 'Y/G', 'Kic_Lng', 'Rate']
GM_COLS = list(pd.read_csv(ALL_PLAYERS, low_memory=False).select_dtypes(include=np.number).columns.to_list())
GM_COLS = [x for x in GM_COLS if x not in ['Team', 'Season', 'Year', 'id', 'Age', 'No.', 'Cap Hit', 'Cap %']]
agg_team = pd.DataFrame()


def agg_team_stats(team_data, player_data):
    """
    Get aggregated team stats for comparison to user's team.

    """
    # get all teams and seasons
    combs = list(zip(team_data['Team'].values, team_data['Year'].values))
    new_df = pd.DataFrame(columns=GM_COLS)
    for comb in combs:
        team = dict()
        team['Team'] = comb[0]
        team['Season'] = comb[1]
        # get team dataframe
        team_df = player_data.loc[(player_data.Team == comb[0]) & (player_data.Season == comb[1])]
        for label in list(team_data.columns):
            if label in GM_COLS:
                # only get players who have stats
                stat_df = team_df.loc[~team_df[label].isnull()]

                # check if it should be summed or averaged
                if label in AVERAGED_STATS:
                    team[label] = round(stat_df[label].mean(), 1)
                else:
                    team[label] = stat_df[label].sum()
        new_df = new_df.append(team, ignore_index=True)

    # add w-l%, drop empty cols, remove 2022 (only 11 games)
    new_df['W-L%'] = new_df.apply(lambda row: team_data.loc[(team_data.Team == row['Team'])
                                                            & (team_data.Year == row['Season'])]['W-L%'].values[0],
                                  axis=1)
    new_df.dropna(how='all', axis=1, inplace=True)
    new_df = new_df.loc[new_df.Season != '2022']
    new_df = dc.remove_empty(new_df)
    new_df = dc.drop_zeroes(new_df)

    return new_df


def get_team_stats(team_data, gm_team):
    """
    Gather the team data from the created team in order to run analysis on it along with the historical teams

    Parameters
    ----------
    team_data : data frame
        df containing the baseline data from the teams in the 2020-2022 seasons
    gm_team : data frame
        df listing all the players from the created team

    Returns
    -------
    empty_cols : list
        list containing the columns in the team data, but not the player data
    gm_team_stats : data frame
        df of the created team in the same format of the other team data
    """
    gm_team_stats = {}
    empty_cols = []

    # gets the stats that are in the original team stats
    for label in list(team_data.columns):

        # gets the overall stats for the created team to line up with the stats of all teams
        if label in list(gm_team.columns):
            if label in AVERAGED_STATS:
                gm_team_stats[label] = [round(gm_team[label].mean(), 1)]
            else:
                # get total stats and adjust for a full season since 2022 is only 11 games so far
                gm_team_stats[label] = [gm_team[label].sum() * (16/11)]
        else:
            empty_cols.append(label)

    # turn the dictionary into a pandas dataframe
    gm_team_stats = pd.DataFrame.from_dict(gm_team_stats)
    empty_cols.remove('W-L%')

    return empty_cols, gm_team_stats


def disp_regress(df, x_feat_list, y_feat, verbose=True):
    """ linear regression, displays model w/ coef

    Args:
        df (pd.DataFrame): dataframe
        x_feat_list (list): list of all features in model
        y_feat (string): target feature
        verbose (bool): toggles command line output

    Returns:
        reg (LinearRegression): model fit to data
    """
    # initialize regression object
    reg = LinearRegression()

    # get target variable
    x = df.loc[:, x_feat_list].values
    y = df.loc[:, y_feat].values

    # fit regression
    reg.fit(x, y)

    # compute / store r2
    y_pred = reg.predict(x)

    if verbose:
        # print model
        model_str = y_feat + f' = {reg.intercept_:.2f}'
        for feat, coef in zip(x_feat_list, reg.coef_):
            model_str += f' + {coef:.2f} {feat}'
        print(model_str)

        # compute / print r2
        r2 = r2_score(y_true=y, y_pred=y_pred)
        print(f'r2 = {r2:.3}')

    return reg


def run_ml(team_data):
    """
    Run a machine logistic regression to predict the number of wins the created team will get

    Parameters
    ----------
    team_data : data frame
        df containing all the team data including that of the drafted team in the last row

    Returns
    -------
    win_loss_p : float
        the projected win/loss percentage of the drafted team
    """
    # show results of multiple regression on dataset
    x_cols = [x for x in list(team_data.columns) if x != 'W-L%']
    res = disp_regress(team_data, x_cols, 'W-L%')
    print(res)

    # run multiple regression classifier and return prediction
    x = team_data.loc[:, x_cols].values
    y = team_data.loc[:, 'W-L%'].values
    x_train = x[:-1]
    y_train = y[:-1]
    x_test = x[-1].reshape(1, -1)
    reg = LinearRegression()
    reg.fit(x_train, y_train)
    y_pred = reg.predict(x_test)

    # return the number of wins calculated from the win percentage
    wins_pred = round(y_pred[0] * 17)

    return wins_pred


def analyze_team(gm_team):
    """
    Run the analysis on the created team from the gm simulator

    Parameters
    ----------
    gm_team : data frame
        df listing all the players from the created team

    Returns
    -------
    pred_wins : int
        the predicted number of wins
    """
    # read in the created team's data and clean it TEMPORARY
    gm_team = dc.condense_positions(gm_team)

    # read in the team's data
    team_data = pd.read_csv(AGG_TEAMS)
    team_data.drop(['Team', 'Season'], axis=1, inplace=True)

    # get the overall team stats of the created team as well as the rows to be dropped and drop them
    empty_cols, gm_team_stats = get_team_stats(team_data, gm_team)
    team_data = team_data.drop(empty_cols, axis=1)

    # append the created team onto the teams_df and clean it for machine learning
    all_teams = pd.concat([team_data, gm_team_stats])
    all_teams.reset_index(inplace=True, drop=True)
    all_teams.fillna(0, inplace=True)

    # calculate the number of wins using a multiple regression
    pred_wins = run_ml(all_teams)
    print('Predicted wins: ', pred_wins)

    return pred_wins


# team_df = agg_team_stats(pd.read_csv(TEAMS, low_memory=False), pd.read_csv(ALL_PLAYERS, low_memory=False))
# team_df.to_csv('agg_teams.csv', index=False)
