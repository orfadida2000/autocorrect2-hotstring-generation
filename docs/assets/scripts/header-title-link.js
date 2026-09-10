document$.subscribe(function () {
  const logoLink = document.querySelector("a.md-header__button.md-logo");

  const siteName = document.querySelector(
    '[data-md-component="header-title"] .md-header__topic:not([data-md-component="header-topic"]) > span.md-ellipsis',
  );

  if (!logoLink || !siteName) {
    return;
  }

  const titleLink = document.createElement("a");

  titleLink.href = logoLink.href;
  titleLink.title = "Go to homepage";
  titleLink.className = "md-header__title-link";

  siteName.replaceWith(titleLink);
  titleLink.append(siteName);
});
