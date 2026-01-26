// function updateUnreadCount() {
//     fetch('/notifications/unread-count')
//         .then(response => response.text())
//         .then(count => {
//             document.getElementById('unread-count').innerText = count;
//         });
//         setTimeout(updateUnreadCount, 30000);
// }
// window.onload = updateUnreadCount;

document.addEventListener('DOMContentLoaded', () => {
    const bell = document.getElementById('notification-bell');
    const dropdown = document.getElementById('notification-dropdown');
    const unreadBadge = document.getElementById('unread-count');
    const unreadHeader = document.getElementById('dropdown-unread');
    const list = document.getElementById('notification-list');

    if (!bell) return;

    function toggleDropdown() {
        dropdown.classList.toggle('hidden');
        if (!dropdown.classList.contains('hidden')) {
            loadNotifications();
        }
    }

    function loadNotifications() {
        fetch('/notifications/json/')
            .then(response => response.json())
            .then(data => {
                list.innerHTML = '';  // Clear previous items

                data.notifications.forEach(notif => {
                    const li = document.createElement('li');
                    li.classList.toggle('unread', !notif.is_read);

                    // Build the clickable link inside the <li>
                    li.innerHTML = `
                        <a href="/bookings/management/" class="text-decoration-none text-dark d-block p-2">
                            ${notif.message}
                            <small class="text-muted">(${notif.created_at})</small>
                        </a>`;

                    list.appendChild(li);
                });

                unreadBadge.textContent = data.unread_count;
                unreadHeader.textContent = `${data.unread_count} unread`;
            })
            .catch(err => console.error('Notifications fetch failed:', err));
    }

    bell.addEventListener('click', (e) => {
        e.preventDefault();
        toggleDropdown();
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!bell.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });

    // Optional: initial load or poll every 60s
    // setInterval(loadNotifications, 60000);
});