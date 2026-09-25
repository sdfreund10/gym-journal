// Sets a cookie containing the user's time zone to display times in their local time.
(function setTimeZoneCookie() {
  const TZ_COOKIE_NAME = "gym-journal-timezone";
  const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return decodeURIComponent(parts.pop().split(";").shift());
    }
    return null;
  };

  if (getCookie(TZ_COOKIE_NAME) !== browserTimezone) {
    document.cookie =
      `${TZ_COOKIE_NAME}=${encodeURIComponent(browserTimezone)}` +
      `; path=/; max-age=${60 * 60 * 24 * 365}`;
  }
})();
