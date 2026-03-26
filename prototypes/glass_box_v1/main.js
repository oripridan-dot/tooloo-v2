// Tooloo Glass Box Prototype Engine
const buddyMessages = [
    "Architectural Note: Recursive memory protection active.",
    "Tribunal Insight: Self-audit identifies zero policy drift.",
    "Vision-to-Code Loop: Pixel intensity matches CSS token calibration.",
    "Agency Alert: Transition from 'Mock' to 'Live' confirmed."
];

let messageIndex = 0;
const buddyText = document.getElementById('buddy-text');
const buddyBox = document.getElementById('buddy-box');

function rotateBuddyInsight() {
    messageIndex = (messageIndex + 1) % buddyMessages.length;
    
    // Simple fade effect
    buddyBox.style.opacity = 0;
    setTimeout(() => {
        buddyText.innerText = buddyMessages[messageIndex];
        buddyBox.style.opacity = 1;
    }, 500);
}

// Rotate insight every 8 seconds
setInterval(rotateBuddyInsight, 8000);

// Initialize some dynamic behavior
console.log("TooLoo Tier-5 Prototype Live.");
