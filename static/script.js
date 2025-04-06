// Initialize Lucide icons
lucide.createIcons();

// Mock data for detections
//const detections = [
//  { id: 1, time: '10:45:23', name: 'John Doe', confidence: '95%' },
//  { id: 2, time: '10:45:30', name: 'Unknown', confidence: '87%' },
//  { id: 3, time: '10:45:45', name: 'Jane Smith', confidence: '92%' },
//];

// Populate detection table
function populateDetectionTable() {
  const tableBody = document.getElementById('detectionTableBody');
  tableBody.innerHTML = '';

  detections.forEach(detection => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="detection-time">
        <i data-lucide="clock"></i>
        ${detection.time}
      </td>
      <td>${detection.name}</td>
      <td>${detection.confidence}</td>
    `;
    tableBody.appendChild(row);
  });

  // Reinitialize icons for the new table rows
  lucide.createIcons();
}

// Alert and notification functionality
let isAlertActive = false;
const alertBox = document.getElementById('alertBox');
const alertStatus = document.getElementById('alertStatus');
const notificationStatus = document.getElementById('notificationStatus');
const toggleAlert = document.getElementById('toggleAlert');

toggleAlert.addEventListener('click', () => {
  isAlertActive = !isAlertActive;
  alertBox.classList.toggle('active', isAlertActive);
  
  if (isAlertActive) {
    alertStatus.innerHTML = '<i data-lucide="alert-circle"></i><span>Incident Detected!</span>';
    notificationStatus.innerHTML = '<i data-lucide="check-circle"></i><span>Alert sent to authorities</span>';
    notificationStatus.classList.add('sent');
  } else {
    alertStatus.innerHTML = '<i data-lucide="alert-circle"></i><span>No incidents detected</span>';
    notificationStatus.innerHTML = '<i data-lucide="check-circle"></i><span>No notifications sent</span>';
    notificationStatus.classList.remove('sent');
  }
  
  lucide.createIcons();
});

// Initialize the table
populateDetectionTable();

// Screen Sharing Functionality
const shareButton = document.getElementById('shareButton');
const liveFeed = document.getElementById('liveFeed');

shareButton.addEventListener('click', async () => {
  try {
    // Start screen sharing
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: true,
    });

    // Display the shared screen in the live feed
    liveFeed.srcObject = stream;
    liveFeed.play();

    // Change button text
    shareButton.innerHTML = '<i data-lucide="share"></i> Stop Sharing';
    shareButton.removeEventListener('click', startSharing);
    shareButton.addEventListener('click', stopSharing);

    // Function to stop sharing
    function stopSharing() {
      stream.getTracks().forEach(track => track.stop());
      liveFeed.srcObject = null;
      shareButton.innerHTML = '<i data-lucide="share"></i> Share Screen';
      shareButton.removeEventListener('click', stopSharing);
      shareButton.addEventListener('click', startSharing);
    }
  } catch (error) {
    console.error('Error starting screen sharing:', error);
    alert('Screen sharing failed. Please allow screen sharing to continue.');
  }
});