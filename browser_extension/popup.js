// Popup script
document.addEventListener('DOMContentLoaded', function() {
    updateStatus();
    document.getElementById('refreshBtn').addEventListener('click', updateStatus);
});

async function updateStatus() {
    try {
        // Show loading state
        document.getElementById('statusText').textContent = 'Checking...';
        document.getElementById('statusMessage').textContent = 'Connecting to tracker...';
        document.getElementById('currentSite').textContent = 'Loading...';
        document.getElementById('trackingTime').textContent = '-';

        // Send message to background script
        const response = await chrome.runtime.sendMessage({action: 'getStatus'});

        const statusCard = document.getElementById('statusCard');
        const statusText = document.getElementById('statusText');
        const statusMessage = document.getElementById('statusMessage');

        if (response.isConnected) {
            statusText.textContent = '✅ CONNECTED';
            statusMessage.textContent = 'Browser tracking is active';
            statusCard.className = 'status-card connected';
        } else {
            statusText.textContent = '❌ DISCONNECTED';
            statusMessage.textContent = 'Start the desktop app to begin tracking';
            statusCard.className = 'status-card disconnected';
        }

        document.getElementById('currentSite').textContent = response.currentTab;
        document.getElementById('trackingTime').textContent = response.trackingSince;

    } catch (error) {
        console.error('Error:', error);
        document.getElementById('statusText').textContent = '❌ ERROR';
        document.getElementById('statusMessage').textContent = 'Could not check status';
        document.getElementById('statusCard').className = 'status-card disconnected';
    }
}

// Auto-refresh every 5 seconds when popup is open
setInterval(updateStatus, 5000);