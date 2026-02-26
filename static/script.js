async function checkRefresh() {
    const refreshValue = await (await fetch("/refresh")).text()
    console.log(refreshValue, window._oldRefreshValue)
    if(refreshValue == window._oldRefreshValue) return
    if(!window._oldRefreshValue) {
        window._oldRefreshValue = refreshValue
        return
    }

    window.location.href = window.location.href
}

checkRefresh();

setInterval(async () => {
    checkRefresh()
}, 1000);