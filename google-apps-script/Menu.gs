/**
 * Menu.gs — the "Nuit Blanche" custom menu, created every time the Sheet opens.
 */

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Nuit Blanche')
    .addItem('Générer le carrousel maintenant', 'generateCarouselNow')
    .addItem('Régénérer le dernier carrousel', 'regenerateLastCarousel')
    .addItem('Ouvrir le dernier export', 'openLastExport')
    .addToUi();
}
