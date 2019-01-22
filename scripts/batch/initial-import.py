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

"""
Normatization notes:
1. Remove all rows without data in any year.
3. Merge "Global" and "National" into one "Category" column and remove them.
4. Look for any row with an indicator id in it, and remove everything except
   for the indicator ID. Note this may need specific exceptions, so check it.
   During this process, save the starting rows for each indicator in a separate
   dict.
5. Remove "age" and "aged" from all values of "Category"
7. Trip whitepace from all values of Category
8. Remove all rows without any value in Category
10. Normalize with case-insensitive wild-card replacements:
    (skipping any that already have a comma)
    *boy* -> Male
    *girl* -> Female
    *urban* -> Urban
    *rural* -> Rural
11. Loop through the indicators and loop through the rows.
    (skipping any that already have a comma)
    a. Any "Male" or "Female" after the first occurence, assume it is a double
       category. Combine it with the last non-gender-related category, separated
       by a comma.
12. Loop through the indicators, finally created tidy CSV data.
    a. First row is always the total
    b. Other rows infer the disaggregation type from the Category, using hints:
        Male/Female = Sex
        *Year*/*Month* = Age
        Anything iwth two integers and a hyphen = Age

At this point print output for tweaks.
"""

YEARS = ['2015', '2016', '2017']

def get_disaggregation_column(category):
    ret = 'Unknown'
    if category == 'Male' or category == 'Female':
        ret = 'Sex'
    if category == 'Rural' or category == 'Urban':
        ret = 'Location'
    if '-' in category or ' to ' in category:
        ret = 'Age'
    print category + ' ' + ret

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

    # Merge 'Global' and 'National' to a 'Category' column.
    df['Category'] = np.where(df.National.isnull(), df.Global, df.National)
    df = df.drop(labels=['Global', 'National'], axis='columns')

    # Remove rows without value in Category.
    df = df.dropna(subset=['Category'], how='all')

    # NOTE: The total number of rows should not change after this point. We
    # reset the index now for logical sequential indexes.
    df = df.reset_index()
    df = df.drop(labels=['index'], axis='columns')

    # Figure out where each indicator starts and set the ID.
    indicators = {}
    for row in df.iterrows():
        category = row[1]['Category']
        id = indicator_id(category)
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
        print(indicator_df)
        break

        csv_df = tidy_blank_dataframe()



    return status

if __name__ == '__main__':
    if not main():
        raise RuntimeError("Failed tidy conversion")
    else:
        print("Success")