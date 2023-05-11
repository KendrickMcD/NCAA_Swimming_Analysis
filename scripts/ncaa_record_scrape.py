# IMPORT LIBRARIES
import pdfplumber
import requests
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.request
import re
import os
import sys
import shutil
import glob
import time

# GET LINKS TO PDF RESULTS FROM 2002 - 2023


def extract_pdf_links(soup, heading):
    h3_tag = soup.find('h3', string=heading)
    pdf_div = h3_tag.find_next_sibling('div', class_='championship-box-years')
    pdf_links = [link.get('href') for link in pdf_div.find_all(
        'a') if link.get('href').endswith('.pdf')]
    return pdf_links


def is_year_in_link(link, years):
    try:
        year = int(link[-8:-4])
        return year in years
    except ValueError:
        return False

# COLLLECT PDF RESULTS FROM 2002 - 2023


def download_pdfs(years, links, late=False):
    half_index = len(links) // 2
    m_links = links[:half_index]
    w_links = links[half_index:]

    for year in years:
        for gender_links, gender in zip([m_links, w_links], ['M', 'W']):
            for link in gender_links:
                if str(year) in link:
                    response = requests.get(link)
                    filename = f'{gender}_{year}.pdf'
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    if late:
                        break
            if late:
                if gender == 'M' and year == 2021:
                    link = links[2]
                elif gender == 'M' and year == 2018:
                    link = links[4]
                elif gender == 'W' and year == 2018:
                    link = links[-13]
                elif gender == 'W' and year == 2016:
                    link = links[23]
                elif gender == 'W' and year == 2015:
                    link = links[24]
                else:
                    continue

                response = requests.get(link)
                filename = f'{gender}_{year}.pdf'
                with open(filename, 'wb') as f:
                    f.write(response.content)

# CREATE A DICTIONARY OF RESULTS FROM 2002 - 2023
# IMPORTANT: Only running the code below will miss some 2009 women's records
# To fix, save a better formatted PDF of results from: https://tinyurl.com/wncaa2009
# Be sure to save the PDF as W_2009.pdf in the same directory as this file, replacing the old one
# Then run the code below


def results_dictionary():
    def process_pdf(year_range, gender_list, event_prefixes, record_prefixes, records):
        for year in year_range:
            if year != 2020:
                for gender in gender_list:
                    filename = f"{gender}_{year}.pdf"
                    with pdfplumber.open(filename) as pdf:
                        seen_events = set()
                        seen_records = set()
                        for page in pdf.pages:
                            text = page.extract_text()
                            lines = text.split('\n')
                            event_lines = [line for line in lines if any(
                                line.startswith(prefix) for prefix in event_prefixes)]
                            record_lines = [line for line in lines if any(
                                line.startswith(prefix) for prefix in record_prefixes)]

                            for j, event in enumerate(event_lines):
                                if event not in seen_events:
                                    seen_events.add(event)
                                    if j < len(record_lines):
                                        record = record_lines[j]
                                        if record not in seen_records:
                                            seen_records.add(record)
                                            if year not in records:
                                                records[year] = {}
                                            if event not in records[year]:
                                                records[year][event] = {}
                                            records[year][event] = record

    later_records = {}
    early_records = {}

    process_pdf(range(2006, 2024), ['M', 'W'], ["Event", "Men"], [
                "NCAA:", "Championship"], later_records)
    process_pdf(range(2002, 2006), ['M', 'W'], ["EVENT"], [
                "NCAA:", "Championship", "NCAA Record"], early_records)

    return early_records, later_records

# REMOVE PDFs FROM DIRECTORY


def remove_results_pdf(start, end):
    import os
    years = list(range(start, end))
    for year in years:
        # Check if file exists
        if os.path.exists(f'W_{year}.pdf'):
            os.remove(f'W_{year}.pdf')
        if os.path.exists(f'M_{year}.pdf'):
            os.remove(f'M_{year}.pdf')

# CLEAN RECORDS


# CLEAN RECORDS FROM 2002 - 2006


def clean_early_records(dictionary):
    df = pd.DataFrame.from_dict(
        dictionary, orient='index').stack().reset_index()
    df.columns = ['year', 'event', 'record']
    df['year'] = df['year'].astype(int)

    # Remove 2004 records since they are in SCM
    df = df.drop(df[df['year'] == 2004].index)

    df = df.drop(df[df['event'].str.contains(
        'DIVING' or 'Diving' or 'Platform')].index)
    df = df.drop(df[df['event'].str.contains('Meter')].index)
    df.reset_index(drop=True, inplace=True)

    df['record'] = df['record'].str.replace('NCAA Record:', '')

    # Fix spacing in the record column
    df['record'] = df['record'].str.lstrip()
    df['record'] = df['record'].str.replace('  ', ' ')

    df['gender'] = np.nan

    # # Split the event column into distance and stroke columns
    for i in range(len(df)):
        if " MEN's" in df.loc[i, 'event']:
            df.loc[i, 'gender'] = 'M'
            df.loc[i, 'event'] = df.loc[i, 'event'].split("MEN's", 1)[
                1].strip()
        elif "WOMEN's" in df.loc[i, 'event']:
            df.loc[i, 'gender'] = 'F'
            df.loc[i, 'event'] = df.loc[i, 'event'].split("WOMEN's", 1)[
                1].strip()
    df['distance'] = df['event'].apply(lambda x: x.split('Yard', 1)[0].strip())
    df['stroke'] = df['event'].apply(lambda x: x.split('Yard', 1)[1].strip())

    # Make the distance column numeric
    df['distance'] = df['distance'].astype(int)

    # Convert stroke to title case
    df['stroke'] = df['stroke'].str.title()

    # Create stroke codes dictionary
    stroke_codes = {
        'Freestyle': 'FR',
        'Backstroke': 'BK',
        'Breaststroke': 'BR',
        'Butterfly': 'FL',
        'IM': 'IM',
        'Individual Medley': 'IM',
        'Medley Relay': 'Medley Relay',
        'Freestyle Relay': 'Freestyle Relay',
    }

    # Replace stroke names with stroke codes
    df['stroke'] = df['stroke'].map(stroke_codes)

    # Create a SCY column
    df['course'] = 'SCY'

    # Create columns for the time, date, and team
    df['time_(string)'] = np.nan
    df['season'] = np.nan
    df['team'] = np.nan
    df['name'] = np.nan

    # Loop over each row of the DataFrame
    for i in range(len(df)):
        # Check if 'stroke' column contains "Relay"
        if 'Relay' in df['stroke'][i]:
            df.loc[i, ['time_(string)', 'team', 'season']
                   ] = df['record'][i].split(' ', 2)
        else:
            time, first, last, team, date, = df['record'][i].split(' ', 4)
            df.loc[i, ['time_(string)', 'season', 'team']] = time, date, team
            df.loc[i, 'name'] = first + ' ' + last
            df.loc[i, 'name'] = df['name'][i].replace(',', '')

    # if time_(string) starts with :, drop the first character
    df['time_(string)'] = df['time_(string)'].apply(
        lambda x: x[1:] if x.startswith(':') else x)

    df['name'] = df['name'].str.title()
    df['team'] = df['team'].str.title()

    df['name'] = df['name'].fillna(df['team'])

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

    # Remove rows with the same name, event, time_(seconds), and season
    df = df.drop_duplicates(
        subset=['name', 'event', 'time_(seconds)', 'season'])
    df.reset_index(drop=True, inplace=True)

    # MANUAL CLEANING

    # Fix team names and seasons
    frolander = df[(df['name'] == 'Lars Frolander')].index
    moravcova = df[(df['name'] == 'Martina Moravcova')].index
    df.loc[frolander, 'team'] = 'Southern Methodist'
    df.loc[moravcova, 'team'] = 'Southern Methodist'
    df.loc[moravcova, 'season'] = 1997
    df.loc[frolander, 'season'] = 1998

    ervin = df[(df['name'] == 'Ervin /')].index[0]
    new = len(df)+1
    df.loc[new] = np.nan
    df.loc[new] = df.loc[ervin]
    df.loc[ervin, 'name'] = 'Matt Biondi'
    df.loc[ervin, 'team'] = 'California'
    df.loc[ervin, 'season'] = 1987
    df.loc[new, 'name'] = 'Anthony Ervin'
    df.loc[new, 'team'] = 'California'
    df.loc[new, 'season'] = 2001

    usc = df[(df['name'] == 'Southern')].index
    df.loc[usc, 'team'] = 'Southern California'
    df.loc[usc, 'season'] = 2002

    amy_van_dyken = df[(df['name'] == 'Amy Van')].index
    df.loc[amy_van_dyken, 'team'] = 'Colorado State'
    df.loc[amy_van_dyken, 'season'] = 1994
    df.loc[amy_van_dyken, 'name'] = 'Amy Van Dyken'

    df['team'] = df['team'].apply(
        lambda x: 'Florida' if 'Florida' in x or 'FLOR' in x or 'Floid' in x else x)

    stanford = df[(df['name'] == 'Stanford')].index
    df.loc[stanford, 'season'] = 2002

    df['name'] = df['name'].apply(
        lambda x: 'Tom Dolan' if 'Tom Dolan' in x else x)

    # Create a date column from the season column assigning 01/01/ to the beginning of the season
    df['date'] = pd.to_datetime('01/01/' + df['season'].astype(str))

    df['name'] = df['name'].str.title()
    df['team'] = df['team'].str.title()

    # Make distance and date columns numeric
    df['distance'] = df['distance'].astype(int)
    df['season'] = df['season'].astype(float)

    # drop the year, event, and record columns
    df = df.drop(['year', 'event', 'record'], axis=1)

    # Drop observations that have the same name, team, and time
    df.drop_duplicates(
        subset=['name', 'team', 'time_(seconds)', 'season'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    columns = ['name', 'distance', 'stroke', 'course',
               'time_(string)', 'time_(seconds)', 'season', 'date', 'team', 'gender']
    df = df[columns]
    return df

# CLEAN RECORDS FROM 2006 - 2023


def clean_later_records(dictionary):
    # Create a DataFrame from the records dictionary
    df = pd.DataFrame.from_dict(
        dictionary, orient='index').stack().reset_index()
    df.columns = ['year', 'event', 'record']
    df['year'] = df['year'].astype(int)

    df.sort_values(by=['year', 'event'], inplace=True, ascending=False)

    df = df.drop(df[df['event'].str.contains('Diving')].index)
    df = df.drop(df[df['event'].str.contains('Swim-off')].index)
    df.reset_index(drop=True, inplace=True)

    # Get ride of the "NCAA:" and "N" in the record column
    df['record'] = df['record'].str.replace('NCAA:', '')
    df['record'] = df['record'].str.replace('Championship:', '')
    df['record'] = df['record'].str.replace(' N ', ' ')
    df['record'] = df['record'].str.replace(' I ', ' ')
    df['record'] = df['record'].str.replace(' C ', ' ')

    # Fix spacing in the record column
    df['record'] = df['record'].str.replace('!', '')
    df['record'] = df['record'].str.lstrip()
    df['record'] = df['record'].str.replace('  ', ' ')
    df['record'] = df['record'].str.replace(',', '')

    # Fix spacing issues in the record column for 2 records
    df['record'] = df['record'].apply(
        lambda x: x.replace('7K', '7 K') if '7K' in x else x)

    # Split the event column into distance and stroke columns
    for i in range(len(df)):
        if "Men" in df.loc[i, 'event']:
            df.loc[i, 'gender'] = 'M'
            df.loc[i, 'event'] = df.loc[i, 'event'].split("Men", 1)[1].strip()
        elif "Women" in df.loc[i, 'event']:
            df.loc[i, 'gender'] = 'F'
            df.loc[i, 'event'] = df.loc[i, 'event'].split("Women", 1)[
                1].strip()
    df['distance'] = df['event'].apply(lambda x: x.split('Yard', 1)[0].strip())
    df['stroke'] = df['event'].apply(lambda x: x.split('Yard', 1)[1].strip())

    # Make the distance column numeric
    df['distance'] = df['distance'].astype(int)

    # Make the distance column numeric
    df['distance'] = df['distance'].astype(int)

    # Create stroke codes dictionary
    stroke_codes = {
        'Freestyle': 'FR',
        'Backstroke': 'BK',
        'Breaststroke': 'BR',
        'Butterfly': 'FL',
        'Butter(cid:976)ly': 'FL',
        'IM': 'IM',
        'Individual Medley': 'IM',
        'Medley Relay': 'Medley Relay',
        'Freestyle Relay': 'Freestyle Relay',
    }

    # Replace stroke names with stroke codes
    df['stroke'] = df['stroke'].map(stroke_codes)

    # Create a SCY column
    df['course'] = 'SCY'

    # Drop rows Auburn relay assigned to non-relay event
    df.drop([247, 283], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Split up record column into time, date, and team columns
    for i in range(len(df)):
        # Check if 'stroke' column contains "Relay"
        if 'Relay' in df['stroke'][i]:
            df.loc[i, ['time_(string)', 'date', 'team']
                   ] = df['record'][i].split(' ', 2)
        else:
            time, date, first, last, team = df['record'][i].split(' ', 4)
            df.loc[i, ['time_(string)', 'date', 'team']] = time, date, team
            df.loc[i, 'name'] = first + ' ' + last
            df.loc[i, 'name'] = df['name'][i].replace(',', '')

    # MANUAL CLEANING

    # Change row with name that is 'Sean R' and change to 'Sean Mahoney'
    index = df[df['name'] == 'Sean R'].index
    df.loc[index, 'name'] = 'Sean Mahoney'
    df.loc[index, 'team'] = 'California'

    # Change 'Virginia - Also 3/18/22' to 'Virginia'
    index = df[df['team'] == 'Virginia - Also 3/18/22'].index
    df.loc[index, 'team'] = 'Virginia'

    # Remove any string values that come after a - in the team column
    df['team'] = df['team'].apply(lambda x: x.split('-', 1)[0].strip())

    # Remove all commas from the team column
    df['team'] = df['team'].str.replace(',', '')

    # Split the team name and if the first and second words are the same, remove the second word
    for i in range(len(df)):
        if len(df['team'][i].split()) > 1:
            if df['team'][i].split()[0] == df['team'][i].split()[1]:
                df.loc[i, 'team'] = df['team'][i].split()[0]

    # Rename 'S California' to 'Southern California'
    df['team'] = df['team'].str.replace('S California', 'Southern California')

    team_dict = {
        'Cal|CAL|Berkeley': 'California',
        'Arizona St|ASU': 'Arizona State',
        'ARIZ|ArizonaL': 'Arizona',
        'Southern Cal|Southern Cali|USC': 'Southern California',
        'AUB|Aub': 'Auburn',
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

    # Correct Texas A&M team name
    index = df[df['name'] == 'Breeja Larson'].index
    df.loc[index, 'team'] = 'Texas A&M'

    # Fill team name as name for relays
    df['name'] = df['name'].fillna(df['team'])

    df['name'] = df['name'].apply(
        lambda x: 'Kara Lynn Joyce' if 'Kara' in x else x)

    df['name'] = df['name'].apply(
        lambda x: 'Vladimir Morozov' if 'Vlad M' in x else x)

    df['name'] = df['name'].apply(
        lambda x: 'Cesar Cielo' if x == 'Cear Cielo' else x)

    df['name'] = df['name'].apply(
        lambda x: 'Arianna Vanderpool-Wallace' if x == 'Ariana Vanderpool-Wallace' else x)

    # Convert time to seconds
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

    # Convert date to datetime object

    months = {
        'Jan': '01', 'Feb': '02', 'Mar': '03',
        'Apr': '04', 'May': '05', 'Jun': '06',
        'Jul': '07', 'Aug': '08', 'Sep': '09',
        'Oct': '10', 'Nov': '11', 'Dec': '12'
    }

    for i in range(len(df)):
        if len(df.loc[i, 'date']) == 4:
            df.loc[i, 'date'] = '01/01/' + df.loc[i, 'date']
            df.loc[i, 'date'] = pd.to_datetime(df.loc[i, 'date'])
        elif '-' in df.loc[i, 'date']:
            day, month, year = df.loc[i, 'date'].split('-')
            month = months[month]
            df.loc[i, 'date'] = month + '/' + day + '/' + year
            df.loc[i, 'date'] = pd.to_datetime(df.loc[i, 'date'])
        else:
            df.loc[i, 'date'] = pd.to_datetime(df.loc[i, 'date'])

    df['date'] = pd.to_datetime(df['date'])

    # Create a column for the season
    for i in range(len(df)):
        if df.loc[i, 'date'].month < 9:
            df.loc[i, 'season'] = df.loc[i, 'date'].year
        else:
            df.loc[i, 'season'] = df.loc[i, 'date'].year + 1

    # Drop observations that have the string 'Krug' or 'Loukas' in the record column
    # These are inaccurate observations
    df = df[~df['record'].str.contains('Krug')]
    df = df[~df['record'].str.contains('Loukas')]
    df.reset_index(drop=True, inplace=True)

    # Drop observations that have the same name, team, and time
    df.drop_duplicates(
        subset=['name', 'team', 'time_(seconds)', 'season'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    df.drop(['year', 'event', 'record'], axis=1, inplace=True)

    columns = ['name', 'distance',
               'stroke', 'course',
               'time_(string)', 'time_(seconds)',
               'season', 'date',
               'team', 'gender']

    df = df[columns]
    return df

# SCRAPE AND CLEAN NCAA RECORDS FROM 2002-2023 ON SWIMSWAM.COM


def scrape_ncaa_reocrds():

    url = 'https://swimswam.com/swimswam-meet-results-archive/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    mens_heading = "NCAA DI Championships (Men's)"
    womens_heading = "NCAA DI Championships (Women)"

    mens_pdf_links = extract_pdf_links(soup, mens_heading)
    womens_pdf_links = extract_pdf_links(soup, womens_heading)

    pdf_links = mens_pdf_links + womens_pdf_links

    indices = []
    for link in pdf_links:
        if '2002' in link:
            indices.append(pdf_links.index(link))
        if '2005' in link:
            indices.append(pdf_links.index(link))
        if '2023' in link:
            indices.append(pdf_links.index(link))

    early_links = pdf_links[indices[1]:indices[2]+1] + \
        pdf_links[indices[4]:indices[5]+1]
    late_links = pdf_links[:indices[1]] + pdf_links[indices[3]:indices[4]]

    # COLLECT PDF RESULTS FROM 2002 - 2006
    early_years = list(range(2002, 2006))
    early_years.reverse()
    download_pdfs(early_years, early_links)

    # COLLECT PDF RESULTS FROM 2006 - 2023
    later_years = list(range(2006, 2024))
    later_years.remove(2020)
    later_years.reverse()
    download_pdfs(later_years, pdf_links, late=True)

    # Remove 2009 file since we will use a different one from the repository
    os.remove('W_2009.pdf')

    # Move the W_2009.pdf file from the data/pdf_results directory to the current directory
    try:
        src = os.path.join(os.getcwd(), '../data', 'pdf_results', 'W_2009.pdf')
        dst = os.path.join(os.getcwd(), 'W_2009.pdf')
        shutil.move(src, dst)
    except:
        print('Correct W_2009.pdf file not found.')
        sys.exit()

    # Wait 3 seconds to make sure files are in the correct place
    time.sleep(3)

    # Verify that the W_2009.pdf file is in the current directory
    if os.path.exists('W_2009.pdf'):

        early_records, later_records = results_dictionary()
        early_recordsdf = clean_early_records(early_records)
        later_recordsdf = clean_later_records(later_records)

        recordsdf = pd.concat(
            [early_recordsdf, later_recordsdf], ignore_index=True)

        # Remove duplicates with the same name, distance, stroke, time_(seconds), and season
        recordsdf.drop_duplicates(
            subset=['name', 'distance', 'stroke', 'time_(seconds)', 'season'], inplace=True)
        recordsdf.reset_index(drop=True, inplace=True)

        # Define source and destination directories
        src_dir = os.getcwd()  # Current working directory
        dst_dir = os.path.join(src_dir, '../data', 'pdf_results')

        # Check if the destination directory exists, if not, create it
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)

        # Move all pdf files to the data folder
        for file in glob.glob(os.path.join(src_dir, "*.pdf")):
            file_name = os.path.basename(file)
            dst_file = os.path.join(dst_dir, file_name)

            if os.path.exists(dst_file):
                os.remove(file)  # Delete the file from the current directory
            else:
                # Move the file to the destination directory
                shutil.move(file, dst_dir)

    else:
        print('W_2009.pdf file not found in the current directory')

    return recordsdf
