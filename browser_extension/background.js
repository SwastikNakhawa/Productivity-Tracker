// Background script for Productivity Tracker extension
class ProductivityTracker {
    constructor() {
        this.currentTab = null;
        this.tabStartTime = null;
        this.serverUrl = 'http://127.0.0.1:3000';
        this.isConnected = false;

        this.init();
    }

    init() {
        console.log('🚀 Productivity Tracker extension initialized');

        // Listen for tab changes
        chrome.tabs.onActivated.addListener((activeInfo) => {
            this.handleTabChange(activeInfo.tabId);
        });

        // Listen for tab updates
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            if (changeInfo.status === 'complete' && tab.active) {
                this.handleTabChange(tabId, tab);
            }
        });

        // Listen for window focus changes
        chrome.windows.onFocusChanged.addListener((windowId) => {
            if (windowId === chrome.windows.WINDOW_ID_NONE) {
                this.handleBrowserBlur();
            } else {
                this.handleBrowserFocus();
            }
        });

        // Track tab removal
        chrome.tabs.onRemoved.addListener((tabId) => {
            this.handleTabRemove(tabId);
        });

        // Test server connection
        this.testConnection();
    }

    async handleTabChange(tabId, tab = null) {
        // Save previous tab activity
        if (this.currentTab && this.tabStartTime) {
            await this.saveTabActivity(this.currentTab);
        }

        // Get new tab info
        if (!tab) {
            try {
                tab = await chrome.tabs.get(tabId);
            } catch (error) {
                console.log('Error getting tab:', error);
                return;
            }
        }

        // Skip internal pages and empty URLs
        if (!tab.url || this.isInternalPage(tab.url)) {
            this.currentTab = null;
            this.tabStartTime = null;
            return;
        }

        // Start tracking new tab
        this.currentTab = {
            id: tab.id,
            url: tab.url,
            title: tab.title || 'Untitled',
            timestamp: new Date().toISOString()
        };
        this.tabStartTime = Date.now();

        console.log(`🎯 Tracking: ${this.getDomain(tab.url)}`);
    }

    async saveTabActivity(tabInfo) {
        const duration = Date.now() - this.tabStartTime;

        // Only save if duration is significant (more than 3 seconds)
        if (duration < 3000) {
            return;
        }

        const activityData = {
            url: tabInfo.url,
            title: tabInfo.title,
            tabId: tabInfo.id,
            timestamp: tabInfo.timestamp,
            duration: Math.floor(duration / 1000) // Convert to seconds
        };

        try {
            const response = await fetch(`${this.serverUrl}/api/browser-activity`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(activityData)
            });

            if (response.ok) {
                const result = await response.json();
                console.log(`✅ Saved: ${this.getDomain(tabInfo.url)} (${Math.floor(duration/1000)}s)`);
            } else {
                console.log('❌ Failed to save activity');
            }
        } catch (error) {
            console.log('🌐 Server not available - is Python tracker running?');
            this.isConnected = false;
        }
    }

    handleBrowserBlur() {
        // Browser lost focus
        if (this.currentTab && this.tabStartTime) {
            this.saveTabActivity(this.currentTab);
            this.tabStartTime = null;
            console.log('⏸️  Browser minimized/lost focus');
        }
    }

    handleBrowserFocus() {
        // Browser gained focus
        if (this.currentTab) {
            this.tabStartTime = Date.now();
            console.log('▶️  Browser focused');
        }
    }

    handleTabRemove(tabId) {
        // Tab closed
        if (this.currentTab && this.currentTab.id === tabId) {
            this.saveTabActivity(this.currentTab);
            this.currentTab = null;
            this.tabStartTime = null;
            console.log('🗑️  Tab closed');
        }
    }

    isInternalPage(url) {
        return url.startsWith('chrome://') ||
               url.startsWith('edge://') ||
               url.startsWith('about:') ||
               url.startsWith('opera://') ||
               url.includes('chrome-extension://') ||
               url.includes('extension://');
    }

    getDomain(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname.replace('www.', '');
        } catch {
            return url;
        }
    }

    async testConnection() {
        try {
            const response = await fetch(`${this.serverUrl}/api/health`, {
                method: 'GET'
            });
            this.isConnected = response.ok;

            if (this.isConnected) {
                console.log('✅ Connected to productivity tracker server');
            } else {
                console.log('❌ Server not responding properly');
            }
        } catch (error) {
            this.isConnected = false;
            console.log('❌ Cannot connect to productivity tracker server');
            console.log('💡 Make sure you run: python src/main_console.py and start browser tracking');
        }
    }

    getStatus() {
        return {
            isConnected: this.isConnected,
            currentTab: this.currentTab ? this.getDomain(this.currentTab.url) : 'None',
            trackingSince: this.tabStartTime ? new Date(this.tabStartTime).toLocaleTimeString() : 'Not tracking'
        };
    }
}

// Initialize tracker
const tracker = new ProductivityTracker();

// Handle messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getStatus') {
        sendResponse(tracker.getStatus());
    }
    return true; // Keep message channel open for async response
});

// Periodic connection check
setInterval(() => {
    tracker.testConnection();
}, 30000); // Check every 30 seconds