import numpy as np
from bs4 import BeautifulSoup as BS
from bs4 import Comment
import requests
import pandas as pd
import warnings
import time

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter("ignore", UserWarning)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)


def scrape_salaries(starting_season=None):
    """
    Get all salaries from spotrac.com

    Parameters
    ----------
    starting_season : int
        Integer representing the first season to gather data from

    Returns
    -------
    df : df
        A dataframe of all players and their salary information.
    """

    # get links to all team pages
    url = 'https://www.spotrac.com'
    soup = BS(requests.get(url + '/nfl').text, features='html.parser')
    div = soup.find_all('a', class_='team-name')
    team_urls = [x.attrs['href'] for x in div]

    if not starting_season:
        seasons = [2022]
    else:
        seasons = [x for x in range(starting_season, 2023, 1) if x >= 2020]

    df = pd.DataFrame()

    for season in seasons:
        # get dataframe for each team then add to existing dataframe
        for team_url in team_urls:
            active_squad = pd.read_html(team_url + f'/{season}/')[0]
            active_squad['Team'] = ' '.join([x.capitalize() for x in team_url.split('/')[-3].split('-')])
            cols = list(active_squad.columns)
            player_col = [col for col in cols if 'Active Players' in col][0]
            cols.pop(cols.index(player_col))
            cols.insert(0, 'Player')
            active_squad.columns = cols
            active_squad = active_squad.replace('(', '').replace(')', '').replace('$', '').replace(',', '')
            active_squad['Season'] = [season] * len(active_squad)
            df = pd.concat([df, active_squad], axis=0).reset_index(drop=True)

    # filter columns, sort, reset index
    df = df[['Player', 'Season', 'Team', 'Base Salary', 'Cap Hit', 'Cap %']]
    df.sort_values(by=['Season', 'Team', 'Player'], inplace=True,
                   ascending=[False, True, True])
    df.reset_index(drop=True, inplace=True)

    return df


def sjoin(x):
    return ';'.join(x[x.notnull()].astype(str)).split(';')[0]


def get_players_df(starting_season=None):
    """
    Get a dataframe of all player data starting from a given year.

    Parameters
    ----------
    starting_season : int (default None)
        The first season we're interested in.

    Returns
    -------
    df : df
        A dataframe with all player data.
    """

    url = 'https://www.pro-football-reference.com'
    if not starting_season:
        seasons = [2022]
    else:
        seasons = [x for x in range(starting_season, 2023, 1) if x > 1988]

    # initialize overall dataframe
    df = pd.DataFrame()

    # get data for each season
    for season in seasons:

        # initialize season_df
        season_df = pd.DataFrame()

        # get the url for each team
        soup = BS(requests.get(url + f'/years/{season}/#').text, features='html.parser')
        conf_tables = soup.find_all('tbody')[:2]
        team_urls = [url + x.attrs['href'] for y in conf_tables for x in y.find_all('a')]

        # go through each team in a year
        for team_url in team_urls:
            team_df = pd.DataFrame()
            team_df['Player'] = np.NaN
            team_soup = BS(requests.get(team_url).text, features='html.parser')
            team_name = team_soup.find('h1').find_all('span')[1].text
            for comment in team_soup(text=lambda text: isinstance(text, Comment)):
                if 'class="table_container"' in comment.string:
                    tag = BS(comment, 'html.parser')
                    comment.replace_with(tag)
            tables_soup = [y.find('table') for y in
                           [x.find('div', class_=lambda j: j and 'table_container' in j)
                            for x in team_soup.find_all('div', class_=lambda
                               i: i and 'table_wrapper' in i)]]

            # create a df with all the team's data for a given year
            for idx in range(len(tables_soup)):
                table_df = pd.read_html(str(tables_soup))[idx]

                # drop multiindex and rename columns
                if table_df.columns.nlevels > 1:
                    cols = list(table_df.columns)
                    new_cols = []
                    for col in cols:
                        if 'Unnamed' in col[0]:
                            new_cols.append(col[1])
                        else:
                            new_cols.append(f'{col[0][:3]}_{col[1]}')
                    table_df = table_df.droplevel(0, axis=1)
                    table_df.columns = new_cols

                # add to team_df if it's player data
                if 'Player' in table_df.columns:
                    # merge duplicate columns and convert to numeric when possible
                    team_df = team_df.groupby(level=0, axis=1).first()
                    table_df = table_df.groupby(level=0, axis=1).first()
                    table_df = table_df.apply(pd.to_numeric, errors='ignore')
                    team_df = team_df.apply(pd.to_numeric, errors='ignore')

                    # merge dfs
                    team_df = team_df.merge(table_df, how='outer')

            # finalize team dataframe
            team_df = team_df.groupby('Player').first().reset_index()
            team_df['Team'] = [team_name] * len(team_df)
            team_df['Season'] = [season] * len(team_df)
            drop_rows = ['Team Total', 'Opp Total', 'Lg Rank Defense', 'Lg Rank Offense', 'Opp. Stats', 'Team Stats']
            team_df = team_df.loc[~team_df.Player.isin(drop_rows)]
            team_df.reset_index(drop=True, inplace=True)
            team_df = team_df[team_df.columns.difference(['Status', 'Details', 'Practice Status'])]

            # add the team's dataframe to the season dataframe
            season_df = pd.concat([season_df, team_df], axis=0).reset_index(drop=True)

        # add season dataframe to overall dataframe
        df = pd.concat([df, season_df], axis=0).reset_index(drop=True)

    # change column order, sort
    cols = list(df.columns)
    order = ['No.', 'Age', 'Season', 'Team', 'Pos', 'Player']
    for col in order:
        cols.pop(cols.index(col))
        cols.insert(1, col)
    df = df[cols]
    df.sort_values(by=['Season', 'Team', 'Player'], inplace=True,
                   ascending=[False, True, True])

    return df


def get_team_df(starting_season=None):
    """
    Get a dataframe of all team data starting from a given year.

    Parameters
    ----------
    starting_season : int (default None)
        The first season we're interested in.

    Returns
    -------
    df : df
        A dataframe with all team data.
    """

    url = 'https://www.pro-football-reference.com'
    if not starting_season:
        seasons = [2022]
    else:
        seasons = [x for x in range(starting_season, 2023, 1) if x > 1988]

    # initialize overall dataframe
    df = pd.DataFrame()

    # get data for each season
    for season in seasons:

        # initialize season_df
        season_df = pd.DataFrame()

        # get all comments
        soup = BS(requests.get(url + f'/years/{season}/#').text, features='html.parser')
        for comment in soup(text=lambda text: isinstance(text, Comment)):
            if 'class="table_container"' in comment.string:
                tag = BS(comment, 'html.parser')
                comment.replace_with(tag)

        # read into dfs
        conf_tables = soup.find_all('table')
        conf_lst = pd.read_html(str(conf_tables))

        for conf_df in conf_lst:
            # make single index
            # drop multiindex and rename columns
            if conf_df.columns.nlevels > 1:
                cols = list(conf_df.columns)
                new_cols = []
                for col in cols:
                    if 'Unnamed' in col[0]:
                        new_cols.append(col[1])
                    else:
                        new_cols.append(f'{col[0][:3]}_{col[1]}')
                conf_df = conf_df.droplevel(0, axis=1)
                conf_df.columns = new_cols

            # only look at dfs tracking by team
            if 'Tm' not in conf_df.columns:
                continue

            # remove unnecessary columns, process strings, convert to numeric
            conf_df = conf_df[~conf_df.Tm.str.contains("AFC")]
            conf_df = conf_df[~conf_df.Tm.str.contains("NFC")]
            conf_df['Tm'] = conf_df.Tm.str.replace('[^a-zA-Z0-9 ]', '')
            # conf_df['Player'] = conf_df.Player.str.replace('[^a-zA-Z0-9 ]', '')
            conf_df = conf_df.rename({'Tm': 'Team'}, axis='columns')
            conf_df = conf_df.groupby(level=0, axis=1).first()
            conf_df = conf_df.apply(pd.to_numeric, errors='ignore')
            season_df = season_df.apply(pd.to_numeric, errors='ignore')
            if len(season_df) != 0:
                season_df = season_df.groupby(level=0, axis=1).first()
                season_df = season_df.merge(conf_df, how='outer')
            else:
                season_df = conf_df.copy()

        # add year and aggregate rows
        season_df['Year'] = [season] * len(season_df)
        season_df = season_df.groupby('Team', axis=0).first()
        season_df.reset_index(inplace=True)

        if len(df) != 0:
            df = df.merge(season_df, how='outer')
        else:
            df = season_df.copy()
        time.sleep(5)

    # reset index
    df.reset_index(drop=True, inplace=True)

    # fix column order
    cols = list(df.columns)
    cols.pop(cols.index('Team'))
    cols.pop(cols.index('Year'))
    cols.insert(0, 'Year')
    cols.insert(0, 'Team')
    df = df[cols]
    if 'Yds.1' in list(df.columns):
        df = df.rename({'Yds.1': 'Yds_lost'}, axis='columns')

    # drop unnecessary rows
    df = df[~df.Team.isin(['Avg Team', 'Avg TmG', 'League Total'])]
    df = df[df.Position.isnull()]
    df.drop(['T', 'Position', 'Reason'], axis=1, inplace=True)

    return df


def players_and_salaries(starting_season=None):
    """
    Get player and salary dfs, merge them and return.

    Parameters
    ----------
    starting_season : int
        The first season we want data from.

    Returns
    -------
    df : df
        A combined dataframe of player and salary data going back to the starting season.

    team_df : df
        A dataframe with team data.

    """

    # get player_df and salary_df, merge
    player_df = get_players_df(starting_season=starting_season)
    salary_df = scrape_salaries(starting_season=starting_season)
    player_df['Player'] = player_df['Player'].astype(str)
    salary_df['Player'] = salary_df['Player'].astype(str)
    player_df['Season'] = player_df['Season'].astype(int)
    salary_df['Season'] = salary_df['Season'].astype(int)
    df = player_df.merge(salary_df, how='left')

    # filter not-null, sort
    df = df[(df['Age'].notna()) & (df['No.'].notna())]
    df.sort_values(by=['Season', 'Team', 'Player'], inplace=True,
                   ascending=[False, True, True])

    # add id column
    df.reset_index(drop=True, inplace=True)
    df.reset_index(inplace=True)
    df = df.rename({'index': 'id', 'Yds.1': 'Yds_lost'}, axis='columns')
    df['id'] = df['id'].apply(lambda x: '{0:0>5}'.format(x))
    df.drop('#Dr', axis=1, inplace=True)

    return df

def scrape_column_names():
    """
    Get all column abbreviations and their corresponding full name.

    Parameters
    ----------
    None

    Returns
    -------
    dct : dct
        A dictionary where the keys are col. abbreviations and values are col. names.
    """

    # get all table headers, uncomment comments
    url = 'https://www.pro-football-reference.com/teams/nyg/2022.htm'
    soup = BS(requests.get(url).text, features='html.parser')
    for comment in soup(text=lambda text: isinstance(text, Comment)):
        if 'class="table_container"' in comment.string:
            tag = BS(comment, 'html.parser')
            comment.replace_with(tag)
    heads = soup.find_all('thead')
    headers = [x.find_all('tr') for x in heads]
    headers = [[x.find_all('th') for x in y] for y in headers]
    cols = []

    for y in headers:
        # if not multiindex
        if len(y) == 1:
            cols += [{'label': x.attrs['aria-label'], 'value': x.text} for x in y[0]]

        # if multiindex
        if len(y) != 1:
            col_abbr = []
            for x in y[0]:
                # check if higher index has text
                if not x.text:
                    # might span multiple columns, or not
                    if 'colspan' in x.attrs.keys():
                        col_abbr += [None] * int(x.attrs['colspan'])
                    else:
                        col_abbr.append(None)

                # if it has text, make first three letters abbreviation
                else:
                    label = x.text
                    col_abbr += [label[:3]] * int(x.attrs['colspan'])

            # get all stat names
            for idx, x in enumerate(y[1]):
                if col_abbr[idx]:
                    cols.append({'label': x.attrs["aria-label"].strip(),
                                 'value': f'{col_abbr[idx].strip()}_{x.text.strip()}'})
                elif x.attrs['aria-label']:
                    cols.append({'label': x.attrs["aria-label"].strip(), 'value': x.text.strip()})

    # remove duplicates
    dup_lst = []
    final_cols = []
    for x in cols:
        if x['value'] in dup_lst:
            continue
        else:
            final_cols.append(x)
            dup_lst.append(x['value'])

    return final_cols


def main():
    # df = players_and_salaries(starting_season=2000)
    # df = get_team_df(starting_season=2000)
    # df = get_players_df(starting_season=2022)
    # df.to_csv('2020_to_2022_players.csv')
    # df.to_csv('2000_to_2022_teams_test.csv', index=False)
    # df = get_players_df()
    cols = scrape_column_names()
    print(cols)



main()
