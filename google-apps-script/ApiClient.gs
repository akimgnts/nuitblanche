/**
 * ApiClient.gs — builds the request payload and calls the Python
 * carousel-generation API.
 */

/** Builds a WeekRequest payload starting today, spanning DAYS_TO_INCLUDE days. */
function buildWeekPayload_(config, events) {
  var daysToInclude = parseInt(config.DAYS_TO_INCLUDE, 10) || 7;
  var startDate = new Date();
  var endDate = new Date();
  endDate.setDate(startDate.getDate() + daysToInclude - 1);

  return {
    city: config.CITY_NAME,
    week_number: getIsoWeekNumber_(startDate),
    start_date: formatDate_(startDate),
    end_date: formatDate_(endDate),
    events: events,
  };
}

/** POSTs the payload to /api/v1/carousels/generate and returns the parsed JSON body. */
function callGenerateApi_(config, payload) {
  if (!config.API_URL) {
    throw new Error("URL de l'API manquante dans l'onglet PARAMETRES.");
  }

  var response = UrlFetchApp.fetch(config.API_URL, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'X-API-Key': config.API_KEY },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });

  var statusCode = response.getResponseCode();
  var body;
  try {
    body = JSON.parse(response.getContentText());
  } catch (parseError) {
    throw new Error('Réponse API illisible (HTTP ' + statusCode + '): ' + response.getContentText());
  }

  if (statusCode < 200 || statusCode >= 300) {
    var detail = body && body.detail ? body.detail : response.getContentText();
    throw new Error('Erreur API (HTTP ' + statusCode + '): ' + detail);
  }

  return body;
}

function formatDate_(date) {
  return Utilities.formatDate(date, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

/** ISO 8601 week number, used as a sensible default for week_number. */
function getIsoWeekNumber_(date) {
  var target = new Date(date.getTime());
  target.setHours(0, 0, 0, 0);
  target.setDate(target.getDate() + 3 - ((target.getDay() + 6) % 7));
  var firstThursday = new Date(target.getFullYear(), 0, 4);
  var daysDiff = (target - firstThursday) / 86400000 - 3 + ((firstThursday.getDay() + 6) % 7);
  return 1 + Math.round(daysDiff / 7);
}
