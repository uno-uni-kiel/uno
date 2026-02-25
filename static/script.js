setInterval(async () => {
    const value = await (await fetch("/refresh")).text()
    console.log(value)
    // window.location.href = window.location.href
}, 1000)