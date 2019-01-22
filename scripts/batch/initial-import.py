# -*- coding: utf-8 -*-
"""
This script imports existing data for Armenia from an Excel file.
"""

import glob
import os.path
import pandas as pd
import yaml

# For more readable code below.
HEADER_ALL = 'all'
HEADER_YEAR_WIDE = 'year'
HEADER_YEAR_TIDY = 'Year'
HEADER_VALUE_TIDY = 'Value'
FOLDER_DATA_CSV_TIDY = 'data'
FOLDER_DATA_CSV_WIDE = 'data-wide'
FOLDER_META = 'meta'
FOLDER_DATA_CSV_SUBNATIONAL = 'data-wide/subnational'

# Specific info on how to parse the indicators in this file.
INDICATORS = {
  '1.1.1': {
    'start': 3,
    'end': 21,
    'disaggregations': {
      'Sex': [4, 5],
      'Location': [6, 7],
      'Age': [8, 9],
      'Employment status': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
    }
  }
}

"""
Normatization notes:
1. Remove all rows without data in any year.
3. Merge "Global" and "National" into one "Category" column and remove them.
4. Look for any row with an indicator id in it, and remove everything except
   for the indicator ID. Note this may need specific exceptions, so check it.
   During this process, save the starting rows for each indicator in a separate
   dict.
5. Remove "age" and "aged" from all values of "Category"
6. Remove any rows with a Category of "Children" (count these, may just be 1)
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

# Allows for more human-friendly folder names in the repository.
FOLDER_NAME_CONVERSIONS = {
    'state': 'GeoCode',
}

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

def main():
    """Tidy up all of the indicator CSVs in the data folder."""

    status = True

    # Create the place to put the files.
    os.makedirs(FOLDER_DATA_CSV_TIDY, exist_ok=True)

    # Read the Excel spreadsheet into a dataframe.
    excel_opts = {
      'header': None,
      'names': ['Global', 'National'],
      'skiprows': range(start),
      'nrows': end - start,
      'usecols': [2,3]
    }
    df = pd.read_excel('SDG_eng.xlsx', **excel_opts)

    #df['indicator_description'] = df.bfill(axis=1).iloc[:, 0]

    return status

if __name__ == '__main__':
    if not main():
        raise RuntimeError("Failed tidy conversion")
    else:
        print("Success")