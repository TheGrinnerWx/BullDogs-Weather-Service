function updateClock() {
    const clockElement = document.getElementById('live-clock');
    if (!clockElement) return;

    const now = new Date();
    const options = {
        timeZone: 'America/New_York',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    };
    
    // Format: 12:34:56 PM
    const timeString = now.toLocaleTimeString('en-US', options);
    
    // We update the text content. We can also add a blinking effect here if desired.
    clockElement.textContent = timeString;
}

// Update immediately and then every second
document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);
});
