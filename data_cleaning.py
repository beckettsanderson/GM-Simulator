import numpy as np
import re

KEY_STATS = ['Status', 'Player', 'Pos', 'Team', 'Age', 'No.', 'Cap Hit']
POS_COUNTS = {
    'Offense': {
        'QB': [1],
        'RB': [1],
        'WR': [3],
        'OL': [5],
        'TE': [1]
    },
    'Defense': {
        'DL': [4, 5],
        'LB': [2, 3],
        'CB': [2, 3],
        'S': [1, 2]
    },
    'Special Teams': {
        'P': [1],
        'K': [1]
    }
}


def remove_empty(df):
    """
    Remove all empty columns from a dataframe

    Parameters
    ----------
    df : data frame
        any data frame from which to remove empty columns

    Returns
    -------
    df : data frame
        the same dataframe with the empty columns removed

    """
    # get the columns that are majority empty as a list
    empty_cols = [col for col in df.columns if df[col].count() < 10]

    # remove the empty columns
    df = df.drop(empty_cols, axis=1)

    return df


def drop_zeroes(df):
    """
    Remove all columns that only have zeroes in the column from a dataframe

    Parameters
    ----------
    df : data frame
        any data frame from which to remove empty columns

    Returns
    -------
    df : data frame
        the same dataframe with the "only zeroes" columns removed

    """
    # get the columns that are majority empty as a list
    empty_cols = [col for col in df.columns if (df[col] == 0).all()]

    # remove the empty columns
    df = df.drop(empty_cols, axis=1)

    return df


def initial_player_view(df):
    """
    Set up the opening view of the player data for 'ALL' players selection

    Parameters
    ----------
    df : data frame
        data frame containing all statistics for NFL players in a certain range of years

    Returns
    -------
    df : data frame
        the same dataframe with the nonessential columns removed

    """
    # get the nonessential columns and remove them from the df
    non_key_stats = [col for col in df.columns if col not in KEY_STATS]
    df = df.drop(non_key_stats, axis=1)

    return df


def condense_positions(df):
    """
    Adjust the positions to make them more intuitive and condensed

    Parameters
    ----------
    df : data frame
        data frame containing all statistics for NFL players in a certain range of years

    Returns
    -------
    df : data frame
        the same dataframe with positions changed to be more concise

    """
    # drop players with no cap hit and LS position
    df['Cap Hit'].replace('', np.nan, inplace=True)
    df.dropna(subset=['Cap Hit'], inplace=True)
    df = df[df['Pos'] != 'LS']

    # change more complex positions into their simplified versions
    df.loc[(df["Pos"] == "OLB"), "Pos"] = 'LB'
    df.loc[(df["Pos"] == "ILB"), "Pos"] = 'LB'
    df.loc[(df["Pos"] == "MLB"), "Pos"] = 'LB'
    df.loc[(df["Pos"] == "DT"), "Pos"] = 'DL'
    df.loc[(df["Pos"] == "DE"), "Pos"] = 'DL'
    df.loc[(df["Pos"] == "SS"), "Pos"] = 'S'
    df.loc[(df["Pos"] == "FS"), "Pos"] = 'S'
    df.loc[(df["Pos"] == "FB"), "Pos"] = 'RB'
    df.loc[(df["Pos"] == "RB-WR"), "Pos"] = 'RB'
    df.loc[(df["Pos"] == "QB/TE"), "Pos"] = 'QB'
    df.loc[(df["Pos"] == "G"), "Pos"] = 'OL'
    df.loc[(df["Pos"] == "T"), "Pos"] = 'OL'
    df.loc[(df["Pos"] == "C"), "Pos"] = 'OL'
    df.loc[(df["Pos"] == "OT"), "Pos"] = 'OL'
    df.loc[(df["Pos"] == "DB"), "Pos"] = 'CB'

    return df


def to_millions(row):
    """
    Convert salaries to millions of dollars. Returns updated row.
    """
    try:
        row['Cap Hit'] = int(re.sub(r'[^0-9]', '', row["Cap Hit"]))
    except TypeError:
        row['Cap Hit'] = 0
    row['Cap Hit'] = f'${round(row["Cap Hit"] / 1000000, 1)}m'
    return row


def convert_salaries(df):
    """
    Calls helper function
    """
    return df.apply(to_millions, axis=1)
