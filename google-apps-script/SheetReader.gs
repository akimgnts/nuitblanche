/**
 * SheetReader.gs — turns spreadsheet rows into the generic event JSON
 * shape the Python engine expects (see backend/app/schemas/events.py).
 *
 * EVENTS_SHEET_NAME and COLUMN_MAPPING are placeholders for the generic
 * squelette. Once the real Google Sheet is received, update them to
 * match its actual tab name and column headers — see
 * docs/GOOGLE_SHEET_MAPPING.md for the full mapping guide. Columns are
 * matched by header text, not position, so reordering columns in the
 * Sheet never breaks this reader.
 */

var EVENTS_SHEET_NAME = 'EVENEMENTS';

var COLUMN_MAPPING = {
  'Date': 'date',
  'Horaire': 'start_time',
  'Horaire fin': 'end_time',
  'Lieu': 'venue',
  'Type': 'category',
  'Événement': 'title',
  'Artiste': 'artist',
  'Description': 'description',
  'Tarif': 'price',
  'Affiche': 'poster_url',
  'Mis en avant': 'featured',
};

/** Reads every non-empty row of EVENTS_SHEET_NAME into event objects. */
function readEventsFromSheet_() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(EVENTS_SHEET_NAME);
  if (!sheet) {
    throw new Error(
      "Onglet '" + EVENTS_SHEET_NAME + "' introuvable. Adaptez EVENTS_SHEET_NAME dans SheetReader.gs."
    );
  }

  var values = sheet.getDataRange().getValues();
  if (values.length < 2) {
    return [];
  }

  var headers = values[0];
  var fieldByColumn = headers.map(function (header) {
    return COLUMN_MAPPING[String(header).trim()] || null;
  });

  var events = [];
  for (var row = 1; row < values.length; row++) {
    var raw = values[row];
    var isBlank = raw.every(function (cell) {
      return cell === '' || cell === null;
    });
    if (isBlank) continue;

    var event = { featured: false };
    for (var col = 0; col < raw.length; col++) {
      var field = fieldByColumn[col];
      if (!field) continue;
      event[field] = formatCellValue_(field, raw[col]);
    }

    if (!event.external_id) {
      event.external_id = EVENTS_SHEET_NAME + '-row-' + (row + 1);
    }
    events.push(event);
  }
  return events;
}

function formatCellValue_(field, value) {
  if (value === '' || value === null || value === undefined) {
    return field === 'featured' ? false : null;
  }
  if (field === 'date' && value instanceof Date) {
    return Utilities.formatDate(value, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  if ((field === 'start_time' || field === 'end_time') && value instanceof Date) {
    return Utilities.formatDate(value, Session.getScriptTimeZone(), 'HH:mm');
  }
  if (field === 'featured') {
    var normalized = String(value).trim().toLowerCase();
    return value === true || normalized === 'oui' || normalized === 'true' || normalized === '1';
  }
  if (typeof value === 'string') {
    return value.trim();
  }
  return value;
}
