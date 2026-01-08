// Content script - runs on every page
console.log('Productivity Tracker content script loaded');

// Track user activity on the page
let pageActive = true;
let lastActivity = Date.now();

// Track user interactions
document.addEventListener('mousemove', updateActivity);
document.addEventListener('keydown', updateActivity);
document.addEventListener('click', updateActivity);
document.addEventListener('scroll', updateActivity);

function updateActivity() {
    pageActive = true;
    lastActivity = Date.now();
}

// Check for inactivity every 30 seconds
setInterval(() => {
    const inactiveTime = Date.now() - lastActivity;
    if (inactiveTime > 30000) { // 30 seconds
        pageActive = false;
    }
}, 30000);

// Send page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden');
    } else {
        console.log('Page visible');
        updateActivity();
    }
});