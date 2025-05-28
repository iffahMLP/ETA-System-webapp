
import logging
import time
from config import SPREADSHEET_ID, SHEET_NAME
from services.sheets_service import get_service, update_sheet_with_retry
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)
service = get_service()

def apply_formulas():
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:N'
        ).execute()
        values = result.get('values', [])
        last_row = len(values) + 1 if values else 2

        assign_type_formulas = []
        pic_formulas = []
        supplier_formulas = []
        for row in range(2, last_row + 1):
            assign_type_formulas.append([f'=IFNA(IF(F{row}="US",IFNA(XLOOKUP(E{row},assign_types!D:D,assign_types!E:E),XLOOKUP(E{row},assign_types!A:A,assign_types!B:B)),XLOOKUP(E{row},assign_types!A:A,assign_types!B:B)),"")'])
            pic_formulas.append([f'=IFNA(IF(F{row}="US",IFNA(XLOOKUP(E{row},assign_types!E:E,assign_types!F:F),XLOOKUP(E{row},assign_types!A:A,assign_types!C:C)),XLOOKUP(E{row},assign_types!A:A,assign_types!C:C)),"")'])
            supplier_formulas.append([f"=IFNA(XLOOKUP(E{row},'[Auto] Supplier'!A:A,'[Auto] Supplier'!B:B),\"\")"])

        update_sheet_with_retry(service, SPREADSHEET_ID, f'{SHEET_NAME}!G2:G{last_row}', {'values': assign_type_formulas}, 'USER_ENTERED')
        update_sheet_with_retry(service, SPREADSHEET_ID, f'{SHEET_NAME}!I2:I{last_row}', {'values': pic_formulas}, 'USER_ENTERED')
        update_sheet_with_retry(service, SPREADSHEET_ID, f'{SHEET_NAME}!H2:H{last_row}', {'values': supplier_formulas}, 'USER_ENTERED')

    except Exception as e:
        logger.error(f"Error applying formulas: {str(e)}")
        raise

def get_sheet_id():
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        for sheet in spreadsheet.get('sheets', []):
            if sheet.get('properties', {}).get('title') == SHEET_NAME:
                return sheet.get('properties', {}).get('sheetId')
    except Exception as e:
        logger.error(f"Error getting sheet ID: {str(e)}")
        return None

def delete_rows():
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:N'
        ).execute()
        values = result.get('values', [])
        rows_to_delete = [i for i, row in enumerate(values) if len(row) > 3 and row[3] in ['Tip', 'MLP-AIR-FRESHENER', '']]

        if not rows_to_delete:
            return

        rows_to_delete.sort(reverse=True)
        sheet_id = get_sheet_id()
        requests = [{"deleteDimension": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": i,
                "endIndex": i + 1
            }
        }} for i in rows_to_delete]

        for attempt in range(3):
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID, body={"requests": requests}
                ).execute()
                logger.info(f"Deleted rows: {rows_to_delete}")
                break
            except HttpError as e:
                if e.resp.status in [429, 503]:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except Exception as e:
                raise
    except Exception as e:
        logger.error(f"Error in delete_rows: {str(e)}")
        raise

def delete_duplicate_rows():
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:N'
        ).execute()
        values = result.get('values', [])
        seen = set()
        rows_to_delete = []

        for i, row in enumerate(values):
            row_str = ','.join(row)
            if row_str in seen:
                rows_to_delete.append(i)
            else:
                seen.add(row_str)

        if not rows_to_delete:
            return

        rows_to_delete.sort(reverse=True)
        sheet_id = get_sheet_id()
        requests = [{"deleteDimension": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": i,
                "endIndex": i + 1
            }
        }} for i in rows_to_delete]

        for attempt in range(3):
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID, body={"requests": requests}
                ).execute()
                logger.info(f"Deleted duplicate rows: {rows_to_delete}")
                break
            except HttpError as e:
                if e.resp.status in [429, 503]:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except Exception as e:
                raise
    except Exception as e:
        logger.error(f"Error in delete_duplicate_rows: {str(e)}")
        raise
