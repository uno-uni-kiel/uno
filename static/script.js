window._oldRefreshValue = localStorage.getItem("refreshValue")

async function checkRefresh() {
  const refreshValue = await (await fetch("/refresh")).text();
  if (refreshValue == window._oldRefreshValue) return;
  if (!window._oldRefreshValue) {
    window._oldRefreshValue = refreshValue;
    return;
  }

  localStorage.setItem("refreshValue", refreshValue)
  window.location.href = window.location.href;
}

checkRefresh();

setInterval(async () => {
  checkRefresh();
}, 1000);
