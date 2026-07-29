/**
 * Config.gs — the PARAMETRES tab is the human-editable source of truth;
 * this file mirrors it into PropertiesService (Script Properties) so the
 * rest of the project reads plain key/value config without re-parsing
 * the sheet on every call.
 */

var PARAMETRES_SHEET_NAME = 'PARAMETRES';

// Label shown in the sheet -> internal config key. Add rows here if you
// need more parameters; existing ones can be relabeled without touching
// any other file.
var PARAMETRES_FIELDS = [
  { label: "URL de l'API", key: 'API_URL', default: '' },
  { label: 'Clé API', key: 'API_KEY', default: '' },
  { label: 'Dossier Google Drive (ID)', key: 'DRIVE_FOLDER_ID', default: '' },
  { label: 'Jour de génération', key: 'GENERATION_DAY', default: 'lundi' },
  { label: 'Heure de génération', key: 'GENERATION_HOUR', default: '08:00' },
  { label: 'Nombre de jours à inclure', key: 'DAYS_TO_INCLUDE', default: '7' },
  { label: 'Email de notification', key: 'NOTIFICATION_EMAIL', default: '' },
  { label: 'Fuseau horaire', key: 'TIMEZONE', default: 'Europe/Paris' },
  { label: 'Ville', key: 'CITY_NAME', default: 'Le Havre' },
  { label: 'Identifiant Instagram', key: 'INSTAGRAM_HANDLE', default: '' },
];

/** Creates the PARAMETRES tab with defaults if it doesn't exist yet. */
function ensureParametresSheet_() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getSheetByName(PARAMETRES_SHEET_NAME);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(PARAMETRES_SHEET_NAME);
  }
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['Paramètre', 'Valeur']);
    PARAMETRES_FIELDS.forEach(function (field) {
      sheet.appendRow([field.label, field.default]);
    });
    sheet.setFrozenRows(1);
    sheet.autoResizeColumns(1, 2);
  }
  return sheet;
}

/** Reads PARAMETRES and copies it into Script Properties. */
function syncConfigFromSheet_() {
  var sheet = ensureParametresSheet_();
  var values = sheet.getDataRange().getValues();

  var valueByLabel = {};
  for (var i = 1; i < values.length; i++) {
    valueByLabel[String(values[i][0]).trim()] = values[i][1];
  }

  var config = {};
  PARAMETRES_FIELDS.forEach(function (field) {
    var raw = valueByLabel.hasOwnProperty(field.label) ? valueByLabel[field.label] : field.default;
    config[field.key] = raw === '' || raw === undefined || raw === null ? field.default : String(raw);
  });

  PropertiesService.getScriptProperties().setProperties(config);
  return config;
}

/** Fast config read. Falls back to a sheet sync the first time it's called. */
function getConfig_() {
  var properties = PropertiesService.getScriptProperties().getProperties();
  if (!properties || !properties.API_URL) {
    return syncConfigFromSheet_();
  }
  return properties;
}
