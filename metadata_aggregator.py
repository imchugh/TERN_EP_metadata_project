#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 11:05:45 2025

@author: imchugh
"""
###############################################################################
### BEGIN IMPORTS ###
###############################################################################

import json
import pandas as pd

import gsheets_api_client as gsac

###############################################################################
### END IMPORTS ###
###############################################################################


###############################################################################
### BEGIN INITS ###
###############################################################################

CONFIGS_FILE = 'configs.json'
TARGET_FOLDER_ID = '1sSdrC4ukE52MzHQWQ9fD5SSA3_25_tbH'

with open(CONFIGS_FILE) as f:
    CONFIGS = json.load(f)

###############################################################################
### END INITS ###
###############################################################################


###############################################################################
### BEGIN FUNCTIONS ###
###############################################################################

def aggregate_sheets():
    """
    Get the content of the site-specific google sheets in the directory and
    aggregate.

    Returns:
        dataframe containing the aggregated content.

    """

    # Get the list of spreadsheets
    files = gsac.get_sheet_ids(folder_id=TARGET_FOLDER_ID)

    # Get the file content for each
    df_list = []
    for file in files:
        sheet_info = gsac.get_sheet_content(
            sheet_id=file['id'],
            tab_range='Metadata'
        )
        df_list.append(
            pd.DataFrame(
                data=sheet_info['values'][2:],
                columns=['Field', sheet_info['values'][1][1]]
            )
            .set_index('Field')
            .squeeze()
        )

    # Concatenate all results, order, format and rename to DSA names
    df = pd.concat(df_list, axis=1).fillna('')
    df = df[sorted(df.columns)]
    df = df.rename(
        {value: key for key, value in CONFIGS['FIELD_ALIASES'].items()}
    )
    return df

###############################################################################
### END FUNCTIONS ###
###############################################################################
