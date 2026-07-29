/**
 * Code.gs — main entry points wired to the "Nuit Blanche" menu (see Menu.gs)
 * and to the weekly trigger (see Triggers.gs).
 */

function generateCarouselNow() {
  runGeneration_({ useStoredWeek: false });
}

function regenerateLastCarousel() {
  runGeneration_({ useStoredWeek: true });
}

function runGeneration_(options) {
  var ui = SpreadsheetApp.getUi();
  var config = getConfig_();

  try {
    var events = readEventsFromSheet_();
    if (events.length === 0) {
      ui.alert("Aucun événement trouvé dans l'onglet '" + EVENTS_SHEET_NAME + "'.");
      return;
    }

    var properties = PropertiesService.getScriptProperties();
    var payload;
    if (options.useStoredWeek && properties.getProperty('LAST_WEEK_START')) {
      // Régénération : on garde la même semaine que le dernier export, on
      // relit juste les événements (utile pour les ajouts de dernière minute).
      payload = {
        city: config.CITY_NAME,
        week_number: parseInt(properties.getProperty('LAST_WEEK_NUMBER'), 10),
        start_date: properties.getProperty('LAST_WEEK_START'),
        end_date: properties.getProperty('LAST_WEEK_END'),
        events: events,
      };
    } else {
      payload = buildWeekPayload_(config, events);
    }

    var result = callGenerateApi_(config, payload);

    properties.setProperties({
      LAST_GENERATION_ID: result.generation_id,
      LAST_DOWNLOAD_URL: joinUrl_(config.API_URL, result.download_url),
      LAST_WEEK_START: payload.start_date,
      LAST_WEEK_END: payload.end_date,
      LAST_WEEK_NUMBER: String(payload.week_number),
      LAST_GENERATED_AT: new Date().toISOString(),
    });

    notifyIfConfigured_(config, payload, result);

    var warningsText =
      result.warnings && result.warnings.length ? '\nAvertissements : ' + result.warnings.join(', ') : '';
    ui.alert('Carrousel généré : ' + result.slide_count + ' slides.' + warningsText);
  } catch (error) {
    ui.alert('Échec de la génération : ' + error.message);
  }
}

function notifyIfConfigured_(config, payload, result) {
  if (!config.NOTIFICATION_EMAIL) return;

  MailApp.sendEmail({
    to: config.NOTIFICATION_EMAIL,
    subject: 'Nuit Blanche — carrousel semaine ' + payload.week_number + ' prêt',
    body:
      'Le carrousel de la semaine ' +
      payload.week_number +
      ' (' +
      payload.start_date +
      ' au ' +
      payload.end_date +
      ') est prêt.\n\n' +
      'Téléchargement : ' +
      joinUrl_(config.API_URL, result.download_url),
  });
}

function joinUrl_(apiUrl, path) {
  if (!path) return apiUrl;
  if (path.indexOf('http') === 0) return path;
  var origin = apiUrl.replace(/\/api\/v1\/.*$/, '');
  return origin + path;
}
