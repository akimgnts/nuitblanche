/**
 * Drive.gs — "where did the last carousel end up".
 *
 * The MVP Python engine stores files locally (see
 * backend/app/storage/local.py) and returns a ZIP download URL. Once
 * GoogleDriveStorageProvider is implemented and DRIVE_FOLDER_ID is set,
 * openDriveFolderIfConfigured_() starts returning a real Drive folder
 * URL and openLastExport() can be pointed at it instead.
 */

function openLastExport() {
  var properties = PropertiesService.getScriptProperties();
  var lastUrl = properties.getProperty('LAST_DOWNLOAD_URL');

  if (!lastUrl) {
    SpreadsheetApp.getUi().alert('Aucun export précédent. Générez un carrousel au préalable.');
    return;
  }

  var html = HtmlService.createHtmlOutput(
    '<p>Dernier export :</p>' +
      '<p><a href="' + lastUrl + '" target="_blank">' + lastUrl + '</a></p>' +
      '<script>window.open("' + lastUrl + '", "_blank");</script>'
  )
    .setWidth(440)
    .setHeight(140);

  SpreadsheetApp.getUi().showModalDialog(html, 'Dernier export Nuit Blanche');
}

/** Returns the configured Drive folder's URL, or null if not set / not accessible. */
function openDriveFolderIfConfigured_(config) {
  if (!config.DRIVE_FOLDER_ID) {
    return null;
  }
  try {
    return DriveApp.getFolderById(config.DRIVE_FOLDER_ID).getUrl();
  } catch (error) {
    return null;
  }
}
