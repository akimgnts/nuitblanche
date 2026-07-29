/**
 * Triggers.gs — weekly automatic generation.
 *
 * installWeeklyTrigger() is not on the menu on purpose: it's a one-time
 * setup step, run once from the Apps Script editor (select the function
 * and click Run) after filling in the PARAMETRES tab.
 */

function installWeeklyTrigger() {
  removeWeeklyTrigger_();

  var config = getConfig_();
  var weekDay = mapFrenchDayToTriggerDay_(config.GENERATION_DAY);
  var hour = parseInt((config.GENERATION_HOUR || '08:00').split(':')[0], 10) || 8;

  ScriptApp.newTrigger('weeklyGenerationTrigger')
    .timeBased()
    .onWeekDay(weekDay)
    .atHour(hour)
    .inTimezone(config.TIMEZONE || 'Europe/Paris')
    .create();

  SpreadsheetApp.getUi().alert(
    'Déclencheur hebdomadaire installé : ' + config.GENERATION_DAY + ' vers ' + hour + 'h.'
  );
}

function removeWeeklyTrigger_() {
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === 'weeklyGenerationTrigger') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}

/** The function the weekly trigger actually calls. */
function weeklyGenerationTrigger() {
  generateCarouselNow();
}

function mapFrenchDayToTriggerDay_(label) {
  var days = {
    lundi: ScriptApp.WeekDay.MONDAY,
    mardi: ScriptApp.WeekDay.TUESDAY,
    mercredi: ScriptApp.WeekDay.WEDNESDAY,
    jeudi: ScriptApp.WeekDay.THURSDAY,
    vendredi: ScriptApp.WeekDay.FRIDAY,
    samedi: ScriptApp.WeekDay.SATURDAY,
    dimanche: ScriptApp.WeekDay.SUNDAY,
  };
  var key = String(label || 'lundi').trim().toLowerCase();
  return days[key] || ScriptApp.WeekDay.MONDAY;
}
