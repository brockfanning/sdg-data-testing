# -*- coding: utf-8 -*-
"""
This script imports existing data for Armenia from an Excel file.
"""

import glob
import os.path
import pandas as pd
import numpy as np

# For more readable code below.
HEADER_YEAR = 'Year'
HEADER_VALUE = 'Value'
FOLDER_DATA_CSV = 'data'

YEARS = ['2015', '2016', '2017']

HARDCODED_DISAGGREGATION_COLUMNS = {
    'participants': 'Employment status',
    'economically inactive  population': 'Employment status',
    'pensioners': 'Employment status',
    'students': 'Employment status',
    'other inactive population': 'Employment status',
}

GENERAL_REPLACEMENTS = {
    '10.7.2. a': '10.7.2.a',
    '10.7.2. b': '10.7.2.b',
    '5.a.1 (a).a': '5.a.1.a.a',
    '5.a.1 (b).a.1': '5.a.1.b.a.1',
    '5.a.1 (b).a.2': '5.a.1.b.a.2',
}

def get_disaggregation_column(category):
    category = category.lower()
    ret = False
    if category == 'male' or category == 'female':
        ret = 'Sex'
    if category == 'rural' or category == 'urban':
        ret = 'Location'
    if '-' in category or ' to ' in category:
        ret = 'Age'
    if 'employ' in category:
        ret = 'Employment status'
    if not ret:
        # Consult a hardcoded list.
        if category in HARDCODED_DISAGGREGATION_COLUMNS:
            ret = HARDCODED_DISAGGREGATION_COLUMNS[category]

    return ret

def blank_dataframe():
    """This starts a blank dataframe with our required tidy columns."""

    # Start with two columns, year and value.
    blank = pd.DataFrame({HEADER_YEAR:[], HEADER_VALUE:[]})
    # Make sure the year column is typed for integers.
    blank[HEADER_YEAR] = blank[HEADER_YEAR].astype(int)

    return blank

def foo_csv(csv):

    try:
        tidy = tidy_dataframe(df, metadata['indicator_variable'])
    except Exception as e:
        print(csv, e)
        return False

    try:
        tidy_path = os.path.join(FOLDER_DATA_CSV, csv_filename)
        tidy.to_csv(tidy_path, index=False, encoding='utf-8')
        print('Converted ' + csv_filename + ' to tidy format.')
    except Exception as e:
        print(csv, e)
        return False

    return True

def indicator_id(text):
    ret = False
    if isinstance(text, str):
        words = text.split(' ')
        id = words[0]
        if '.' in id:
            if id.endswith('.'):
                id = id[:-1]
            ret = id
    return ret

def main():
    """Tidy up all of the indicator CSVs in the data folder."""

    status = True

    # Create the place to put the files.
    os.makedirs(FOLDER_DATA_CSV, exist_ok=True)

    # Read the Excel spreadsheet into a dataframe.
    excel_opts = {
      'header': None,
      'names': ['Global', 'National', 'Unit', '2015', '2016', '2017'],
      'skiprows': [0, 1],
      'usecols': [2,3,4,5,6,7]
    }
    df = pd.read_excel('SDG_eng.xlsx', **excel_opts)

    # Some indicators are already properly disaggregated in the source data.
    already_disaggregated = [
        '2.2.2',
        '8.5.2',
        '8.6.1'
    ]

    # Do some general replacements.
    for search in GENERAL_REPLACEMENTS:
        df = df.replace(search, GENERAL_REPLACEMENTS[search], regex=True)

    # Merge 'Global' and 'National' to a 'Category' column.
    df['Category'] = np.where(df.National.isnull(), df.Global, df.National)
    df = df.drop(labels=['Global', 'National'], axis='columns')

    # Remove rows without value in Category.
    df = df.dropna(subset=['Category'], how='all')

    # NOTE: The total number of rows should not change after this point. We
    # reset the index now for logical sequential indexes.
    df = df.reset_index(drop=True)

    # Figure out where each indicator starts and set the ID.
    indicators = {}
    for row in df.iterrows():
        category = row[1]['Category']
        id = indicator_id(category)
        if id == '17.8.1':
            print(category)
            print(id)
            print(row[0])
        if id:
            indicators[id] = {
                'start': row[0]
            }
            # Replace the cell data with just the id number.
            df.set_value(row[0], 'Category', id)
    # Also set the end rows.
    last_id = False
    for id in indicators:
        if last_id:
            indicators[last_id]['end'] = (indicators[id]['start'] - 1)
        last_id = id
    # Set the last end row.
    for id in indicators:
        if 'end' not in indicators[id]:
            indicators[id]['end'] = df.last_valid_index()
        # For ease later, add the number of rows.
        indicators[id]['num_rows'] = indicators[id]['end'] - indicators[id]['start'] + 1

    #print(indicators)
    # Remove "age" and "aged".
    df = df.replace('aged', '', regex=True)
    df = df.replace('age', '', regex=True)

    # Remove whitespace from Category values.
    df['Category'] = df['Category'].str.strip()

    # More normalization replacements.
    replacements = {
        'boy': 'Male',
        'girl': 'Female',
        'urban': 'Urban',
        'rural': 'Rural'
    }
    for row in df.iterrows():
        category = row[1]['Category']
        category = category.lower()

        # Skip rows with commas, as those seem to be fine already.
        if ',' in category:
            continue

        for replacement in replacements:
            if replacement in category:
                df.set_value(row[0], 'Category', replacements[replacement])

    # Figure out which rows are disaggregations. Only look for Male/Female.
    for id in indicators:
        start = indicators[id]['start']
        end = indicators[id]['end']
        num_rows = indicators[id]['num_rows']
        # Skip indicators with only one row, as they have no disaggregation.
        if num_rows == 1:
            continue

        # Take a slice of the main dataframe for this indicator.
        indicator_df = df[start:end + 1]

        # For indicators that already have sufficient disaggregation, we just
        # convert the commas to pipes.
        if id in already_disaggregated:
            for row in indicator_df.iterrows():
                index = row[0]
                category = row[1]['Category']
                category = category.replace(',', '|')
                df.set_value(index, 'Category', category)

        # Since we're only looking for Male/Female disaggregation, we can also
        # skip any rows that have 1 or less instances of 'Male' or 'Female'.
        num_male = indicator_df['Category'].str.count('Male').sum()
        num_female = indicator_df['Category'].str.count('Female').sum()
        if num_male < 2 and num_female < 2:
            continue

        first_male_found = False
        first_female_found = False
        last_non_gender_category = False
        for row in indicator_df.iterrows():
            index = row[0]
            category = row[1]['Category']
            if category == 'Male':
                if not first_male_found:
                    first_male_found = True
                    continue
            if category == 'Female':
                if not first_female_found:
                    first_female_found = True
                    continue
            if category != 'Male' and category != 'Female':
                last_non_gender_category = category
            else:
                # We need to update the main dataframe by combining this
                # Male/Female with whatever the last non-gender category was,
                # separated by a pipe.
                disaggregated_category = '|'.join([category, last_non_gender_category])
                df.set_value(index, 'Category', disaggregated_category)

    # Finally loop through the indicators and create CSV files.
    for id in indicators:
        start = indicators[id]['start']
        end = indicators[id]['end']
        num_rows = indicators[id]['num_rows']

        # Take a slice of the main dataframe for this indicator.
        indicator_df = df[start:end + 1]
        #print(indicator_df)
        for row in indicator_df.iterrows():
            category = row[1]['Category']
            if id == category:
                # This is the aggregate total. If this has no values, then we
                # have to skip the whole indicator. Make a note of this.
                foo = 'bar'
                continue
            disaggregation_column = get_disaggregation_column(category)
            #if not disaggregation_column:
            #    print(id + ' -- ' + category)

        csv_df = blank_dataframe()



    return status

if __name__ == '__main__':
    if not main():
        raise RuntimeError("Failed tidy conversion")
    else:
        print("Success")