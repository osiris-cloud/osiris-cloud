window.onload = ()=> {
    consoleText(['the better web','robust deployments','seamless integrations'], 'text', ['']);
}
function consoleText(words, id)
{
    let visible = true;
    const con = document.getElementById('console-text-con');
    let letterCount = 1;
    let x = 1;
    let waiting = false;
    let target = document.getElementById(id);
    window.setInterval(function()
    {
        if (letterCount === 0 && waiting === false)
        {
            waiting = true;
            target.innerHTML = words[0].substring(0, letterCount);
            window.setTimeout(function()
            {
                let usedWord = words.shift();
                words.push(usedWord);
                x = 1;
                letterCount += x;
                waiting = false;
            }, 1000);
        }
        else if (letterCount === words[0].length + 1 && waiting === false)
        {
            waiting = true;
            window.setTimeout(function() {
                x = -1;
                letterCount += x;
                waiting = false;
            }, 1000);
        }
        else if (waiting === false)
        {
            target.innerHTML = words[0].substring(0, letterCount);
            letterCount += x;
        }
    }, 120);

    window.setInterval(function()
    {
        if (visible === true)
        {
            con.className = 'console-underscore hidden';
            visible = false;
        }
        else
        {
            con.className = 'console-underscore';
            visible = true;
        }
    }, 400);
}
