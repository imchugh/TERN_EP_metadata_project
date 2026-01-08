#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created November 2025

@author: imchugh

Generalised module for validating google sheets / drive api authentication /
access and manipulating sheets.
"""

###############################################################################
### BEGIN IMPORTS ###
###############################################################################

import pandas as pd
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

###############################################################################
### END IMPORTS ###
###############################################################################


###############################################################################
### BEGIN INITS ###
###############################################################################

AUTH_DIR = '/home/unimelb.edu.au/imchugh/Documents/secrets'
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

TOKEN_PATH = '/'.join([AUTH_DIR, TOKEN_FILE])
SECRET_PATH = '/'.join([AUTH_DIR, CLIENT_SECRET_FILE])

# Load or authenticate credentials
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
else:
    flow = InstalledAppFlow.from_client_secrets_file(SECRET_PATH, SCOPES)
    creds = flow.run_local_server(
        port=0, access_type='offline', prompt='consent'
    )
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

# Build Drive and Sheets services
drive_service = build("drive", "v3", credentials=creds)
sheets_service = build("sheets", "v4", credentials=creds)

###############################################################################
### END INITS ###
###############################################################################


###############################################################################
### Folder-level functions ###
###############################################################################

# -----------------------------------------------------------------------------
def list_folder_contents(folder_id: str) -> list:
    """
    List items in a drive folder.

    Args:
        folder_id: unique id of drive folder.

    Returns:
        results: list of dicts (one for each item).

    """

    query = f"'{folder_id}' in parents and trashed = false"
    results = []
    page_token = None

    while True:
        response = drive_service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token
        ).execute()

        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return results
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def get_sheet_ids(folder_id: str, path: str = '', output: list = None) -> list:
    """
    Walk a parent folder and get all sheets in parent and child folders
    recursively.

    Args:
        folder_id: unique id of parent folder.
        path (optional): path to folder. Defaults to ''.
        output (optional): result list to append to. Defaults to None.

    Returns:
        list of dicts (one for each sheet).

    """

    # Inits
    if output is None:
        output = []

    # Get the folder contents
    items = list_folder_contents(folder_id=folder_id)

    # Iterate over folders
    for item in items:

        item_path = f"{path}/{item['name']}"

        # Recurse into any subfolder
        if item["mimeType"] == "application/vnd.google-apps.folder":
            get_sheet_ids(folder_id=item["id"], path=item_path, output=output)

        # Get contents of Google Sheet
        elif item["mimeType"] == "application/vnd.google-apps.spreadsheet":
            output.append(
                {
                    "name": item["name"],
                    "id": item["id"],
                    "path": item_path
                }
            )

    return output
# -----------------------------------------------------------------------------

###############################################################################
### Sheet-level functions ###
###############################################################################

# -----------------------------------------------------------------------------
def create_sheet(file_name: str, folder_id: str) -> str:
    """
    Create a sheet using the drive service (required when writing to a
    particular location).


    Args:
        file_name: name for the spreadsheet.
        folder_id: id of the parent folder.

    Returns:
        the file id.

    """

    file_metadata = {
        "name": file_name,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [folder_id]
        }

    file = drive_service.files().create(
        body=file_metadata,
        fields="id"
    ).execute()

    return file["id"]
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def copy_sheet(sheet_id: str, dest_folder_id: str, new_sheet_name: str) -> None:
    """
    Create a copy of an existing spreadsheet.

    Args:
        sheet_id: unique id of existing sheet.
        dest_folder_id: unique id of parent folder to contain copied sheet.
        new_sheet_name: name of copied sheet.

    Returns:
        None.

    """

    body = {
        "name": new_sheet_name,
        "parents": [dest_folder_id]
    }
    return (
        drive_service.files().copy(
            fileId=sheet_id,
            body=body
        )
        .execute()
    )
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def write_info_to_sheet(
    sheet_id: str, tab_name: str, data: pd.DataFrame | pd.Series
    ) -> None:
    """
    Write information to sheet.

    Args:
        sheet_id: unique id of existing sheet.
        tab_name: name of tab to write to.
        data: data to be written.

    Returns:
        None.

    """

    # Convert DataFrame to list of lists
    values = [data.columns.tolist()] + data.values.tolist()

    # Write to sheet
    (
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!A1",
            valueInputOption="RAW",
            body={"values": values}
        )
        .execute()
    )
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def do_batch_update(sheet_id: str, body: dict) -> dict:
    """
    Update the spreadsheet using the formatting options in the dict passed to
    `body`.

    Args:
        sheet_id: unique id of existing sheet.
        body: dictionary containing formatting syntax.

    Returns:
        json-formatted api response.

    """

    return (
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body=body
        )
        .execute()
    )
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def get_sheet_metadata(sheet_id: str) -> dict:
    """
    Get metadata for sheet.

    Args:
        sheet_id: unique id of existing sheet.

    Returns:
        dictionary containing metadata.

    """

    return (
        sheets_service.spreadsheets().get(
            spreadsheetId=sheet_id)
        .execute()
    )
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def get_sheet_content(sheet_id: str, tab_range: str | list) -> list:
    """
    Get the sheet data content.

    Args:
        sheet_id: unique id of existing sheet.
        tab_range: tab(s) and ranges tio which to write data.

    Returns:
        list of dicts containing data.

    """

    if isinstance(tab_range, str):
        return (
            sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=tab_range,
                majorDimension="ROWS",
                valueRenderOption="UNFORMATTED_VALUE"
            )
            .execute()
        )

    if isinstance(tab_range, list):
        return (
            sheets_service.spreadsheets().values().batchGet(
                spreadsheetId=sheet_id,
                ranges=tab_range,
                majorDimension="ROWS",
                valueRenderOption="UNFORMATTED_VALUE"
            )
            .execute()
        )
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
def get_sheet_mod_metadata(sheet_id: str) -> dict:
    """
    Return the modification metadata.

    Args:
        sheet_id: unique id of existing sheet.

    Returns:
        dict of metadata.

    """

    return (
        drive_service.files().get(
            fileId=sheet_id,
            fields="id, name, modifiedTime, lastModifyingUser"
            )
        .execute()
        )
# -----------------------------------------------------------------------------


###############################################################################
### Tab-level formatters ###
###############################################################################

# -----------------------------------------------------------------------------
def _get_col_width_formatter(
        tab_id: int, start: int, end: int, n_px: int
) -> dict:
    """
    Return the populated column width formatter.

    Args:
        tab_id: unique tab identifier.
        start: index (0-based) of start column.
        end: index of end column.
        n_px: with in number of pixels.

    Returns:
        formatter populated with input fields.

    """

    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": tab_id,
                "dimension": 'COLUMNS',
                "startIndex": start, "endIndex": end
            },
            "properties": {"pixelSize": n_px},
            "fields": "pixelSize"
        }
    }
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def _create_tab_request(tab_name: str, row_count: int, col_count: int) -> dict:
    """
    Create dictionary required to generate new tab in api.

    Args:
        tab_name: name of tab to create.
        row_count: number of tab rows.
        col_count: number of tab cols.

    Returns:
        the request dictionary.

    """

    return {
        "addSheet": {
            "properties": {
                "title": tab_name,
                "gridProperties": {
                    "rowCount": row_count,
                    "columnCount": col_count
                }
            }
        }
    }
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def _get_cell_help_formatter(
        tab_id: int, start_row_idx: int, end_row_idx: int, start_col_idx: int,
        end_col_idx: int, msg: str
):
    """
    Return the populated help message formatter.

    Args:
        tab_id: unique tab identifier.
        start_row_idx: index of start row.
        end_row_idx: index of end row.
        start_col_idx: index of start column.
        end_col_idx: index of end column.
        msg: the help message that should appear.

    Returns:
        formatter populated with input fields.

    """

    return {
        "updateCells": {
            "range": {
                "sheetId": tab_id,
                "startRowIndex": start_row_idx,
                "endRowIndex": end_row_idx,
                "startColumnIndex": start_col_idx,
                "endColumnIndex": end_col_idx
            },
            "rows": [{"values": [{"note": msg}]}],
            "fields": "note"
        }
    }
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def _get_wrap_text_formatter(tab_id: int) -> dict:
    """
    Return the populated formatter to wrap text.

    Args:
        tab_id: unique tab identifier.

    Returns:
        formatter populated with input fields.

    """

    return {
        "repeatCell": {
            "range": {"sheetId": tab_id},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat.wrapStrategy"
        }
    }
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def _get_bold_formatter(
        tab_id: int, start_row_idx: int, end_row_idx: int
) -> dict:
    """
    Return the populated formatter to create bold text.

    Args:
        tab_id: unique tab identifier.
        start_row_idx: index of start row.
        end_row_idx: index of end row.

    Returns:
        formatter populated with input fields.

    """

    return {
        "repeatCell": {
            "range": {
                "sheetId": tab_id,
                "startRowIndex": start_row_idx,
                "endRowIndex": end_row_idx
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {"bold": True}
                }
            },
            "fields": "userEnteredFormat.textFormat.bold"
        }
    }
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def _get_tab_order_formatter(tab_id: int, tab_idx=0) -> dict:
    """
    Return the populated formatter to determine tab order.

    Args:
        tab_id: unique tab identifier.
        tab_idx (optional): move tab to a particular integer location.
        Defaults to 0.

    Returns:
        formatter populated with input fields.

    """

    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": tab_id,
                "index": tab_idx
            },
            "fields": "index"
        }
    }
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def _get_active_tab_formatter(tab_id: int) -> dict:
    """
    Return the populated formatter setting the active tab.

    Args:
        tab_id: unique tab identifier.

    Returns:
        formatter populated with input fields.

    """

    return {
        "setActiveSheetId": {
            "sheetId": tab_id
        }
    }
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def _get_range_lock_formatter(
        tab_id: int, start_row_idx: int, end_row_idx: int, start_col_idx: int,
        end_col_idx: int
) -> dict:
    """
    Return the formatter that locks cells or row / col ranges thereof.

    Args:
        tab_id: unique tab identifier.
        start_row_idx: index of start row.
        end_row_idx: index of end row.
        start_col_idx: index of start column.
        end_col_idx: index of end column.

    Returns:
        formatter populated with input fields.

    """

    return {
        "addProtectedRange": {
            "protectedRange": {
                "range": {
                    "sheetId": tab_id,
                    "startRowIndex": start_row_idx,
                    "endRowIndex": end_row_idx,
                    "startColumnIndex": start_col_idx,
                    "endColumnIndex": end_col_idx
                },
                "description": "Lock example cell",
                "warningOnly": False,
                "editors": {
                    "users": []
                }
            }
        }
    }
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def _get_data_validation_formatter(
        tab_id: int, start_row_idx: int, end_row_idx: int, start_col_idx: int,
        end_col_idx: int, rule: str, options=None
):
    """
    Return the formatter that sets data validation rules for cells or row / col
    ranges thereof.

    Args:
        tab_id: unique tab identifier.
        start_row_idx: index of start row.
        end_row_idx: index of end row.
        start_col_idx: index of start column.
        end_col_idx: index of end column.
        rule: validation rule.
        options (optional): list of elements fior dropdown list is using
        dropdown validation rules. Defaults to None.

    Raises:
        RuntimeError: raised if dropdown is passed as rule AND options is not a
        list.

    Returns:
        dict: DESCRIPTION.

    """

    rules_dict = {
        'date': {
            "condition": {
                "type": "DATE_IS_VALID"
            }
        },
        'number': {
            "condition": {
                "type": "NUMBER_GREATER_THAN_EQ",
                "values": [{"userEnteredValue": "-1e100"}]
            }
        }
    }

    if rule == 'dropdown':
        if options is None or not isinstance(options, list):
            raise RuntimeError(
                'There must be a list of items to populate the dropdown list!')
        rules_dict['dropdown'] = {
            "condition": {
                "type": "ONE_OF_LIST",
                "values": [{"userEnteredValue": v} for v in options]
            }
        }

    format_dict = rules_dict[rule]
    format_dict.update({"showCustomUi": True, "strict": True})

    return {

        "setDataValidation": {
            "range": {
                "sheetId": tab_id,
                "startRowIndex": start_row_idx,
                "endRowIndex": end_row_idx,
                "startColumnIndex": start_col_idx,
                "endColumnIndex": end_col_idx
            },
            "rule": format_dict
        }
    }
# -----------------------------------------------------------------------------
