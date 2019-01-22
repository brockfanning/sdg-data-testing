# -*- coding: utf-8 -*-
"""
This script imports existing data for Armenia from an Excel file.
"""

import glob
import os.path
import pandas as pd
import numpy as np

# For more readable code below.
HEADER_YEAR_TIDY = 'Year'
HEADER_VALUE_TIDY = 'Value'
FOLDER_DATA_CSV_TIDY = 'data'

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

def tidy_blank_dataframe():
    """This starts a blank dataframe with our required tidy columns."""

    # Start with two columns, year and value.
    blank = pd.DataFrame({HEADER_YEAR_WIDE:[], HEADER_VALUE_TIDY:[]})
    # Make sure the year column is typed for integers.
    blank[HEADER_YEAR_WIDE] = blank[HEADER_YEAR_WIDE].astype(int)

    return blank

def tidy_csv(csv):

    try:
        tidy = tidy_dataframe(df, metadata['indicator_variable'])
    except Exception as e:
        print(csv, e)
        return False

    try:
        tidy_path = os.path.join(FOLDER_DATA_CSV_TIDY, csv_filename)
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
    os.makedirs(FOLDER_DATA_CSV_TIDY, exist_ok=True)

    # Read the Excel spreadsheet into a dataframe.
    excel_opts = {
      'header': None,
      'names': ['Global', 'National', 'Unit', '2015', '2016', '2017'],
      'skiprows': [0, 1],
      'usecols': [2,3,4,5,6,7]
    }
    df = pd.read_excel('SDG_eng.xlsx', **excel_opts)

    # Ignore rows with no yearly data.
    years = ['2015', '2016', '2017']
    df = df.dropna(subset=years, how='all')

    # Merge 'Global' and 'National' to a 'Category' column.
    df['Category'] = np.where(df.National.isnull(), df.Global, df.National)
    df = df.drop(labels=['Global', 'National'], axis='columns')

    # Figure out where each indicator starts and set the ID.
    starting_rows = {}
    for row in df.iterrows():
        category = row[1]['Category']
        id = indicator_id(category)
        if id:
            starting_rows[id] = row[0]
            df.set_value(row[0], 'Category', id)

    # Remove "age" and "aged".
    df = df.replace('aged', '', regex=True)
    df = df.replace('age', '', regex=True)

    # Remove whitespace from Category values.
    df['Category'] = df['Category'].str.strip()

    print(df['Category'])

    return status

if __name__ == '__main__':
    if not main():
        raise RuntimeError("Failed tidy conversion")
    else:
        print("Success")