/**
 * AI Lyric Video Generator - Client-side JavaScript
 */

// Utility functions
const LyricVideoApp = {
    // Format timestamp (seconds) to MM:SS format
    formatTime: function(seconds) {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    // Show formatted error message
    showError: function(message) {
        alert('Error: ' + message);
    },
    
    // Update task status with fetch API
    updateTaskStatus: async function(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error updating task status:', error);
            return null;
        }
    },
    
    // Get queue status with fetch API
    getQueueStatus: async function() {
        try {
            const response = await fetch('/api/queue/status');
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error getting queue status:', error);
            return null;
        }
    },
    
    // Submit a new task
    submitTask: async function(songQuery) {
        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ song_query: songQuery })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to submit task');
            }
            
            return data;
        } catch (error) {
            console.error('Error submitting task:', error);
            this.showError(error.message);
            return null;
        }
    }
};

// Initialize tooltips and popovers if Bootstrap is used
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if they exist
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    
    if (typeof bootstrap !== 'undefined') {
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// Auto-refresh task status for task detail page
if (document.getElementById('task-status-container')) {
    const taskIdElement = document.querySelector('table th + td');
    if (taskIdElement) {
        const taskId = taskIdElement.textContent.trim();
        const statusElements = document.querySelectorAll('.badge');
        
        let isCompleted = false;
        statusElements.forEach(el => {
            if (el.textContent.trim() === 'Completed' || el.textContent.trim() === 'Failed') {
                isCompleted = true;
            }
        });
        
        if (!isCompleted && taskId) {
            // Check for status update every 5 seconds
            setInterval(async function() {
                const data = await LyricVideoApp.updateTaskStatus(taskId);
                if (data && data.status !== document.querySelector('table tr:nth-child(3) td .badge').textContent.trim().toLowerCase()) {
                    // Status changed - reload the page
                    window.location.reload();
                }
            }, 5000);
        }
    }
}

// Auto-update queue status on index page
const queueCountElement = document.getElementById('queue-count');
if (queueCountElement) {
    // Update every 5 seconds
    setInterval(async function() {
        const data = await LyricVideoApp.getQueueStatus();
        if (data) {
            const totalJobs = data.queue.queued + data.queue.active;
            queueCountElement.textContent = `${totalJobs} task(s) in queue`;
            
            // Update progress bar
            const progressElement = document.getElementById('queue-progress');
            if (progressElement) {
                if (totalJobs > 0) {
                    const width = (data.queue.active / totalJobs) * 100;
                    progressElement.style.width = `${width}%`;
                } else {
                    progressElement.style.width = '0%';
                }
            }
        }
    }, 5000);
}
