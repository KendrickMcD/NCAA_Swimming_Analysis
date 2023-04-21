# This script is used to clean NCAA Swimming data from the USA Swimming website to make it easier for data analysis
# The first function, clean_ncaa_record_data(), is used to clean a csv file, downloaded from USA Swimming, which shows
# the progress of NCAA df over time. The function is used to remove unnecessary columns, rename columns, and convert data types
# The second function, clean_ncaa_swimming_data(), is similarly used to clean a csv file, downloaded from USA Swimming, which shows
# the top swimmers per event for a given season.

# Import libraries

import pandas as pd
import numpy as np

# Clean NCAA record data


def clean_ncaa_record_data(csv_file):

    # Read in data
    df = pd.read_csv(csv_file)

    # Remove the '=' and '"' from the column names
    df = df.applymap(lambda x: x.strip('=') if isinstance(x, str) else x)
    df = df.applymap(lambda x: x.strip('"') if isinstance(x, str) else x)
    df.columns = df.columns.str.strip('=')
    df.columns = df.columns.str.strip('"')

    # Remove unncessary columns
    df = df.drop(
        ["description", "record_tracking_list_display_format_id",
         "age_group_desc", "RecordAgeGroupId", 'RANK',
         "record_tracking_list_event_id", "location_country_code",
         "country_code",  "disable_name_swapping_yn", "location",
         "relay_lead_yn", "bios_display_swap_first_last_name_yn",
         'individual_time_id'], axis=1)

    # Rename columns
    new_names = {'swim_time': 'time_(string)',
                 'stroke_code': 'stroke',
                 'course_code': 'course',
                 'swim_date': 'date',
                 'club_code': 'team',
                 'full_name_computed': 'name',
                 'meet_name': 'meet',
                 'lsc_id': 'conference',
                 'AthleteOrgUnitId': 'team_id',
                 'MeetId': 'meet_id',
                 'PersonId': 'athlete_id',
                 'session_desc': 'session'}

    df = df.rename(columns=new_names)

    # Change date data type
    df['date'] = pd.to_datetime(df['date'])

    # Create a column for the season
    for i in range(len(df)):
        if df.loc[i, 'date'].month < 9:
            df.loc[i, 'season'] = df.loc[i, 'date'].year
        else:
            df.loc[i, 'season'] = df.loc[i, 'date'].year + 1

    # Convert time to seconds in a new column
    for i in range(len(df)):
        if len(df.loc[i, 'time_(string)']) == 5:
            df.loc[i, 'time_(seconds)'] = float(df.loc[i, 'time_(string)'])
        elif len(df.loc[i, 'time_(string)']) == 7:
            df.loc[i, 'time_(seconds)'] = \
                float(df.loc[i, 'time_(string)'][:1])*60 + \
                float(df.loc[i, 'time_(string)'][2:4]) +\
                float(df.loc[i, 'time_(string)'][5:])/100
        elif len(df.loc[i, 'time_(string)']) == 8:
            df.loc[i, 'time_(seconds)'] = \
                float(df.loc[i, 'time_(string)'][:2])*60 + \
                float(df.loc[i, 'time_(string)'][3:5]) +\
                float(df.loc[i, 'time_(string)'][6:])/100

    # Reorder columns
    new_order = ['name', 'distance',
                 'stroke', 'course',
                 'gender', 'time_(string)',
                 'time_(seconds)',
                 'date', 'season',
                 'team', 'conference',
                 'meet', 'session',
                 'event_id', 'athlete_id',
                 'team_id', 'meet_id']

    df = df[new_order]

    # Remove incomplete string from lsc_id
    df['conference'] = df['conference'].str[:-3]

    # Convert distance to integer
    df['distance'] = df['distance'].astype(int)

    # Convert IDs to integers
    df['event_id'] = df['event_id'].astype(int)
    df['team_id'] = df['team_id'].astype(int)
    df['meet_id'] = df['meet_id'].astype(int)
    df['athlete_id'] = df['athlete_id'].astype(int)

    # Convert distance to integer
    df['distance'] = df['distance'].astype(int)

    # Remove rows that share a meet_id, athlete_id, and event_id
    df = df.drop_duplicates(
        subset=['meet_id', 'athlete_id', 'event_id'], keep='first').reset_index(drop=True)

    # Sort the dataframe by event_id, gender, and time in ascending order
    df = df.sort_values(['event_id', 'gender', 'time_(seconds)'])

    # Calculate the time difference between consecutive df within each event/gender group
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

    for i in range(len(df)):
        val = df.loc[i, 'record_broken_by']
        if np.isnan(val):
            pass
        else:
            # Otherwise, set record_broken_by to the time difference between the record and the next record
            # and calculate the percentage improvement
            df.loc[i, 'record_broken_by'] = \
                df.loc[i, 'record_broken_by']
            df.loc[i, 'record_improvement_%'] = \
                (df.loc[i, 'record_broken_by'] /
                 df.loc[i+1, 'time_(seconds)'])*100

    return df

# Clean NCAA swimming data


def clean_ncaa_swimming_data(csv_file):
    df = pd.read_csv(csv_file)

    # Remove the '=' and '"' from the column names
    df = df.applymap(lambda x: x.strip('=') if isinstance(x, str) else x)
    df = df.applymap(lambda x: x.strip('"') if isinstance(x, str) else x)
    df.columns = df.columns.str.strip('=')
    df.columns = df.columns.str.strip('"')

    # Remove unncessary columns
    df = df.drop(["team_code", "converted_time_flag",
                  "alt_adjust_flag", "elig_period_code",
                  "standard_name", "RANK",
                  "full_desc_intl", "fina_points",
                  "country_code", "meet_city",
                  "time_is_for_ineligible_secondary_team_yn"], axis=1)

    # Rename columns
    new_names = {'full_desc': 'event',
                 'swim_time_as_time': 'time_(HH:MM:SS)',
                 'swim_time': 'time_(string)',
                 'swim_time_sec': 'time_(seconds)',
                 'swim_date': 'date',
                 'team_short_name': 'team',
                 'full_name_computed': 'name',
                 'meet_name': 'meet'}

    df = df.rename(columns=new_names)

    # Convert swim_time to second and milliseconds
    df['time_(HH:MM:SS)'] = pd.to_timedelta(df['time_(HH:MM:SS)'])
    df['time_(seconds)'] = df['time_(HH:MM:SS)'] / pd.Timedelta(seconds=1)

    # Change date data type
    df['date'] = pd.to_datetime(df['date'])
    df['birth_date'] = pd.to_datetime(df['birth_date'])

    # Create a column for the season
    for i in range(len(df)):
        if df.loc[i, 'date'].month < 9:
            df.loc[i, 'season'] = df.loc[i, 'date'].year
        else:
            df.loc[i, 'season'] = df.loc[i, 'date'].year + 1

    # Split event into distance and stroke
    for i in range(len(df)):
        split_values = df['event'][i].split(' ')
        if len(split_values) == 4:
            df.loc[i, 'distance'] = split_values[0]
            df.loc[i, 'stroke'] = split_values[1]
            df.loc[i, 'course'] = split_values[2]
            df.loc[i, 'gender'] = split_values[3]
        elif len(split_values) == 5:
            df.loc[i, 'distance'] = split_values[0]
            df.loc[i, 'stroke'] = split_values[1] + ' ' + split_values[2]
            df.loc[i, 'course'] = split_values[3]
            df.loc[i, 'gender'] = split_values[4]

    # Convert event_id to integer
    df['event_id'] = df['event_id'].astype(int)

    # Reorder the text in the name column
    for i in range(len(df)):
        split_name = df['name'][i].split(', ')
        df.loc[i, 'name'] = split_name[1] + ' ' + split_name[0]
        split_school = df['team'][i].split(', ')
        if len(split_school) == 2:
            df.loc[i, 'team'] = split_school[1] + \
                ' ' + split_school[0]
        elif len(split_school) == 3:
            df.loc[i, 'team'] = split_school[1] + \
                ' ' + split_school[0] + ' ' + split_school[2]
        else:
            df.loc[i, 'team'] = split_school[0]

    # Reorder columns
    new_order = ['name', 'event', 'distance', 'stroke', 'course', 'gender',
                 'time_(string)', 'time_(seconds)', 'time_(HH:MM:SS)',
                 'date', 'season', 'team', 'meet',
                 'birth_date', 'event_id']
    df = df.reindex(columns=new_order)

    # Remove observations from invalid events
    valid_events = ['50 Freestyle', '100 Freestyle', '200 Freestyle', '500 Freestyle', '1000 Freestyle', '1650 Freestyle',
                    '100 Backstroke', '200 Backstroke',
                    '100 Breaststroke', '200 Breaststroke',
                    '100 Butterfly', '200 Butterfly',
                    '200 Individual Medley', '400 Individual Medley',
                    '200 Medley Relay', '400 Medley Relay',
                    '200 Freestyle Relay', '400 Freestyle Relay', '800 Freestyle Relay']

    for i in range(len(df)):
        event = df['distance'][i] + ' ' + df['stroke'][i]
        if event not in valid_events:
            df = df.drop(i)

    df['distance'] = df['distance'].astype(int)

    # Return cleaned dataframe
    return df

# Calculate record stats


def calculate_record_stats(df):

    # Remove rows that share a meet_id, athlete_id, and event_id
    df = df.drop_duplicates(
        subset=['meet_id', 'athlete_id', 'event_id'], keep='first').reset_index(drop=True)

    # Sort the dataframe by event_id, gender, and time in ascending order
    df = df.sort_values(['event_id', 'gender', 'time_(seconds)'])

    # Calculate the time difference between consecutive df within each event/gender group
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

    for i in range(len(df)):
        # Get the current athlete and event IDs
        record_sum = df.loc[i, 'record_broken_by']
        athlete_id = df.loc[i, 'athlete_id']
        event_id = df.loc[i, 'event_id']

        # Check if the current observation has a record_broken_by value
        if np.isnan(record_sum):
            pass
        else:

            # Calculate the record improvement percentage
            df.loc[i, 'record_improvement_%'] = (
                record_sum/df.loc[i+1, 'time_(seconds)'])*100

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
                    new_record_holder_sum/((df.loc[i+1, 'time_(seconds)'])+new_record_holder_sum))*100

            else:
                # Set the remaining values to NaN
                df.loc[i, 'new_record_holder_broken_by'] = np.nan
                df.loc[i, 'new_record_holder_improvement_%'] = np.nan

    return df
