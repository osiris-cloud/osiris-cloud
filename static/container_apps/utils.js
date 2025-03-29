window.isValidIPOrSubnet = function isValidIPOrSubnet(value) {
    if (value.includes('-')) {
        const [startIP, endIP] = value.split('-');
        return isValidIP(startIP) && isValidIP(endIP) && isValidIPRange(startIP, endIP);
    }

    const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
    if (!cidrRegex.test(value)) return false;

    const parts = value.split('.');
    const ipParts = parts[3].split('/');
    const isValidRange = parts.slice(0, 3).every(part => parseInt(part) >= 0 && parseInt(part) <= 255);
    const isValidLastPart = parseInt(ipParts[0]) >= 0 && parseInt(ipParts[0]) <= 255;
    const isValidSubnet = ipParts[1] ? parseInt(ipParts[1]) >= 0 && parseInt(ipParts[1]) <= 32 : true;

    return isValidRange && isValidLastPart && isValidSubnet;
}

window.isValidIP = function isValidIP(ip) {
    const parts = ip.split('.');
    if (parts.length !== 4) return false;
    return parts.every(part => {
        const num = parseInt(part);
        return num >= 0 && num <= 255 && part === num.toString(); // Ensures no leading zeros
    });
}

window.isValidIPRange = function isValidIPRange(startIP, endIP) {
    const start = ipToNumber(startIP);
    const end = ipToNumber(endIP);
    return start !== null && end !== null && start <= end;
}

window.ipToNumber = function ipToNumber(ip) {
    const parts = ip.split('.');
    if (parts.length !== 4) return null;

    return parts.reduce((acc, part) => {
        const num = parseInt(part);
        if (isNaN(num) || num < 0 || num > 255) return null;
        return (acc << 8) + num;
    }, 0);
}
