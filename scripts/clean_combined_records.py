# This script is intended to clean and correct the combined records from the USA Swiming website
# and those collected via web scraping from the SwimSwam.com NCAA meet results archive

# Import libraries
import pandas as pd
import numpy as np
import re

# Remove duplicate records


def drop_duplicates(df):
    # Drop duplicate records
    df.drop_duplicates(subset=['name', 'time_(seconds)',
                               'season'], keep='first', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

# Clean the combined USA Swimming and SwimSwam records, after they have
# been combined into a single dataframe


def clean_combined_records(df):

    team_dict = {
        'Cal|CAL|Berkeley': 'California',
        'Arizona St|ASU': 'Arizona State',
        'ARIZ|ArizonaL': 'Arizona',
        'Southern Cal|Southern Cali|USC': 'Southern California',
        'AUB': 'Auburn',
        'NC State|NCS': 'NC State',
        'MICH|Michigan': 'Michigan',
        'FLOR': 'Florida',
        'TENN': 'Tennessee',
        'WISC': 'Wisconsin',
        'IU|Indiana': 'Indiana',
        'ND|Notre Dame': 'Notre Dame',
        'NW|Northwestern': 'Northwestern',
        'HARV': 'Harvard',
        'Tex|TEX': 'Texas',
        'Virginia|UVA': 'Virginia',
        'Stanford|STAN': 'Stanford',
        ' Georgia|GeorgiaS|UGA': 'Georgia',
        'Florida|Floid': 'Florida'
    }

    # Create regular expression patterns for each team name
    patterns = {re.compile(key): value for key, value in team_dict.items()}

    # Function to map team names to team IDs using regular expressions
    def map_team_name(name):
        for pattern, team in patterns.items():
            if pattern.search(name):
                return team
        return name

    # Apply the map_team_name function to the 'team' column to create a new 'team_id' column
    df['team'] = df['team'].apply(map_team_name)

    # ASSIGN ATHLETE_IDs

    # Show rows with no athlete_id value
    missing_athlete_id = df[(df['athlete_id'].isnull()) & (
        ~df['stroke'].str.contains('Relay'))]['name'].unique()

    has_athlete_id = df[(df['athlete_id'].notnull()) & (
        ~df['stroke'].str.contains('Relay'))]['name'].unique()

    # See which athletes in the array missing_athlete_id are in the has_athlete_id array
    to_assign_id = missing_athlete_id[np.isin(
        missing_athlete_id, has_athlete_id)]

    id_to_assign = {}
    for name in to_assign_id:
        # Search df['name'] for the name and locate any non-null athlete_id values
        athlete_id = df[(df['name'] == name) & (
            df['athlete_id'].notnull())]['athlete_id'].unique()
        # Assign the athlete_id value to the name in the dictionary
        id_to_assign[name] = athlete_id[0]

    # Use the dictionary to assign the athlete_id values to the missing values
    for name, athlete_id in id_to_assign.items():
        df.loc[df['name'] == name, 'athlete_id'] = athlete_id

    # Show df rows missing athlete_id values
    still_missing = df[(df['athlete_id'].isnull()) & (
        ~df['stroke'].str.contains('Relay'))]['name'].unique()

    for name in still_missing:
        random_id = np.random.randint(100000, 999999)
        df.loc[df['name'] == name, 'athlete_id'] = random_id

    # ASSIGN TEAM IDs

    existing_team_ids = df['team_id'].unique()
    team_names = df['team'].unique()
    team_dict = {}

    for team_name in team_names:
        # Check if team ID already exists for this team name
        team_id = df.loc[df['team'] == team_name, 'team_id'].iloc[0]
        if np.isnan(team_id):
            # Assign new ID if team has no existing ID
            team_id = len(team_dict) + 1
            team_dict[team_name] = team_id
        else:
            team_dict[team_name] = team_id

    df['team_id'] = df['team'].map(team_dict)

    # ASSIGN EVENT_IDs

    # Create a dictionary of event_id values based on pairs of distance, stroke, and event_id in the df
    event_id_dict = {
        50: {'FR': 1},
        100: {'FR': 2, 'BK': 7, 'BR': 9, 'FL': 11},
        200: {'FR': 3, 'BK': 8, 'BR': 10, 'FL': 12, 'IM': 13, 'Freestyle Relay': 15, 'Medley Relay': 18},
        400: {'IM': 14, 'Freestyle Relay': 16, 'Medley Relay': 19},
        500: {'FR': 4},
        800: {'Freestyle Relay': 17},
        1000: {'FR': 5},
        1650: {'FR': 6}
    }

    # Assign event_id values to the df based on the event_id_dict
    for distance, stroke, event_id in zip(df['distance'], df['stroke'], df['event_id']):
        df.loc[(df['distance'] == distance) & (df['stroke'] == stroke),
               'event_id'] = event_id_dict[distance][stroke]

    df.sort_values(by=['event_id', 'gender'], ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Correct Texas A&M team name
    index = df[df['name'] == 'Breeja Larson'].index
    df.loc[index, 'team'] = 'Texas A&M'

    index = df[df['name'] == 'Natalie Coughlin'].index
    df.loc[index, 'team'] = 'California'

    index = df[df['name'] == 'Simon Burnett'].index
    df.loc[index, 'team'] = 'Arizona'

    df = df.sort_values(
        by=['season'], ascending=False).sort_values(
        by=['event_id', 'gender', 'time_(seconds)'], ascending=[True, True, True]).reset_index(drop=True)

    columns = ['name', 'distance',
               'stroke', 'course',
               'gender', 'season',
               'time_(seconds)', 'time_(string)',
               'date', 'team',
               'conference', 'meet',
               'event_id', 'athlete_id', 'team_id',
               'session', 'meet_id'
               ]

    df = df[columns]
    return df


def calculate_seasons_between_records(df):
    df['seasons_between_records'] = abs(-df.groupby(
        ['event_id', 'gender'])['season'].diff().shift(-1))
    return df


def calculate_seasons_between_new_holders(df):
    # Reverse the order of the DataFrame
    df = df.iloc[::-1].reset_index(drop=True)

    # Identify when a new record holder appears
    df['new_record_holder'] = df['name'].ne(df['name'].shift())

    # Initialize the 'seasons_between_new_holders' column with NaN values
    df['seasons_between_new_holders'] = np.nan

    # Calculate the difference in seasons between new record holders
    df.loc[df['new_record_holder'], 'seasons_between_new_holders'] = df[df['new_record_holder']
                                                                        ]['season'].diff().apply(lambda x: x if x >= 0 else np.nan)

    # Reverse the order of the DataFrame again
    df = df.iloc[::-1].reset_index(drop=True)

    return df

# FACT CHECK RECORDS

# After reviewing the combined dataframe and cleaning it, there are still some records that need to be corrected,
# either because they are incorrect or because they are missing. This function will correct those records.
# This is based on research with sources recorded in a jupyter notebook.


def fact_checked_records(df):

    # Post Fact-Checking Manual Cleaning

    np.random.seed(23)

    # Add Missing Records

    # Add Tom Jager 50 Free record
    ervin_50_free_index = df[(df['name'] == 'Anthony Ervin') &
                             (df['event_id'] == 1)].index[0]
    tom_jager_50_free = df.loc[ervin_50_free_index].copy()
    tom_jager_50_free['name'] = 'Tom Jager'
    tom_jager_50_free['season'] = 1990
    tom_jager_50_free['date'] = pd.to_datetime('1990-01-01')
    tom_jager_50_free['team'] = 'UCLA'
    tom_jager_50_free['athlete_id'] = np.random.randint(100000, 999999)

    # Add Maritza Correia 100 Free record
    correia_100_free_index = df[(df['name'] == 'Maritza Correia') &
                                (df['event_id'] == 1)].index[0]
    correia_100_free = df.loc[correia_100_free_index].copy()
    correia_100_free['event_id'] = 2
    correia_100_free['distance'] = 100
    correia_100_free['time_(string)'] = '47.56'
    correia_100_free['time_(seconds)'] = 47.56
    correia_100_free['season'] = 2002
    correia_100_free['date'] = pd.to_datetime('2002-01-01')

    # Add new 100 Back record for Brian Retterer
    retterer_100_back_index = df[(df['name'] == "Brian Retterer") &
                                 (df['event_id'] == 8)].index[0]
    retterer_100_back = df.loc[retterer_100_back_index].copy()
    retterer_100_back['event_id'] = 7
    retterer_100_back['distance'] = 100
    retterer_100_back['time_(string)'] = '45.43'
    retterer_100_back['time_(seconds)'] = 45.43
    retterer_100_back['season'] = 1995
    retterer_100_back['date'] = pd.to_datetime('1995-01-01')

    # Add new 100 back record for Natalie Coughlin
    coughlin_100_back1_index = df[(df['name'] == 'Natalie Coughlin') &
                                  (df['time_(seconds)'] == 50.57)].index[0]
    coughlin_100_back1 = df.loc[coughlin_100_back1_index].copy()
    coughlin_100_back1['time_(seconds)'] = 51.23
    coughlin_100_back1['time_(string)'] = '51.23'
    coughlin_100_back1['season'] = 2001
    coughlin_100_back1['date'] = pd.to_datetime('2001-01-01')

    # Add new 100 back record for Natalie Coughlin
    coughlin_100_back2_index = df[(df['name'] == 'Natalie Coughlin') &
                                  (df['time_(seconds)'] == 50.57)].index[0]
    coughlin_100_back2 = df.loc[coughlin_100_back1_index].copy()
    coughlin_100_back2['time_(seconds)'] = 51.66
    coughlin_100_back2['time_(string)'] = '51.66'
    coughlin_100_back2['season'] = 2001
    coughlin_100_back2['date'] = pd.to_datetime('2001-01-01')

    # Add new 100 back record for Marylyn Chiang
    chiang_100_back_index = df[(df['name'] == 'Natalie Coughlin') &
                               (df['time_(seconds)'] == 49.97)].index[0]
    chiang_100_back = df.loc[chiang_100_back_index].copy()
    chiang_100_back['name'] = 'Marylyn Chiang'
    chiang_100_back['time_(seconds)'] = 52.36
    chiang_100_back['time_(string)'] = '52.36'
    chiang_100_back['season'] = 1999
    chiang_100_back['date'] = pd.to_datetime('1999-01-01')
    chiang_100_back['athlete_id'] = np.random.randint(100000, 999999)

    # Add new 200 back record for Natalie Coughlin
    coughlin_200_back1_index = df[(df['name'] == 'Natalie Coughlin') &
                                  (df['time_(seconds)'] == 109.52)].index[0]
    coughlin_200_back1 = df.loc[coughlin_200_back1_index].copy()
    coughlin_200_back1['time_(string)'] = '1:51.02'
    coughlin_200_back1['time_(seconds)'] = 111.02
    coughlin_200_back1['season'] = 2001
    coughlin_200_back1['date'] = pd.to_datetime('2001-01-01')

    # Add new 200 back record for Natalie Coughlin
    coughlin_200_back2_index = df[(df['name'] == 'Natalie Coughlin') &
                                  (df['time_(seconds)'] == 109.52)].index[0]
    coughlin_200_back2 = df.loc[coughlin_200_back2_index].copy()
    coughlin_200_back2['time_(string)'] = '1:52.73'
    coughlin_200_back2['time_(seconds)'] = 112.73
    coughlin_200_back2['season'] = 2001
    coughlin_200_back2['date'] = pd.to_datetime('2001-01-01')

    # Add new 200 back record for Whitney Hedgepeth
    hedgepeth_200_back_index = df[(df['name'] == 'Natalie Coughlin') &
                                  (df['time_(seconds)'] == 109.52)].index[0]
    hedgepeth_200_back = df.loc[hedgepeth_200_back_index].copy()
    hedgepeth_200_back['name'] = 'Whitney Hedgepeth'
    hedgepeth_200_back['time_(string)'] = '1:52.98'
    hedgepeth_200_back['time_(seconds)'] = 112.98
    hedgepeth_200_back['season'] = 1992
    hedgepeth_200_back['date'] = pd.to_datetime('1992-01-01')
    hedgepeth_200_back['team'] = 'Florida'
    hedgepeth_200_back['athlete_id'] = np.random.randint(100000, 999999)

    # Add Kristy Kowal 100 breast record in 1998
    kowal_100_breast_index = df[(df['name'] == 'Annie Chandler') &
                                (df['time_(seconds)'] == 58.06)].index[0]
    kowal_100_breast = df.loc[kowal_100_breast_index].copy()
    kowal_100_breast['name'] = 'Kristy Kowal'
    kowal_100_breast['time_(string)'] = '59.05'
    kowal_100_breast['time_(seconds)'] = 59.05
    kowal_100_breast['season'] = 1998
    kowal_100_breast['date'] = pd.to_datetime('1998-01-01')
    kowal_100_breast['team'] = 'Georgia'
    kowal_100_breast['athlete_id'] = np.random.randint(100000, 999999)

    # Change Annie Chandler 100 breast record to 2010
    df.loc[df['name'] == 'Annie Chandler', ['date', 'season']] = [
        pd.to_datetime('2010-01-01'), 2010]

    # Add Misty Hyman 1998 Record
    hyman_100_fly_index = df[(df['name'] == 'Natalie Coughlin') &
                             (df['time_(seconds)'] == 51.18)].index[0]
    hyman_100_fly = df.loc[hyman_100_fly_index].copy()
    hyman_100_fly['name'] = 'Misty Hyman'
    hyman_100_fly['time_(string)'] = '51.34'
    hyman_100_fly['time_(seconds)'] = 51.34
    hyman_100_fly['season'] = 1998
    hyman_100_fly['date'] = pd.to_datetime('1998-01-01')
    hyman_100_fly['team'] = 'Stanford'
    hyman_100_fly['athlete_id'] = np.random.randint(100000, 999999)

    # Add Gil Stovall record in 200 fly
    stovall_200_fly_index = df[(df['name'] == 'Shaune Fraser') &
                               (df['time_(seconds)'] == 101.17)].index[0]
    stovall_200_fly = df.loc[stovall_200_fly_index].copy()
    stovall_200_fly['name'] = 'Gil Stovall'
    stovall_200_fly['time_(string)'] = '1:41.33'
    stovall_200_fly['time_(seconds)'] = 101.33
    stovall_200_fly['season'] = 2008
    stovall_200_fly['date'] = pd.to_datetime('2008-01-01')
    stovall_200_fly['team'] = 'Georgia'
    stovall_200_fly['athlete_id'] = np.random.randint(100000, 999999)

    # Add George Bovell record in 200 IM in 2003
    bovell_200_im_index = df[(df['name'] == 'Ryan Lochte') &
                             (df['time_(seconds)'] == 101.76)].index[0]
    bovell_200_im = df.loc[bovell_200_im_index].copy()
    bovell_200_im['name'] = 'George Bovell'
    bovell_200_im['time_(string)'] = '1:42.66'
    bovell_200_im['time_(seconds)'] = 102.66
    bovell_200_im['season'] = 2003
    bovell_200_im['date'] = pd.to_datetime('2003-01-01')
    bovell_200_im['team'] = 'Auburn'
    bovell_200_im['athlete_id'] = np.random.randint(100000, 999999)

    # Change first Maggie Bowen 200 IM record to 2000
    df.loc[(df['name'] == 'Maggie Bowen') & (df['time_(seconds)'] == 115.49),
           ['date', 'season']] = [pd.to_datetime('2000-01-01'), 2000]

    # Add 2 new Julia Smit records from 2009
    smit_400_im_index = df[(df['name'] == 'Julia Smit') &
                           (df['time_(seconds)'] == 238.23)].index[0]
    smit_400_im = df.loc[smit_400_im_index].copy()
    smit_400_im['season'] = 2009
    smit_400_im['date'] = pd.to_datetime('2009-01-01')
    smit_400_im['time_(string)'] = '4:00.56'
    smit_400_im['time_(seconds)'] = 240.56

    # New Aaron Peirsol 200 back record in 2003
    peirsol_200_back_index = df[(df['name'] == 'Ryan Lochte') &
                                (df['time_(seconds)'] == 98.29)].index[0]
    peirsol_200_back = df.loc[peirsol_200_back_index].copy()
    peirsol_200_back['name'] = 'Aaron Peirsol'
    peirsol_200_back['season'] = 2003
    peirsol_200_back['date'] = pd.to_datetime('2003-01-01')
    peirsol_200_back['time_(string)'] = '1:39.16'
    peirsol_200_back['time_(seconds)'] = 99.16
    peirsol_200_back['team'] = 'Texas'
    peirsol_200_back['athlete_id'] = np.random.randint(100000, 999999)

    new_records = [tom_jager_50_free, correia_100_free,
                   retterer_100_back, coughlin_100_back1,
                   coughlin_100_back2, chiang_100_back,
                   coughlin_200_back1, coughlin_200_back2,
                   hedgepeth_200_back, kowal_100_breast,
                   hyman_100_fly, stovall_200_fly,
                   bovell_200_im, smit_400_im,
                   peirsol_200_back]

    # Convert all new records to DataFrame and concat with one another
    new_records_df = pd.DataFrame(new_records)
    new_records_df = new_records_df.reset_index(drop=True)

    # Concat new records with original DataFrame
    df = pd.concat([df, new_records_df], ignore_index=True)
    df = df.sort_values(
        by=['event_id', 'gender', 'time_(seconds)']).reset_index(drop=True)

    # Delete Inaccurate records

    # Delete Simon Burnett duplicate records
    df = df[(df['name'] != "Simon Burnett") | (
        df['season'] != 2004)]

    # Delete duplicate Natalie Coughlin 200 Fly record
    df = df[~((df['date'] == pd.to_datetime('01-01-2002'))
              & (df['time_(seconds)'] == 111.91))]
    df = df[~((df['date'] == pd.to_datetime('01-01-2002'))
              & (df['time_(seconds)'] == 102.65))]

    # Delete Peter Vanderkaay inaccurate record
    df = df[(df['name'] != "Peter Vanderkaay") | (
        df['time_(seconds)'] != 249.82)]

    # Drop Joseph Schooling duplicates
    df = df[(df['name'] != 'Joseph Schooling')]

    # Remove Kelsi Worrell/Dahlia Duplicate Records
    df = df[df['name'] != 'Kelsi Dahlia']

    # Inaccurate M 50 Free record
    df = df[df['name'] != 'Roland Schoeman']

    # Inaccurate M 200 Fly record
    df = df[df['name'] != 'Mark Dylla']

    df.reset_index(drop=True, inplace=True)

    df = df.sort_values(
        by=['season'], ascending=False).sort_values(
        by=['event_id', 'gender', 'time_(seconds)'], ascending=[True, True, True]).reset_index(drop=True)

    return df

# CALCULATE RECORD STATS

# Once the combined data has been thoroughly cleaned and corrected,
# we can calculate statistics about record improvements


def calculate_seasons_between_records(df):
    df['seasons_between_records'] = abs(-df.groupby(
        ['event_id', 'gender'])['season'].diff().shift(-1))
    return df


def calculate_seasons_between_new_holders(df):
    # Reverse the order of the DataFrame
    df = df.iloc[::-1].reset_index(drop=True)

    # Identify when a new record holder appears
    df['new_record_holder'] = df['athlete_id'].ne(df['athlete_id'].shift())

    # Initialize the 'seasons_between_new_holders' column with NaN values
    df['seasons_between_new_holders'] = np.nan

    # Calculate the difference in seasons between new record holders
    df.loc[df['new_record_holder'], 'seasons_between_new_holders'] = df[df['new_record_holder']
                                                                        ]['season'].diff().apply(lambda x: x if x >= 0 else np.nan)

    # Reverse the order of the DataFrame again
    df = df.iloc[::-1].reset_index(drop=True)

    return df


def calculate_record_stats(df):

    df = df.sort_values(
        by=['season'], ascending=False).sort_values(
        by=['event_id', 'gender', 'time_(seconds)'], ascending=[True, True, True]).reset_index(drop=True)

    # CALCULATE RECORD IMPROVEMENT STATS

    # Sort the dataframe by event_id, gender, and time in ascending order
    time_diff = df.groupby(['event_id', 'gender'])['time_(seconds)'].diff()
    time_diff = time_diff.fillna(0)
    time_diff = time_diff[1:]
    time_diff = pd.concat([time_diff, pd.Series([np.nan])], ignore_index=True)

    # For the last record within each event/gender group, set the record_broken_by value to NaN
    last_record_mask = df.groupby(['event_id', 'gender']).tail(1).index
    time_diff[last_record_mask] = np.nan

    # For df that are not new df, set the record_broken_by value to 0
    time_diff[time_diff <= 0] = 0

    # Add the record_broken_by column to the dataframe
    df['record_broken_by'] = time_diff

    # Initialize a dictionary to keep track of the new values for each athlete and event combination
    total_improvement = {}

    # Calculate record improvement and new record holder improvement
    for i in range(len(df)):
        record_sum = df.loc[i, 'record_broken_by']
        athlete_id = df.loc[i, 'athlete_id']
        event_id = df.loc[i, 'event_id']

        if np.isnan(record_sum):
            pass
        else:

            # Calculate the record improvement percentage
            df.loc[i, 'record_improvement_%'] = (
                record_sum/df.loc[i+1, 'time_(seconds)'])*100

            # Skip all relays for new_record_holder stats
            if 'Relay' in df.loc[i, 'stroke']:
                continue
            else:

                # Check if the current athlete and event combination already has a record_sum
                if (athlete_id, event_id) not in total_improvement:
                    # Calculate the sum of record_broken_by for the current athlete and event IDs
                    new_record_holder_sum = df[(df['athlete_id'] == athlete_id) & (
                        df['event_id'] == event_id)]['record_broken_by'].sum()
                    total_improvement[(athlete_id, event_id)
                                      ] = new_record_holder_sum
                else:
                    # Use the existing record_sum for the current athlete and event combination
                    new_record_holder_sum = total_improvement[(
                        athlete_id, event_id)]

                # Update the new_record_holder_broken_by column in the first observation for the athlete and event combination
                if i == df[(df['athlete_id'] == athlete_id) & (df['event_id'] == event_id)].index[0]:
                    df.loc[i, 'new_record_holder_broken_by'] = new_record_holder_sum
                    df.loc[i, 'new_record_holder_improvement_%'] = (
                        new_record_holder_sum/((df.loc[i, 'time_(seconds)'])+new_record_holder_sum))*100

                else:
                    # Set the remaining values to NaN
                    df.loc[i, 'new_record_holder_broken_by'] = np.nan
                    df.loc[i, 'new_record_holder_improvement_%'] = np.nan

    df = calculate_seasons_between_records(df)
    df = calculate_seasons_between_new_holders(df)

    columns = [
        'name', 'distance', 'stroke', 'course', 'gender', 'season',
        'time_(seconds)', 'time_(string)',
        'record_broken_by', 'record_improvement_%',
        'new_record_holder', 'new_record_holder_broken_by', 'new_record_holder_improvement_%',
        'seasons_between_records', 'seasons_between_new_holders',
        'team', 'conference', 'date', 'meet',
        'event_id', 'athlete_id', 'team_id', 'session', 'meet_id'
    ]

    df = df[columns]

    df = df.sort_values(
        by=['season'], ascending=False).sort_values(
        by=['event_id', 'gender', 'time_(seconds)'], ascending=[True, True, True]).reset_index(drop=True)

    return df
